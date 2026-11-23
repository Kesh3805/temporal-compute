"""Column-only fetch of the TC-01-HG meta parquet files via HTTP range requests."""
import io, json, sys, urllib.request, urllib.error, time
import pyarrow.parquet as pq, pyarrow as pa

BASE = "https://huggingface.co/datasets/AnonymizedTMLRSubmission/reasoning-traces/resolve/main/"
COLS = ["model_key", "data_id", "task", "seed", "extracted_answer", "is_correct",
        "num_completion_tokens", "finish_reason", "ground_truth", "num_prompt_tokens"]

class RangeFile(io.RawIOBase):
    def __init__(self, url):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "tc01-audit"})
        with urllib.request.urlopen(req) as r:
            self.size = int(r.headers["Content-Length"])
        self.bytes = 0
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos
    BLOCK = 1 << 20
    _cache_start, _cache = -1, b""
    def _get(self, start, end):
        delay = 5
        for attempt in range(12):
            try:
                req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}", "User-Agent": "tc01-audit"})
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
        if n is None or n < 0: n = self.size - self.pos
        if n == 0 or self.pos >= self.size: return b""
        end = min(self.pos + n, self.size)
        B = 1 << 18
        if not hasattr(self, "_blocks"): self._blocks = {}
        first, last = self.pos // B, (end - 1) // B
        missing = [k for k in range(first, last + 1) if k not in self._blocks]
        while missing:  # fetch contiguous runs of missing blocks in one request each
            k0 = missing[0]; k1 = k0
            while k1 + 1 in missing: k1 += 1
            data = self._get(k0 * B, min((k1 + 1) * B, self.size) - 1)
            for k in range(k0, k1 + 1):
                self._blocks[k] = data[(k - k0) * B:(k - k0 + 1) * B]
            missing = [k for k in missing if k > k1]
        buf = b"".join(self._blocks[k] for k in range(first, last + 1))
        data = buf[self.pos - first * B:end - first * B]
        self.pos += len(data)
        return data
    def readinto(self, b):
        d = self.read(len(b)); b[:len(d)] = d; return len(d)

def main(listfile, outdir):
    paths = [l.strip() for l in open(listfile) if l.strip()]
    total = 0
    for p in paths:
        out = f"{outdir}/{p.replace('/', '__')}"
        import os
        if os.path.exists(out): continue
        f = RangeFile(BASE + p)
        pf = pq.ParquetFile(f)
        names = set(pf.schema_arrow.names)
        cols = [c for c in COLS if c in names]
        missing = [c for c in COLS if c not in names]
        t = pf.read(columns=cols)
        pq.write_table(t, out)
        total += f.bytes
        print(json.dumps({"file": p, "rows": t.num_rows, "missing": missing, "fetched_mb": round(f.bytes/1e6, 2)}), flush=True)
    print("TOTAL_MB", round(total/1e6, 1))

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
