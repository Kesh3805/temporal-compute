#!/usr/bin/env python3
"""Run every fixed scenario twice, verify byte replay, and save research artifacts."""
import argparse
import json
import os
from pathlib import Path
import subprocess

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='results/local')
    parser.add_argument('--binary', help='Use an already built tc executable')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if not args.binary:
        subprocess.run(['cargo', 'build', '--locked', '--release', '-p', 'tc-cli'], cwd=root, check=True)
    target = Path(os.environ.get('CARGO_TARGET_DIR', 'target'))
    if not target.is_absolute():
        target = root / target
    binary = Path(args.binary).resolve() if args.binary else target / 'release' / ('tc.exe' if os.name == 'nt' else 'tc')
    directory = root / args.output
    directory.mkdir(parents=True, exist_ok=True)
    summaries = []
    # Run all commands before writing artifacts: git_dirty must not change mid-replay.
    reports = []
    for scenario in sorted((root / 'scenarios').glob('*/scenario.toml')):
        command = [str(binary), 'compare', scenario.relative_to(root).as_posix(), '--seed', '42', '--format', 'json']
        first = subprocess.check_output(command, cwd=root)
        second = subprocess.check_output(command, cwd=root)
        if first != second:
            raise RuntimeError(f'nondeterministic output: {scenario}')
        report = json.loads(first)
        reports.append((scenario.parent.name, first))
        for run in report['runs']:
            summaries.append(dict(scenario=run['scenario']['name'], scheduler=run['scheduler'], **run['metrics']))
    for name, output in reports:
        (directory / f'{name}.json').write_bytes(output)
    (directory / 'summary.json').write_text(json.dumps(summaries, indent=2) + '\n', encoding='utf-8')
    print(f'{len(reports)} scenarios x 5 schedulers: byte-identical replay verified; artifacts: {directory}')
    for row in summaries:
        print(f"{row['scenario']:20} {row['scheduler']:26} utility={row['total_utility']:5} wasted_us={row['compute_time_wasted_us']}")

if __name__ == '__main__':
    main()
