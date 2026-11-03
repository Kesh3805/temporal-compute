"""E2: how much headroom does a reactive (realized-error) oracle have over plug-in cost-aware?

Same scenes and seeds as E1 (footprint.py seed), so cells are comparable.
Usage: python cond_oracle.py <k>
"""

from __future__ import annotations

import sys

import numpy as np

from footprint import CHECKPOINTS, COST_SD, P
from sim import make_scene, run

NAMES = ("costaware", "oracle_floor", "oracle_cond")


def main(k, n_scenes=12, n_seeds=2, seed=20261105):
    rng = np.random.default_rng(seed)
    print(f"k={k} P={P} cost_sd={COST_SD}")
    for family in ("caustic", "mixed"):
        logs = {n: [] for n in NAMES}
        for i in range(n_scenes):
            sc = make_scene(rng, family, cost_sd=COST_SD)
            sc["foot"] = k * k
            for j in range(n_seeds):
                for name in NAMES:
                    e = np.array(run(name, sc, seed + 1000 * i + j, CHECKPOINTS, P=P))
                    logs[name].append(np.log(np.maximum(e, 1e-12)))
        ref = np.array(logs["costaware"])
        print(f"[{family}]")
        for name in NAMES:
            unit = (np.array(logs[name]) - ref).mean(1)
            ci = 1.96 * unit.std(ddof=1) / np.sqrt(len(unit))
            print(f"  {name:13s} effect {1 - np.exp(unit.mean()):+.3f} (95% CI log ±{ci:.3f})")
        sys.stdout.flush()


if __name__ == "__main__":
    main(int(sys.argv[1]))
