"""Shard [0, 32768) of each extended stream must equal the registered 32768-spp image (same binary, identity)."""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from reference_shards import load_npy  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shards', required=True)
    parser.add_argument('--registered', required=True, help='directory with registered <stem>-<stream>-32768.npy/.json')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rows, problems = [], []
    for path in sorted(Path(args.shards).glob('*.json')):
        shard = json.loads(path.read_text(encoding='utf-8'))
        if shard.get('schema') != 'tc-r1-reference-shard-v1' or (shard['begin'], shard['end']) != (0, 32768):
            continue
        scene_id, frame_id, _, stream = shard['identity']
        reg_path = Path(args.registered)/f'{scene_id}-{frame_id}-{stream}-32768.npy'
        if not reg_path.exists():
            problems.append(f'missing registered image {reg_path.name}')
            continue
        record = json.loads(reg_path.with_suffix('.json').read_text(encoding='utf-8'))
        a = load_npy(Path(args.shards)/shard['path'], shard['sha256'])
        b = load_npy(reg_path, record['sha256'])
        tolerance = 1e-6 + 1e-5*np.maximum(np.abs(a), np.abs(b))
        worst = float(np.max(np.abs(a-b)/tolerance))
        identical = bool(np.array_equal(a, b))
        if worst > 1 or record['binary_sha256'] != shard['binary_sha256'] or record['seed'] != shard['seed']:
            problems.append(f'{scene_id}/{frame_id} {stream}: worst {worst:.3f}, binary/seed match '
                            f"{record['binary_sha256'] == shard['binary_sha256']}/{record['seed'] == shard['seed']}")
        rows.append(dict(frame=f'{scene_id}/{frame_id}', stream=stream, identical=identical, worst_tolerance=worst))
    verdict = 'PASS' if rows and not problems else 'FAIL'
    Path(args.output).write_text(json.dumps(dict(verdict=verdict, rows=rows, problems=problems), indent=1)+'\n',
                                 encoding='utf-8')
    print(json.dumps(dict(verdict=verdict, compared=len(rows), identical=sum(r['identical'] for r in rows),
                          problems=problems[:5])))
    sys.exit(0 if verdict == 'PASS' else 1)


if __name__ == '__main__':
    main()
