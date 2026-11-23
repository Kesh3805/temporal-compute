"""E1: correlated spike footprints (see docs/tc-ia1/prereg-footprint.md).

Usage: python footprint.py <k> [scenes] [seeds]
"""

from __future__ import annotations

import sys

import numpy as np

from sim import POLICIES, make_scene, oracle_static_mse, run

CHECKPOINTS = [32, 64, 128, 256]
P = 256
COST_SD = 0.52


def main(k, n_scenes=12, n_seeds=2, seed=20261105):
    rng = np.random.default_rng(seed)
    names = list(POLICIES) + ["oracle_static"]
    print(f"k={k} (footprint {k}x{k}, {P // (k * k)} spike draws/sample/region) P={P} cost_sd={COST_SD}")
    for family in ("caustic", "mixed"):
        logs = {n: [] for n in names}
        for i in range(n_scenes):
            sc = make_scene(rng, family, cost_sd=COST_SD)
            sc["foot"] = k * k
            ora = np.log([oracle_static_mse(sc, b) for b in CHECKPOINTS])
            for j in range(n_seeds):
                s = seed + 1000 * i + j
                for name in POLICIES:
                    e = np.array(run(name, sc, s, CHECKPOINTS, P=P))
                    logs[name].append(np.log(np.maximum(e, 1e-12)))
                logs["oracle_static"].append(ora)
        ref = np.array(logs["costaware"])
        print(f"[{family}] reference = plug-in cost-aware")
        for name in names:
            d = np.array(logs[name]) - ref
            unit = d.mean(1)
            eff = 1 - np.exp(unit.mean())
            ci = 1.96 * unit.std(ddof=1) / np.sqrt(len(unit))
            per_cp = 1 - np.exp(d.mean(0))
            print(f"  {name:14s} effect {eff:+.3f} (95% CI log ±{ci:.3f})  by checkpoint "
                  + " ".join(f"{x:+.3f}" for x in per_cp))
        sys.stdout.flush()


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]), *(int(x) for x in a[1:]))
