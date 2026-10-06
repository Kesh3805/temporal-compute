"""Compare independent TC-S1 executions, excluding declared host provenance."""
import argparse
import gzip
import json
from pathlib import Path


def compare(left, right):
    names = ['aggregate.json', 'paired-comparisons.json', 'class-breakdown.json', 'sensitivity.json', 'controls.json', 'oracle.json', 'corpus/stream-hashes.json']
    for name in names:
        if json.loads((left/name).read_text()) != json.loads((right/name).read_text()):
            raise ValueError(f'scientific artifact differs: {name}')
    compressed = ['corpus/metrics.jsonl.gz'] + [p.relative_to(left).as_posix() for p in (left/'corpus/traces').glob('*.json.gz')]
    for name in compressed:
        with gzip.open(left/name, 'rb') as first, gzip.open(right/name, 'rb') as second:
            if first.read() != second.read():
                raise ValueError(f'canonical uncompressed stream differs: {name}')
    print(f'{len(names)} scientific JSON artifacts and {len(compressed)} canonical streams match; host/runtime/source provenance excluded.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('left', type=Path)
    parser.add_argument('right', type=Path)
    args = parser.parse_args()
    compare(args.left, args.right)
