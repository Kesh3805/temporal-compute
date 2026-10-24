"""Reference producer validation on non-primary fixtures (amendment 0006).

For each fixture, the producer's full-frame PFM image at a fixed seed and spp
must equal, per pixel and channel within the frozen E2 estimator tolerance,
the mean of the qualified binary's per-sample ToOutputRGB records for the
same seed and spp. This checks orientation, seed handling and the Film
estimator in one comparison. No primary scene is rendered.
"""
import argparse
import csv
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from reference_producer import render  # noqa: E402

FIXTURES = {'surface-paths.pbrt': ROOT/'research/tc-r1/native-validation/fixtures/surface-paths.pbrt',
            'throughput-256.pbrt': ROOT/'research/tc-r1/local-measurement/fixtures/throughput-256.pbrt'}
SEED, SPP = 123457, 64


def close(a, b):
    return abs(a-b) <= 1e-6 + 1e-5*max(abs(a), abs(b))


def logged_means(binary, scene, seed, spp, threads, workdir):
    log = Path(workdir)/'samples.csv'
    env = {k: v for k, v in os.environ.items() if not k.startswith('TC_R1')}
    env['TC_R1E_SAMPLE_LOG'] = str(log)
    proc = subprocess.run([str(binary), '--nthreads', str(threads), '--seed', str(seed), '--spp', str(spp), '--quiet',
                           '--outfile', str(Path(workdir)/'logged.pfm'), str(scene)], env=env, capture_output=True,
                          text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:])
    sums, counts = {}, {}
    with open(log, newline='') as handle:
        for row in csv.reader(handle):
            key = (int(row[0]), int(row[1]))
            rgb = tuple(float(v) for v in row[3:6])
            prior = sums.get(key, (0.0, 0.0, 0.0))
            sums[key] = tuple(p+v for p, v in zip(prior, rgb))
            counts[key] = counts.get(key, 0) + 1
    return {k: tuple(v/counts[k] for v in s) for k, s in sums.items()}, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rows = []
    for name, scene in FIXTURES.items():
        for threads in (1, 4):
            with tempfile.TemporaryDirectory() as tmp:
                image, _, _, _ = render(args.binary, scene, SEED, SPP, threads, tmp)
                means, counts = logged_means(args.binary, scene, SEED, SPP, 1, tmp)
            height, width = image.shape[:2]
            problems = []
            if set(counts) != {(x, y) for y in range(height) for x in range(width)} or set(counts.values()) != {SPP}:
                problems.append('logged sample domain')
            worst = 0.0
            for (x, y), mean in means.items():
                for c in range(3):
                    a, b = float(image[y, x, c]), mean[c]
                    if not (math.isfinite(a) and close(a, b)):
                        if len(problems) < 5:
                            problems.append(f'pixel ({x},{y}) channel {c}: producer {a!r} vs samples {b!r}')
                    worst = max(worst, abs(a-b)/(1e-6+1e-5*max(abs(a), abs(b))))
            rows.append(dict(fixture=name, threads=threads, spp=SPP, pixels=len(means),
                             worst_tolerance_fraction=worst, problems=problems))
    verdict = 'PASS' if all(not r['problems'] for r in rows) else 'FAIL'
    Path(args.output).write_text(json.dumps(dict(schema='tc-r1-reference-producer-validation-v1', verdict=verdict,
                                                 seed=SEED, rows=rows), indent=1)+'\n', encoding='utf-8')
    print(verdict)
    if verdict != 'PASS':
        sys.exit(1)


if __name__ == '__main__':
    main()
