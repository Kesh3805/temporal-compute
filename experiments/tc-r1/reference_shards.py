"""Sharded reference rendering (proposed amendment 0007).

A reference stream at N spp is the Film estimate over sample indices [0, N).
The worker's DUMP renders any [begin, end) for the stream's registered
identity; the independent sampler fixes every sample by (pixel, index), so
disjoint shards covering [0, N) combine, by count-weighted mean, into the same
estimate as one render of [0, N) up to float rounding. Shards from a lower
level are reused by higher levels: they are the identical deterministic prefix.
"""
import argparse
import hashlib
import io
import json
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from persistent_backend import PersistentPbrtBackend  # noqa: E402
from progressive_kernel import Region, require  # noqa: E402
from reference_producer import RENDER_TIMEOUT_SECONDS, canonical_bytes, resolution  # noqa: E402

SHARD_SPP = 32768


def shard_ranges(spp, shard=SHARD_SPP):
    require(type(spp) is int and spp > 0 and spp % shard == 0, 'level must be a positive multiple of the shard size')
    return [(b, b+shard) for b in range(0, spp, shard)]


def render_shard(binary, manifest, scene, scene_sha256, identity, begin, end, threads, output):
    width, height = resolution(scene)
    with tempfile.TemporaryDirectory() as tmp:
        backend = PersistentPbrtBackend(binary, manifest, scene, scene_sha256, identity, Path(tmp)/'dump',
                                        threads=threads, admitted_scenes={scene_sha256},
                                        timeout=RENDER_TIMEOUT_SECONDS)
        start = time.perf_counter_ns()
        image, dump_sha256 = backend.dump(Region(0, width, 0, height), begin, end)
        elapsed = time.perf_counter_ns() - start
        backend.close()
    raw = canonical_bytes(image)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'xb') as handle:
        handle.write(raw)
    record = dict(schema='tc-r1-reference-shard-v1', path=output.name, identity=list(identity), begin=begin, end=end,
                  seed=backend.seed, sha256=hashlib.sha256(raw).hexdigest(), dump_sha256=dump_sha256,
                  elapsed_ns=elapsed, threads=threads, scene_sha256=scene_sha256,
                  binary_sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
                  startup_failures=backend.startup_failures)
    output.with_suffix('.json').write_text(json.dumps(record, indent=1)+'\n', encoding='utf-8')
    return record


def load_npy(path, expected_sha256):
    raw = Path(path).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == expected_sha256, f'shard hash mismatch: {Path(path).name}')
    with io.BytesIO(raw) as source:
        image = np.load(source, allow_pickle=False)
    require(image.dtype == np.dtype('<f8') and image.ndim == 3 and np.isfinite(image).all(), 'invalid shard image')
    return image


def combine(records, directory, spp):
    """Count-weighted mean of shards that exactly tile [0, spp) for one identity and one binary."""
    require(records, 'no shards')
    identities = {tuple(r['identity']) for r in records}
    binaries = {r['binary_sha256'] for r in records}
    scenes = {r['scene_sha256'] for r in records}
    require(len(identities) == len(binaries) == len(scenes) == 1, 'shards mix identities, binaries or scenes')
    ordered = sorted(records, key=lambda r: r['begin'])
    require([(r['begin'], r['end']) for r in ordered] == shard_ranges(spp, ordered[0]['end']-ordered[0]['begin']),
            'shards do not tile [0, spp) exactly')
    total = None
    for r in ordered:
        image = load_npy(Path(directory)/r['path'], r['sha256'])*(r['end']-r['begin'])
        total = image if total is None else total + image
    return np.ascontiguousarray(total/spp, dtype='<f8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    shard = sub.add_parser('shard')
    for name in ('binary', 'manifest', 'scene', 'scene-sha256', 'scene-id', 'frame-id', 'stream', 'output'):
        shard.add_argument('--'+name, required=True)
    shard.add_argument('--begin', type=int, required=True)
    shard.add_argument('--end', type=int, required=True)
    shard.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    identity = (args.scene_id, args.frame_id, 0, args.stream)
    record = render_shard(args.binary, args.manifest, args.scene, args.scene_sha256, identity, args.begin, args.end,
                          args.threads, args.output)
    print(json.dumps(dict(sha256=record['sha256'], seconds=record['elapsed_ns']/1e9)))


if __name__ == '__main__':
    main()
