"""TC-IA2 E2 runner (docs/tc-ia2/prereg-e2.md).

Usage: python e2.py <family> [scenes] [seeds]   -> writes results/e2_<family>.npz
       python e2.py score                       -> prints the D1/D2 decisions from all .npz files
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

import testbed
from e1 import FAMILIES
from estimators import est_b1, est_clamp, est_mean
from testbed import make_image, run_frame

CHECKPOINTS = [1024, 4096, 16384]
ESTIMATORS = {"mean": est_mean, "gpt_b1": est_b1, "clamp10": est_clamp}
FAMS = ["diffuse", "caustic_p1e-2", "caustic_p1e-3", "mixed"]
OUT = Path(__file__).resolve().parents[2] / "docs" / "tc-ia2" / "results"


def run(fam, n_scenes=12, n_seeds=2, seed=20261107):
    testbed.DTYPE = np.float32
    rng = np.random.default_rng(seed + sum(map(ord, fam)))
    mse = {k: [] for k in ESTIMATORS}
    worst = {k: [] for k in ESTIMATORS}
    for i in range(n_scenes):
        img = make_image(rng, H=64, W=64, **FAMILIES[fam])
        for j in range(n_seeds):
            out = run_frame(seed + 1000 * i + j, img, CHECKPOINTS, ESTIMATORS)
            for k, v in out.items():
                mse[k].append([x[0] for x in v])
                worst[k].append([x[1] for x in v])
        print(f"{fam}: scene {i + 1}/{n_scenes} done", flush=True)
    np.savez(OUT / f"e2_{fam}.npz", **{f"mse_{k}": np.array(v) for k, v in mse.items()},
             **{f"worst_{k}": np.array(v) for k, v in worst.items()})


def _stats(L):
    m, se = L.mean(), L.std(ddof=1) / np.sqrt(len(L))
    return m, se


def score():
    pooled = []
    d1_all, d2_bad = True, False
    print(f"checkpoints {CHECKPOINTS}; effects as 1 - exp(mean log ratio); + = B1 better")
    for fam in FAMS:
        z = np.load(OUT / f"e2_{fam}.npz")
        lm = np.log(z["mse_gpt_b1"]) - np.log(z["mse_mean"])
        lc = np.log(z["mse_gpt_b1"]) - np.log(z["mse_clamp10"])
        wm = np.log(z["worst_gpt_b1"]) - np.log(z["worst_mean"])
        m1, s1 = _stats(lm.mean(1))
        up1 = m1 + 1.645 * s1
        d1 = up1 <= np.log(1.02)
        d1_all &= d1
        m2, s2 = _stats(lc.mean(1))
        lo2, hi2 = m2 - 1.96 * s2, m2 + 1.96 * s2
        d2_bad |= lo2 > 0
        pooled.append(lc.mean(1))
        per_cp = " ".join(f"{1 - np.exp(x):+.3f}" for x in lm.mean(0))
        per_cpc = " ".join(f"{1 - np.exp(x):+.3f}" for x in lc.mean(0))
        print(f"[{fam}] units={len(lm)}")
        print(f"  B1 vs mean   : effect {1 - np.exp(m1):+.4f}; worst-case (95% one-sided) {1 - np.exp(up1):+.4f}"
              f" -> D1 {'PASS' if d1 else 'FAIL'}; by checkpoint {per_cp}; worst-region {1 - np.exp(wm.mean()):+.3f}")
        print(f"  B1 vs clamp10: effect {1 - np.exp(m2):+.4f} (95% CI {1 - np.exp(hi2):+.4f}..{1 - np.exp(lo2):+.4f});"
              f" by checkpoint {per_cpc}")
    P = np.concatenate(pooled)
    m, s = _stats(P)
    d2 = (m + 1.96 * s < 0) and not d2_bad
    print(f"D1 stability overall: {'SURVIVES' if d1_all else 'REJECTED'}")
    print(f"D2 pooled B1 vs clamp10: effect {1 - np.exp(m):+.4f} (95% CI {1 - np.exp(m + 1.96 * s):+.4f}.."
          f"{1 - np.exp(m - 1.96 * s):+.4f}); no family significantly worse: {not d2_bad} -> "
          f"{'SURVIVES' if d2 else 'REJECTED'}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "score":
        score()
    else:
        run(a[0], *(int(x) for x in a[1:]))
