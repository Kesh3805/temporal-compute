"""Integrated dry run on the non-primary 256x256 fixture (required before the execution freeze).

Exercises the exact execution path (validated worker binary, cached kernels,
six registered policies in timing order, retention, offline scoring with the
pinned metric stack, parity and determinism checks) with scaled-down
increments so it finishes quickly. Fixture references are produced at 1024 spp
with two private seeds; they are not convergence-grade and only feed scoring.
No primary scene, corpus reference or comparative outcome.
"""
import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import metrics  # noqa: E402
from execution_runner import POLICIES  # noqa: E402
from reference_pipeline import scoring_reference  # noqa: E402
from reference_producer import render  # noqa: E402
from unit_job import run_unit  # noqa: E402

FIXTURE = ROOT/'research/tc-r1/local-measurement/fixtures/throughput-256.pbrt'
INCREMENTS = (2**18, 2**19, 2**20, 2**22)
SNAPSHOT = 2**18


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary', 'manifest', 'weights', 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--cap-seconds', type=float, default=30.0)
    args = parser.parse_args()
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory() as tmp:
        a = render(args.binary, FIXTURE, 900001, 1024, 4, tmp)[0]
    with tempfile.TemporaryDirectory() as tmp:
        b = render(args.binary, FIXTURE, 900002, 1024, 4, tmp)[0]
    reference = scoring_reference(a, b)
    perceptual = metrics.Perceptual(args.weights)
    out = Path(args.output)
    summaries = []
    for repeat in (0, 1):
        summaries.append(run_unit(args.binary, args.manifest, FIXTURE, digest, {digest}, ('dry-run', 'f0', 0), repeat,
                                  args.cap_seconds, reference, dict(kind='dry-run fixture reference'), perceptual,
                                  out/f'repeat-{repeat}', increments=INCREMENTS, snapshot_rays=SNAPSHOT))
    problems = []
    for summary in summaries:
        if summary['initialization_parity'] is None or summary['initialization_parity']['status'] != 'identical':
            problems.append(f"parity {summary['repeat']}: {summary['initialization_parity']}")
        for policy, value in summary['policies'].items():
            if value['status'] != 'complete' or len(value['checkpoint_mse']) != 4:
                problems.append(f"incomplete {policy} repeat {summary['repeat']}")
    for policy in POLICIES:
        hashes = []
        for repeat in (0, 1):
            result = json.loads((out/f'repeat-{repeat}'/f'{policy}-result.json').read_text())
            checkpoint = [s['sha256'] for s in result['scores'] if s['index'] in (1, 2, 4, 16)]
            hashes.append(checkpoint)
            if not all(all(map(lambda v: v == v, (s['mse'], s['ssim'], s['lpips']))) for s in result['scores']):
                problems.append(f'nonfinite score {policy}')
        if hashes[0] != hashes[1]:
            problems.append(f'nondeterministic checkpoints {policy}')
    sizes = {p.name: sum(f.stat().st_size for f in p.rglob('*') if f.is_file()) for p in out.iterdir()}
    report = dict(schema='tc-r1-dry-run-v1', verdict='PASS' if not problems else 'FAIL', problems=problems,
                  increments=list(INCREMENTS), snapshot_rays=SNAPSHOT, cap_seconds=args.cap_seconds,
                  binary_sha256=hashlib.sha256(Path(args.binary).read_bytes()).hexdigest(), output_bytes=sizes,
                  policies={s['repeat']: {p: dict(seconds=v['seconds'], requests=v['requests'],
                                                  initialization=v['initialization']) for p, v in s['policies'].items()}
                            for s in summaries},
                  primary_scenes_used=False, comparative_outcome=False)
    (out/'dry-run-report.json').write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(dict(verdict=report['verdict'], problems=problems[:5])))
    if problems:
        sys.exit(1)


if __name__ == '__main__':
    main()
