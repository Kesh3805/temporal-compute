"""C1 headroom check: how far are the registered-style baselines from the oracle?

If the oracle (true variances) is < 10% better than the best baseline at a
budget, no allocation policy can be 10% better there either.
"""

from __future__ import annotations

import sys

import numpy as np

from sim import POLICIES, make_scene, oracle_static_mse, run

CHECKPOINTS = [32, 64, 128, 256]  # mean cost per pixel (≈ spp at mean cost 1)


def main(n_scenes=12, cost_sd=0.5, seed=20261103):
    rng = np.random.default_rng(seed)
    names = list(POLICIES)
    for family in ("diffuse", "caustic", "mixed"):
        logs = {k: [] for k in names + ["oracle_static"]}
        raw = {k: [] for k in names + ["oracle_static"]}
        for i in range(n_scenes):
            sc = make_scene(rng, family, cost_sd=cost_sd)
            for k in names:
                e = np.array(run(k, sc, seed + 1000 * i, CHECKPOINTS))
                logs[k].append(np.log(np.maximum(e, 1e-12)))
                raw[k].append(e)
            e = np.array([oracle_static_mse(sc, b) for b in CHECKPOINTS])
            logs["oracle_static"].append(np.log(e))
            raw["oracle_static"].append(e)
        best = min(("variance", "mcucb", "costaware"), key=lambda k: np.mean(logs[k]))
        print(f"\n[{family}] cost_sd={cost_sd} scenes={n_scenes} strongest baseline={best}")
        print(f"{'policy':15s} " + " ".join(f"{c:>8d}" for c in CHECKPOINTS) + "   effect_vs_best(log) effect_vs_best(meanMSE)")
        for k in names + ["oracle_static"]:
            L = np.array(logs[k])
            R = np.array(raw[k])
            eff_log = 1 - np.exp(np.mean(L - np.array(logs[best])))
            eff_mean = 1 - R.mean() / np.array(raw[best]).mean()
            print(f"{k:15s} " + " ".join(f"{v:8.2e}" for v in np.exp(L.mean(0)))
                  + f"   {eff_log:+8.3f}            {eff_mean:+8.3f}")
        sys.stdout.flush()


if __name__ == "__main__":
    sd = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    main(n_scenes=n, cost_sd=sd)
