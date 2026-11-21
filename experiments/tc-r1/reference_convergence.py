"""Convergence decisions for one reference level (amendment 0006).

For every produced A/B pair, compute the hash-bound reference metrics report
(reference_metrics.report), bind it with reference_pipeline.pair_record (which
independently re-verifies linear MSE), and record converged / escalate / halt.
No policy, production image or renderer is involved.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from reference_metrics import report  # noqa: E402
from reference_pipeline import corpus_plans, pair_record, reference_plan  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--images', required=True, help='directory holding <scene>-<frame>-<stream>-<spp>.npy and .json')
    parser.add_argument('--weights', required=True)
    parser.add_argument('--spp', type=int, required=True)
    parser.add_argument('--frames', default='all', help='comma list scene/frame, or all')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    images = Path(args.images)
    base = corpus_plans(ROOT, ROOT/'research/tc-r1/corpus/manifest.json')
    wanted = None if args.frames == 'all' else set(args.frames.split(','))
    weights = Path(args.weights)
    models = {'alexnet': weights/'alexnet-owt-7be5be79.pth', 'lpips': weights/'alex.pth'}
    rows = []
    for plan in base['pairs']:
        key = f"{plan['scene_id']}/{plan['frame_id']}"
        if wanted is not None and key not in wanted:
            continue
        level = reference_plan(plan['scene_id'], plan['frame_id'], plan['asset_sha256'], plan['corpus_sha256'], args.spp)
        stem = f"{plan['scene_id']}-{plan['frame_id']}"
        paths = {s: images/f'{stem}-{s}-{args.spp}.npy' for s in ('reference-a', 'reference-b')}
        records = {s: json.loads(p.with_suffix('.json').read_text(encoding='utf-8')) for s, p in paths.items()}
        for stream, record in records.items():
            if record['plan'] != level or record['stream'] != stream:
                raise ValueError(f'reference record identity mismatch: {stem} {stream}')
        metrics = report(paths['reference-a'], paths['reference-b'], records['reference-a']['sha256'],
                         records['reference-b']['sha256'], weights)
        metrics_path = images/f'{stem}-{args.spp}.metrics.json'
        metrics_path.write_text(json.dumps(metrics, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        rows.append(pair_record(level, paths['reference-a'], paths['reference-b'], metrics_path,
                                HERE/'reference_metrics.py', models))
    summary = dict(schema='tc-r1-reference-convergence-v1', spp=args.spp, pairs=len(rows),
                   decisions={d: sorted(f"{r['plan']['scene_id']}/{r['plan']['frame_id']}" for r in rows
                                        if r['decision'] == d) for d in ('converged', 'escalate', 'halt')},
                   records=rows)
    Path(args.output).write_text(json.dumps(summary, indent=1, default=str)+'\n', encoding='utf-8')
    print(json.dumps({d: len(v) for d, v in summary['decisions'].items()}))


if __name__ == '__main__':
    main()
