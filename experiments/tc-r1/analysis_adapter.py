"""Turn the 720 unit-job outputs into the frozen analysis inputs and run analysis.analyze.

Quality rows come from repeat 0 at the four registered checkpoints (snapshot
indices 1, 4, 16, 64). Checkpoint image hashes must be identical across the
three repeats (deterministic runs); otherwise accounting fails. Timing rows use
analysis.target_observations over each repeat's snapshot scores within C, with
follow-up exactly C. Prerequisites are computed from evidence, never asserted.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import analysis  # noqa: E402

NAMES = {'uniform': 'uniform', 'adaptive-mc-ucb-region': 'adaptive', 'variance-guided': 'variance',
         'tc-full': 'controller', 'tc-no-feedback': 'no-feedback', 'tc-equal-cost': 'equal-cost'}
CHECKPOINTS = dict(zip((1, 4, 16, 64), analysis.BUDGETS))


def family_manifest():
    manifest = json.loads((ROOT/'research/tc-r1/corpus/manifest.json').read_text(encoding='utf-8'))
    families = {f: [] for f in analysis.FAMILIES}
    for scene in manifest['scenes']:
        families[scene['family']].append(scene['scene_id'])
    return families


def load_jobs(directory):
    jobs = {}
    for summary_path in sorted(Path(directory).glob('**/summary.json')):
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        unit = summary['unit']
        key = (unit['scene_id'], unit['frame_id'], unit['replicate'], summary['repeat'])
        if key in jobs:
            raise ValueError(f'duplicate unit job {key}')
        results = {p: json.loads((summary_path.parent/f'{p}-result.json').read_text(encoding='utf-8'))
                   for p in summary['order']}
        jobs[key] = dict(summary=summary, results=results)
    return jobs


def build(jobs, cap):
    quality, timing, problems = [], [], []
    units = {k[:3] for k in jobs}
    for scene_id, frame_id, replicate in sorted(units):
        repeats = [jobs.get((scene_id, frame_id, replicate, r)) for r in range(3)]
        if any(r is None for r in repeats):
            problems.append(f'missing repeat for {scene_id}/{frame_id}/{replicate}')
            continue
        for job in repeats:
            parity = job['summary']['initialization_parity']
            if not parity or parity['status'] != 'identical':
                problems.append(f'initialization parity failed {scene_id}/{frame_id}/{replicate}')
        for policy, name in NAMES.items():
            hashes = []
            for repeat, job in enumerate(repeats):
                result = job['results'].get(policy)
                if result is None or result['record']['status'] != 'complete':
                    problems.append(f'incomplete {policy} {scene_id}/{frame_id}/{replicate} repeat {repeat}')
                    continue
                scores = result['scores']
                hashes.append(tuple(s['sha256'] for s in scores if s['index'] in CHECKPOINTS))
                rows = [dict(time=s['seconds'], mse=s['mse'], ssim=s['ssim'], lpips=s['lpips'])
                        for s in scores if s['seconds'] <= cap]
                observed = analysis.target_observations(rows, cap, cap)
                timing.append(dict(policy=name, scene_id=scene_id, frame_id=frame_id, replicate=replicate,
                                   repeat=repeat, **observed))
                if repeat == 0:
                    for s in scores:
                        if s['index'] in CHECKPOINTS:
                            quality.append(dict(policy=name, scene_id=scene_id, frame_id=frame_id,
                                                replicate=replicate, checkpoint=CHECKPOINTS[s['index']],
                                                mse=s['mse'], ssim=s['ssim'], lpips=s['lpips'],
                                                worst_region=s['worst_region']))
            if len(set(hashes)) > 1:
                problems.append(f'nondeterministic checkpoint images {policy} {scene_id}/{frame_id}/{replicate}')
    return quality, timing, problems


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jobs', required=True)
    parser.add_argument('--cap-seconds', type=float, required=True)
    parser.add_argument('--evidence', required=True, help='JSON with references/estimator/baselines/provenance flags')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    jobs = load_jobs(args.jobs)
    quality, timing, problems = build(jobs, args.cap_seconds)
    evidence = json.loads(Path(args.evidence).read_text(encoding='utf-8'))
    prerequisites = dict(references=evidence['references'] is True, estimator=evidence['estimator'] is True,
                         baselines=evidence['baselines'] is True, provenance=evidence['provenance'] is True,
                         accounting=not any('parity' in p or 'nondeterministic' in p for p in problems),
                         execution_complete=len(jobs) == 720 and not any(p.startswith(('missing', 'incomplete'))
                                                                         for p in problems))
    try:
        report = analysis.analyze(family_manifest(), quality, timing, ['uniform', 'adaptive', 'variance'],
                                  args.cap_seconds, prerequisites)
    except ValueError as error:
        report = dict(schema='tc-r1-analysis-v1', classification='INCONCLUSIVE', error=str(error),
                      prerequisites=prerequisites)
    report['adapter_problems'] = problems
    report['jobs'] = len(jobs)
    Path(args.output).write_text(json.dumps(report, indent=1, default=str)+'\n', encoding='utf-8')
    print(report['classification'])


if __name__ == '__main__':
    main()
