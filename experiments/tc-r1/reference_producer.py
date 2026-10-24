"""Reference image producer (amendment 0006): full-frame native render to canonical NPY.

Renders one reference stream with the qualified binary (no TC logs enabled),
the stream's registered PBRT seed and a full deterministic prefix [0, spp).
PBRT writes float32 PFM; this module converts it to the canonical C-order
little-endian float64 H,W,RGB array. Orientation and the Film estimator are
validated against per-sample means on non-primary fixtures before use.
"""
import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from reference_pipeline import STREAMS, reference_plan  # noqa: E402


def read_pfm(raw):
    """Parse a colour PFM into an H,W,3 float64 array with row 0 at the image top."""
    stream = io.BytesIO(raw)
    if stream.readline().strip() != b'PF':
        raise ValueError('colour PFM required')
    width, height = map(int, stream.readline().split())
    scale = float(stream.readline().strip())
    dtype = '<f4' if scale < 0 else '>f4'
    data = np.frombuffer(stream.read(), dtype=dtype)
    if data.size != width*height*3:
        raise ValueError('PFM payload size mismatch')
    # PFM stores scanlines bottom to top.
    image = data.reshape(height, width, 3)[::-1].astype('<f8')
    if not np.isfinite(image).all():
        raise ValueError('nonfinite reference value')
    return np.ascontiguousarray(image)


def canonical_bytes(image):
    buffer = io.BytesIO()
    np.save(buffer, np.ascontiguousarray(image, dtype='<f8'), allow_pickle=False)
    return buffer.getvalue()


def render(binary, scene, seed, spp, threads, workdir):
    env = {k: v for k, v in os.environ.items() if not k.startswith('TC_R1')}
    out = Path(workdir)/'reference.pfm'
    command = [str(binary), '--nthreads', str(threads), '--seed', str(seed), '--spp', str(spp),
               '--quiet', '--outfile', str(out), str(scene)]
    start = time.perf_counter_ns()
    proc = subprocess.run(command, env=env, capture_output=True, text=True)
    elapsed = time.perf_counter_ns() - start
    if proc.returncode != 0:
        raise RuntimeError('native reference render failed: '+proc.stderr[-2000:])
    return read_pfm(out.read_bytes()), command, elapsed, proc.stdout+proc.stderr


def produce(binary, scene, scene_id, frame_id, asset_sha256, corpus_sha256, spp, stream, threads, output):
    if stream not in STREAMS:
        raise ValueError('reference stream required')
    if hashlib.sha256(Path(scene).read_bytes()).hexdigest() != asset_sha256:
        raise ValueError('scene asset hash mismatch')
    plan = reference_plan(scene_id, frame_id, asset_sha256, corpus_sha256, spp)
    with tempfile.TemporaryDirectory() as tmp:
        image, command, elapsed, log = render(binary, scene, plan['pbrt_seeds'][stream], spp, threads, tmp)
    if image.shape != (256, 256, 3):
        raise ValueError('reference must be 256x256 RGB')
    raw = canonical_bytes(image)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'xb') as handle:   # never overwrite reference evidence
        handle.write(raw)
    record = dict(schema='tc-r1-reference-image-v1', plan=plan, stream=stream, path=output.name,
                  sha256=hashlib.sha256(raw).hexdigest(), command=command, elapsed_ns=elapsed,
                  binary_sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(), threads=threads,
                  source='PBRT float32 PFM converted exactly to float64', log_tail=log[-2000:])
    output.with_suffix('.json').write_text(json.dumps(record, indent=1)+'\n', encoding='utf-8')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary', 'scene', 'scene-id', 'frame-id', 'asset-sha256', 'corpus-sha256', 'stream', 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--spp', type=int, required=True)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    record = produce(args.binary, args.scene, args.scene_id, args.frame_id, args.asset_sha256, args.corpus_sha256,
                     args.spp, args.stream, args.threads, args.output)
    print(json.dumps(dict(sha256=record['sha256'], seconds=record['elapsed_ns']/1e9)))


if __name__ == '__main__':
    main()
