"""Common wall cap C calibration (amendment 0006 section 4). Non-primary fixture, uniform policy only.

Runs the uniform policy with the persistent worker and cached kernel to the
final registered checkpoint A_u + 2^26, three repeats, snapshot extraction
included. C = 2 x median wall time, rounded up to a whole minute.
No primary scene, reference or policy comparison.
"""
import argparse
import hashlib
import json
import math
import statistics
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from execution_runner import PolicyRun  # noqa: E402
from persistent_backend import PersistentPbrtBackend  # noqa: E402

FIXTURE = ROOT/'research/tc-r1/local-measurement/fixtures/throughput-256.pbrt'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    rows = []
    with open(args.output, 'x', encoding='utf-8') as reserve:
        reserve.write('{"status": "started"}\n')
    for repeat in range(3):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)

            def backends(stream):
                return PersistentPbrtBackend(args.binary, args.manifest, FIXTURE, digest,
                                             ('cap-calibration', 'f0', repeat, stream), tmp/stream, threads=1,
                                             admitted_scenes={digest})

            def sink(policy, index, image):
                array = np.asarray(image, dtype='<f8')
                path = tmp/f'snapshot-{index}.npy'
                np.save(path, array)
                value = hashlib.sha256(path.read_bytes()).hexdigest()
                path.unlink()
                return value
            # A tiny cap makes the run end exactly when the last checkpoint commits.
            record = PolicyRun(256, 256, backends, 1e-9, sink, tmp/'trace.jsonl').run('uniform')
            rows.append(dict(repeat=repeat, seconds=record['seconds'], requests=record['requests'],
                             initialization=record['initialization'], charged_rays=record['charged_rays'],
                             checkpoints=record['checkpoints'], snapshots=len(record['snapshots'])))
    median = statistics.median(r['seconds'] for r in rows)
    cap = 60*math.ceil(2*median/60)
    report = dict(schema='tc-r1-cap-calibration-v1', fixture_sha256=digest,
                  binary_sha256=hashlib.sha256(Path(args.binary).read_bytes()).hexdigest(),
                  rows=rows, median_seconds=median, cap_seconds=cap, rule='C = 2 x median, rounded up to a minute',
                  primary_scenes_used=False, policy_comparison=False)
    Path(args.output).write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(dict(median_seconds=median, cap_seconds=cap)))


if __name__ == '__main__':
    main()
