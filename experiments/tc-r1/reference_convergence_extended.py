"""Convergence at extended reference levels (proposed amendment 0007).

For each frame: combine both streams' shards over [0, spp), retain the combined
canonical images, compute the hash-bound reference metrics (reference_metrics.report),
re-verify linear MSE independently, and decide with the registered thresholds:
converged, escalate (next doubling) or halt at the amendment ceiling.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from reference_metrics import report  # noqa: E402
from reference_producer import canonical_bytes  # noqa: E402
from reference_shards import combine  # noqa: E402
from progressive_kernel import require  # noqa: E402

EXTENDED_LEVELS = tuple(2**k for k in range(15, 22))   # 32768 .. 2097152
CEILING = EXTENDED_LEVELS[-1]


def decide(spp, metrics):
    require(spp in EXTENDED_LEVELS, 'unregistered extended level')
    passes = (max(metrics['relative_mse_ab'], metrics['relative_mse_ba']) <= 1e-4 and
              metrics['ssim'] >= 0.995 and metrics['lpips'] <= 0.01)
    return 'converged' if passes else ('halt' if spp == CEILING else 'escalate')


def verified_mse(a, b):
    numerator = float(np.sum((a-b)**2, dtype=np.float64))
    return (numerator/(float(np.sum(b**2, dtype=np.float64)) + a.size*1e-12),
            numerator/(float(np.sum(a**2, dtype=np.float64)) + a.size*1e-12))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shards', required=True, help='directory with shard .npy/.json files')
    parser.add_argument('--frames', required=True, help='comma list scene/frame')
    parser.add_argument('--spp', type=int, required=True)
    parser.add_argument('--weights', required=True)
    parser.add_argument('--output', required=True, help='directory for combined images and the report')
    args = parser.parse_args()
    shards = Path(args.shards)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    records = [json.loads(p.read_text(encoding='utf-8')) for p in sorted(shards.glob('*.json'))]
    rows = []
    for key in args.frames.split(','):
        scene_id, frame_id = key.split('/')
        images, evidence = {}, {}
        for stream in ('reference-a', 'reference-b'):
            mine = [r for r in records if r.get('schema') == 'tc-r1-reference-shard-v1'
                    and r['identity'] == [scene_id, frame_id, 0, stream] and r['end'] <= args.spp]
            image = combine(mine, shards, args.spp)
            raw = canonical_bytes(image)
            name = f'{scene_id}-{frame_id}-{stream}-{args.spp}.npy'
            with open(out/name, 'xb') as handle:
                handle.write(raw)
            digest = hashlib.sha256(raw).hexdigest()
            (out/name).with_suffix('.json').write_text(json.dumps(dict(
                schema='tc-r1-reference-image-v3', stream=stream, path=name, sha256=digest, spp=args.spp,
                shards=[dict(begin=r['begin'], end=r['end'], sha256=r['sha256']) for r in sorted(mine, key=lambda r: r['begin'])],
                binary_sha256=mine[0]['binary_sha256'], scene_sha256=mine[0]['scene_sha256'],
                seed=mine[0]['seed']), indent=1)+'\n', encoding='utf-8')
            images[stream], evidence[stream] = image, dict(sha256=digest, path=name)
        metrics_report = report(out/evidence['reference-a']['path'], out/evidence['reference-b']['path'],
                                evidence['reference-a']['sha256'], evidence['reference-b']['sha256'], args.weights)
        (out/f'{scene_id}-{frame_id}-{args.spp}.metrics.json').write_text(
            json.dumps(metrics_report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        metrics = metrics_report['metrics']
        ab, ba = verified_mse(images['reference-a'], images['reference-b'])
        require(math.isclose(metrics['relative_mse_ab'], ab, rel_tol=1e-12, abs_tol=1e-15) and
                math.isclose(metrics['relative_mse_ba'], ba, rel_tol=1e-12, abs_tol=1e-15),
                'metric report disagrees with independently computed MSE')
        rows.append(dict(plan=dict(scene_id=scene_id, frame_id=frame_id, spp=args.spp), decision=decide(args.spp, metrics),
                         metrics=metrics, a=evidence['reference-a'], b=evidence['reference-b']))
    summary = dict(schema='tc-r1-reference-convergence-v1', spp=args.spp, extended=True, ceiling=CEILING,
                   pairs=len(rows), decisions={d: sorted(f"{r['plan']['scene_id']}/{r['plan']['frame_id']}"
                                                         for r in rows if r['decision'] == d)
                                               for d in ('converged', 'escalate', 'halt')}, records=rows)
    (out/f'convergence-{args.spp}.json').write_text(json.dumps(summary, indent=1)+'\n', encoding='utf-8')
    print(json.dumps({d: len(v) for d, v in summary['decisions'].items()}))


if __name__ == '__main__':
    main()
