"""TC-HP1 phase 2: Stage 0 quantities and predictions. Never evaluates M.

Usage: python predict.py <data dir> <output json>
"""
import json, sys
import numpy as np
import pandas as pd
from common import *

PAIRS = {
    "P1": dict(sub="sc", file="MATH_Llama-3-8B-Instruct", kind="MATH", B=("uniform", 16)),
    "P2": dict(sub="sc", file="GSM8K_Llama-3-8B-Instruct", kind="GSM8K", B=("uniform", 16)),
    "P3": dict(sub="sc", file="MATH_Llama-3-70B-Instruct", kind="MATH", B=("asc", 0.95)),
    "P4": dict(sub="ab", file="MATH_Llama-3-8B-Instruct", kind="MATH", B=("asc", 0.95)),
    "P5": dict(sub="rt"), "P6": dict(sub="rt"),
}


def load_mb(d, f):
    return [json.loads(l) for l in open(f"{d}/mb_{f}.jsonl", encoding="utf-8")]


def sc_oracle_curves(S, cost_B):
    """Per unit mean quality/cost of the per unit-permutation hindsight stopper, for each lambda."""
    lc, ct = S["lc"].astype(float), S["ct"]
    Q, C = [], []
    for lam in LAMBDAS:
        ch = (lc - lam * ct / cost_B).argmax(-1)[..., None]
        Q.append(np.take_along_axis(lc, ch, -1)[..., 0].mean(1))
        C.append(np.take_along_axis(ct, ch, -1)[..., 0].mean(1))
    return np.array(Q), np.array(C)  # [L, U]


def gate(H_lo, D, obs):
    win = bool(H_lo >= 0.20 and D >= 0.10 and obs >= 0.70)
    ghat = float(np.clip(min(H_lo, D) * (2 * obs - 1), 0, 1)) if np.isfinite(H_lo) and np.isfinite(D) else 0.0
    return win, ghat


def predict_sc(cfg, units, S, sc80w):
    U = len(units)
    nB = stop_index(S, *cfg["B"], units)
    aB, cB = outcome(S, nB)
    aB_u, cB_u = aB.mean(1), cB.mean(1)
    qB, costB = aB_u.mean(), cB_u.mean()
    Qd, Cd = sc_oracle_curves(S, costB)

    def H_of(w):
        q_t, c_b = weighted_mean(aB_u, w), weighted_mean(cB_u, w)
        c_o = lambda_curve_cost(weighted_mean(Qd, w), weighted_mean(Cd, w), q_t)
        return 1 - c_o / c_b

    H = H_of(np.ones(U))
    hs = np.array([H_of(w) for w in bootstrap_groups(U)])
    H_lo = float(np.nanpercentile(hs, 2.5)) if np.isfinite(hs).any() else float("nan")
    # O_stat: one n per question-length quintile (in-sample)
    bins = quintile_bins(units)
    lc_n, ct_n = S["lc"].mean(1), S["ct"].mean(1)  # [U, NMAX] uniform-n per unit
    Qs, Cs = [], []
    for lam in LAMBDAS:
        q = c = 0.0
        for b in range(5):
            m = bins == b
            if not m.any():
                continue
            j = (lc_n[m].sum(0) - lam * ct_n[m].sum(0) / costB).argmax()
            q += lc_n[m, j].sum(); c += ct_n[m, j].sum()
        Qs.append(q / U); Cs.append(c / U)
    c_stat = lambda_curve_cost(np.array(Qs), np.array(Cs), qB)
    c_dyn = lambda_curve_cost(Qd.mean(1), Cd.mean(1), qB)
    D = (c_stat - c_dyn) / costB
    # Obs: plurality at n=4 equals plurality at n=80
    F = first4_features(S, units).reshape(U * R, -1)
    y = (S["ld"][:, :, K_FEAT - 1] == S["ld"][:, :, NMAX - 1]).reshape(-1).astype(int)
    obs, _ = cv_auroc(F, y, np.repeat(np.arange(U), R))
    return dict(q_B=qB, cost_B=costB, cost_Odyn=c_dyn, cost_Ostat=c_stat, H=H, H_lo=H_lo, D=D, Obs=obs)


def predict_ab(cfg, units, S, sc80w):
    U = len(units)
    keep = ~sc80w
    aB, cB = outcome(S, stop_index(S, *cfg["B"], units))
    cB = np.maximum(cB, S["ct"][:, :, K_FEAT - 1])
    aB_u, cB_u = aB.mean(1), cB.mean(1)
    qB, costB = aB_u.mean(), cB_u.mean()
    target = qB - 0.005

    def H_of(w):
        q_t = weighted_mean(aB_u, w) - 0.005
        qo, co = weighted_mean(aB_u * keep, w), weighted_mean(cB_u * keep, w)
        return (1 - co / weighted_mean(cB_u, w)) if qo >= q_t else float("nan")

    H = H_of(np.ones(U))
    hs = np.array([H_of(w) for w in bootstrap_groups(U)])
    H_lo = float(np.nanpercentile(np.where(np.isfinite(hs), hs, -1.0), 2.5))
    c_dyn = (cB_u * keep).mean() if (aB_u * keep).mean() >= target else float("nan")
    bins = quintile_bins(units)
    best = costB
    for mask in range(32):
        ab = np.isin(bins, [b for b in range(5) if mask >> b & 1])
        if (aB_u * ~ab).mean() >= target:
            best = min(best, (cB_u * ~ab).mean())
    D = (best - c_dyn) / costB
    F = first4_features(S, units).reshape(U * R, -1)
    y = np.repeat(sc80w, R).astype(int)
    obs, _ = cv_auroc(F, y, np.repeat(np.arange(U), R))
    return dict(q_B=qB, target=target, cost_B=costB, cost_Odyn=c_dyn, cost_Ostat=best, H=H, H_lo=H_lo, D=D, Obs=obs)


def predict_rt(pair, sp):
    df, n_pre = sprout_stream(sp, pair)
    qB, costB, est_static, lamB = sprout_B(df, n_pre)
    post = df.iloc[n_pre:].reset_index(drop=True)
    dlt, dc = post["delta"].to_numpy(), (post["c_strong"] - post["c_cheap"]).to_numpy()
    sc, ss, cc, cs = (post[k].to_numpy() for k in ("s_cheap", "s_strong", "c_cheap", "c_strong"))
    blocks = np.minimum((np.arange(len(post)) * NBLOCKS) // len(post), NBLOCKS - 1)
    Qd, Cd = [], []
    for lam in LAMBDAS:
        st = dlt - lam * dc / costB > 0
        Qd.append(np.where(st, ss, sc)); Cd.append(np.where(st, cs, cc))
    Qd, Cd = np.array(Qd), np.array(Cd)  # [L, N]
    stB = est_static[n_pre:] > lamB
    qB_i, cB_i = np.where(stB, ss, sc), np.where(stB, cs, cc)

    def H_of(wb):
        w = wb[blocks]
        return 1 - lambda_curve_cost(weighted_mean(Qd, w), weighted_mean(Cd, w), weighted_mean(qB_i, w)) / weighted_mean(cB_i, w)

    H = H_of(np.ones(NBLOCKS))
    hs = np.array([H_of(w) for w in bootstrap_groups(NBLOCKS)])
    H_lo = float(np.nanpercentile(hs, 2.5))
    c_dyn = lambda_curve_cost(Qd.mean(1), Cd.mean(1), qB)
    cat_mean = post.groupby("dataset")["delta"].transform("mean").to_numpy()
    pts = []
    for lam in np.concatenate([[-np.inf], np.unique(cat_mean)]):
        st = cat_mean > lam
        pts.append((np.where(st, cs, cc).mean(), np.where(st, ss, sc).mean()))
    c_stat = frontier_cost_at(pts, qB)
    D = (c_stat - c_dyn) / costB
    feat = online_estimates(df)[n_pre:, None]
    obs, _ = cv_auroc(feat, (dlt > 0).astype(int), blocks)
    return dict(q_B=qB, cost_B=costB, lambda_B=lamB, n=len(df), n_prefix=n_pre, cost_Odyn=c_dyn,
                cost_Ostat=c_stat, H=H, H_lo=H_lo, D=D, Obs=obs)


def main(d, out):
    res, cache = {}, {}
    sp = pd.read_parquet(f"{d}/sprout.parquet")
    for p, cfg in PAIRS.items():
        if cfg["sub"] in ("sc", "ab"):
            if cfg["file"] not in cache:
                units = mb_units(load_mb(d, cfg["file"]), cfg["kind"])
                cache[cfg["file"]] = (units, *sequences(units))
            units, S, sc80w = cache[cfg["file"]]
            r = (predict_sc if cfg["sub"] == "sc" else predict_ab)(cfg, units, S, sc80w)
            r["sc80_wrong_rate"] = float(sc80w.mean()); r["units"] = len(units)
        else:
            r = predict_rt(p, sp)
        r["predicted_win"], r["g_hat"] = gate(r["H_lo"], r["D"], r["Obs"])
        res[p] = r
        print(p, json.dumps({k: r[k] for k in ("q_B", "H", "H_lo", "D", "Obs", "predicted_win", "g_hat")}, default=float), flush=True)
    dump(res, out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
