"""TC-IA2 E1 runner (docs/tc-ia2/prereg-e1.md). Usage: python e1.py <family> [scenes] [seeds]"""

from __future__ import annotations

import sys

import numpy as np

from estimators import BASE
from testbed import make_image, run_frame

CHECKPOINTS = [32, 64, 128, 256, 512]
FAMILIES = {
    "diffuse": dict(family="diffuse"),
    "caustic_p1e-4": dict(family="caustic", fixed_p=1e-4),
    "caustic_p1e-3": dict(family="caustic", fixed_p=1e-3),
    "caustic_p1e-2": dict(family="caustic", fixed_p=1e-2),
    "mixed": dict(family="mixed"),
}


def main(fam, n_scenes=12, n_seeds=2, seed=20261106):
    rng = np.random.default_rng(seed + sum(map(ord, fam)))
    mse = {k: [] for k in BASE}
    worst = {k: [] for k in BASE}
    for i in range(n_scenes):
        img = make_image(rng, **FAMILIES[fam])
        for j in range(n_seeds):
            out = run_frame(seed + 1000 * i + j, img, CHECKPOINTS, BASE)
            for k, v in out.items():
                mse[k].append(np.log([x[0] for x in v]))
                worst[k].append(np.log([x[1] for x in v]))
    ref, wref = np.array(mse["mean"]), np.array(worst["mean"])
    print(f"family={fam} units={len(ref)} checkpoints={CHECKPOINTS}")
    print(f"{'estimator':10s} {'effect':>7s} {'CI95 low':>8s} {'CI95 high':>9s} {'worst':>7s} {'@512':>7s} {'meanMSE':>8s}  by checkpoint")
    for k in BASE:
        d = np.array(mse[k]) - ref
        unit = d.mean(1)
        se = unit.std(ddof=1) / np.sqrt(len(unit))
        eff = 1 - np.exp(unit.mean())
        lo, hi = 1 - np.exp(unit.mean() + 1.96 * se), 1 - np.exp(unit.mean() - 1.96 * se)
        w = 1 - np.exp((np.array(worst[k]) - wref).mean())
        last = 1 - np.exp(d[:, -1].mean())
        lin = 1 - np.exp(np.array(mse[k])).mean() / np.exp(ref).mean()
        cps = " ".join(f"{1 - np.exp(x):+.3f}" for x in d.mean(0))
        print(f"{k:10s} {eff:+7.3f} {lo:+8.3f} {hi:+9.3f} {w:+7.3f} {last:+7.3f} {lin:+8.3f}  {cps}")


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], *(int(x) for x in a[1:]))
