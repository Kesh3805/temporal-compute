"""TC-HP1 data preparation.

python fetch.py mb <raw parquet path> <name> <out dir>   -> out/mb_<name>.jsonl (first 80 samples per question)
python fetch.py sprout <out dir>                          -> out/sprout.parquet (score/token columns via HTTP range)
"""
import io, json, sys, time, urllib.error, urllib.request
import pandas as pd
import pyarrow.parquet as pq

NMAX = 80
SPROUT = "https://huggingface.co/api/datasets/CARROT-LLM-Routing/SPROUT/parquet/default/train/{}.parquet"
MODELS = {"cheap": "openai-gpt-4o-mini", "strong": "openai-gpt-4o"}


class RangeFile(io.RawIOBase):
    BLOCK = 1 << 18

    def __init__(self, url):
        self.url, self.pos, self.cache, self.bytes = url, 0, {}, 0
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "tc-hp1-audit"})
        with urllib.request.urlopen(req) as r:
            self.url = r.geturl()
            self.size = int(r.headers["Content-Length"])

    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def _get(self, start, end):
        delay = 5
        for attempt in range(12):
            try:
                req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}", "User-Agent": "tc-hp1-audit"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    data = r.read()
                self.bytes += len(data)
                return data
            except urllib.error.HTTPError as e:
                if attempt == 11: raise
                wait = int(e.headers.get("Retry-After", delay)) if e.code == 429 else delay
                time.sleep(min(wait, 300)); delay = min(delay * 2, 300)
            except Exception:
                if attempt == 11: raise
                time.sleep(delay); delay = min(delay * 2, 300)

    def read(self, n=-1):
        if n < 0: n = self.size - self.pos
        n = max(0, min(n, self.size - self.pos))
        out = bytearray()
        while len(out) < n:
            b = (self.pos + len(out)) // self.BLOCK
            if b not in self.cache:
                s = b * self.BLOCK
                self.cache[b] = self._get(s, min(s + self.BLOCK, self.size) - 1)
            blk = self.cache[b]
            off = self.pos + len(out) - b * self.BLOCK
            out += blk[off:off + n - len(out)]
        self.pos += n
        return bytes(out)

    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)


def mb(raw, name, out):
    t = pq.read_table(raw, columns=["question", "samples", "is_corrects"]).to_pylist()
    with open(f"{out}/mb_{name}.jsonl", "w", encoding="utf-8") as f:
        for r in t:
            f.write(json.dumps(dict(question=r["question"], samples=r["samples"][:NMAX], is_corrects=r["is_corrects"][:NMAX])) + "\n")
    print(name, len(t), "questions")


def sprout(out):
    cols = ["dataset", "dataset_idx"] + [f"{m}.{k}" for m in MODELS.values() for k in ("score", "num_input_tokens", "num_output_tokens")]
    parts = []
    for i in range(3):
        f = RangeFile(SPROUT.format(i))
        t = pq.ParquetFile(f).read(columns=cols).flatten().to_pandas()
        parts.append(t)
        print("shard", i, len(t), "rows", round(f.bytes / 1e6, 1), "MB fetched", flush=True)
    df = pd.concat(parts, ignore_index=True)
    ren = {}
    for k, m in MODELS.items():
        ren.update({f"{m}.score": "s_" + k, f"{m}.num_input_tokens": "in_" + k, f"{m}.num_output_tokens": "out_" + k})
    df = df.rename(columns=ren)[["dataset", "dataset_idx"] + list(ren.values())]
    df.to_parquet(f"{out}/sprout.parquet", index=False)
    print("sprout", len(df), "rows")


if __name__ == "__main__":
    if sys.argv[1] == "mb":
        mb(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sprout(sys.argv[2])
