"""Reference image producer (amendment 0006): full-frame worker DUMP to canonical NPY.

PBRT's RGB film image output is half precision by default, and the frozen
corpus cannot be edited to change that (producer validation, run 40125241618).
References are therefore rendered by the validated worker's DUMP request: the
stream's registered identity fixes the PBRT seed, the full prefix [0, spp) is
rendered without per-sample logs, and the Film's own GetPixelRGB values are
written at full float precision and returned as canonical float64.
"""
import argparse
import hashlib
import io
import json
import re
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from persistent_backend import PersistentPbrtBackend  # noqa: E402
from progressive_kernel import Region  # noqa: E402
from reference_pipeline import STREAMS, reference_plan  # noqa: E402


# A full-frame 8192-32768 spp DUMP can take well over the 600 s request default.
RENDER_TIMEOUT_SECONDS = 5*3600


def resolution(scene):
    text = Path(scene).read_text(encoding='utf-8')
    x = re.search(r'"integer xresolution"\s*\[\s*(\d+)\s*\]', text)
    y = re.search(r'"integer yresolution"\s*\[\s*(\d+)\s*\]', text)
    if not x or not y:
        raise ValueError('scene resolution not found')
    return int(x.group(1)), int(y.group(1))


def canonical_bytes(image):
    buffer = io.BytesIO()
    np.save(buffer, np.ascontiguousarray(image, dtype='<f8'), allow_pickle=False)
    return buffer.getvalue()


def render(binary, manifest, scene, scene_sha256, identity, spp, threads, workdir):
    """Full-frame Film estimate over [0, spp) for one registered stream identity."""
    width, height = resolution(scene)
    backend = PersistentPbrtBackend(binary, manifest, scene, scene_sha256, identity, Path(workdir)/'dump',
                                    threads=threads, admitted_scenes={scene_sha256},
                                    timeout=RENDER_TIMEOUT_SECONDS)
    start = time.perf_counter_ns()
    image, dump_sha256 = backend.dump(Region(0, width, 0, height), 0, spp)
    elapsed = time.perf_counter_ns() - start
    backend.close()
    return np.ascontiguousarray(image, dtype='<f8'), dict(seed=backend.seed, elapsed_ns=elapsed,
                                                          dump_sha256=dump_sha256, command=backend.command,
                                                          startup_failures=backend.startup_failures)


def produce(binary, manifest, scene, scene_id, frame_id, asset_sha256, corpus_sha256, spp, stream, threads, output):
    if stream not in STREAMS:
        raise ValueError('reference stream required')
    if hashlib.sha256(Path(scene).read_bytes()).hexdigest() != asset_sha256:
        raise ValueError('scene asset hash mismatch')
    plan = reference_plan(scene_id, frame_id, asset_sha256, corpus_sha256, spp)
    with tempfile.TemporaryDirectory() as tmp:
        image, info = render(binary, manifest, scene, asset_sha256, (scene_id, frame_id, 0, stream), spp, threads, tmp)
    if info['seed'] != plan['pbrt_seeds'][stream]:
        raise ValueError('reference seed differs from the registered plan')
    if image.shape != (256, 256, 3):
        raise ValueError('reference must be 256x256 RGB')
    raw = canonical_bytes(image)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with open(output, 'xb') as handle:   # never overwrite reference evidence
        handle.write(raw)
    record = dict(schema='tc-r1-reference-image-v2', plan=plan, stream=stream, path=output.name,
                  sha256=hashlib.sha256(raw).hexdigest(), threads=threads,
                  binary_sha256=hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
                  source='validated worker DUMP of Film GetPixelRGB (float32) converted exactly to float64', **info)
    output.with_suffix('.json').write_text(json.dumps(record, indent=1)+'\n', encoding='utf-8')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary', 'manifest', 'scene', 'scene-id', 'frame-id', 'asset-sha256', 'corpus-sha256', 'stream',
                 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--spp', type=int, required=True)
    parser.add_argument('--threads', type=int, default=4)
    args = parser.parse_args()
    record = produce(args.binary, args.manifest, args.scene, args.scene_id, args.frame_id, args.asset_sha256,
                     args.corpus_sha256, args.spp, args.stream, args.threads, args.output)
    print(json.dumps(dict(sha256=record['sha256'], seconds=record['elapsed_ns']/1e9)))


if __name__ == '__main__':
    main()
