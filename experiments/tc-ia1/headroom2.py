"""Round-B testbed: headroom vs pixels per region, plus the Round-A candidate policies.

Usage: python headroom2.py <cost_sd> <pixels_per_region> <scenes> <seeds>
"""

from __future__ import annotations

import sys

import numpy as np

from sim import POLICIES, make_scene, oracle_static_mse, run

CHECKPOINTS = [32, 64, 128, 256]
BASELINES = ("variance", "mcucb", "costaware")


def main(cost_sd, P, n_scenes, n_seeds, seed=20261104):
    rng = np.random.default_rng(seed)
    names = list(POLICIES) + ["oracle_static"]
    print(f"cost_sd={cost_sd} P={P} scenes={n_scenes} seeds={n_seeds}")
    for family in ("diffuse", "caustic", "mixed"):
        logs = {k: [] for k in names}
        for i in range(n_scenes):
            sc = make_scene(rng, family, cost_sd=cost_sd)
            ora = np.log([oracle_static_mse(sc, b) for b in CHECKPOINTS])
            for j in range(n_seeds):
                s = seed + 1000 * i + j
                for k in POLICIES:
                    e = np.array(run(k, sc, s, CHECKPOINTS, P=P))
                    logs[k].append(np.log(np.maximum(e, 1e-12)))
                logs["oracle_static"].append(ora)
        best = min(BASELINES, key=lambda k: np.mean(logs[k]))
        ref = np.array(logs[best])
        print(f"[{family}] strongest baseline={best}")
        for k in names:
            d = np.array(logs[k]) - ref  # per unit x checkpoint
            unit = d.mean(1)
            eff = 1 - np.exp(unit.mean())
            se = unit.std(ddof=1) / np.sqrt(len(unit))
            per_cp = 1 - np.exp(d.mean(0))
            print(f"  {k:14s} effect {eff:+.3f} (±{1.96 * se:.3f} log)  by checkpoint "
                  + " ".join(f"{x:+.3f}" for x in per_cp))
        sys.stdout.flush()


if __name__ == "__main__":
    a = sys.argv[1:]
    main(float(a[0]), int(a[1]), int(a[2]), int(a[3]))
