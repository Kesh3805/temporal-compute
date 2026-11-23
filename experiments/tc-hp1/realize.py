"""TC-HP1 phase 3: realized gain of each M over B, then scoring against the committed predictions.

Usage: python realize.py <data dir> <predictions json> <output json>
"""
import json, sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from common import *
from predict import PAIRS, load_mb


def g_from(points, target, costB):
    c = frontier_cost_at(points, target)
    return (1 - c / costB) if np.isfinite(c) else -1.0, c


def realize_sc(p, cfg, units, S, pred):
    grid = [("asc", t) for t in TAUS] if p in ("P1", "P2") else [("esc", w) for w in WINDOWS]
    pts = []
    for b in grid:
        a, c = outcome(S, stop_index(S, *b, units))
        pts.append((c.mean(), a.mean()))
    g, c = g_from(pts, pred["q_B"], pred["cost_B"])
    return dict(g=g, cost_M=c, points=pts)


def realize_ab(cfg, units, S, sc80w, pred):
    """TC-01-HG realized() with first-4 features, no model one-hot; strict target q_B - 0.005."""
    U = len(units)
    a_ref, t_ref = outcome(S, stop_index(S, *cfg["B"], units))
    t_ref = np.maximum(t_ref, S["ct"][:, :, K_FEAT - 1]).reshape(-1)
    a_ref = a_ref.reshape(-1)
    c_ab = S["ct"][:, :, K_FEAT - 1].reshape(-1)
    X = first4_features(S, units).reshape(U * R, -1)
    y = np.repeat(sc80w, R).astype(int)
    g_ = np.repeat(np.arange(U), R)
    dec = np.zeros(len(y), bool)
    for tr, te in GroupKFold(5).split(X, y, g_):
        sc = StandardScaler().fit(X[tr])
        clf = LogisticRegression(max_iter=2000).fit(sc.transform(X[tr]), y[tr])
        ptr, pte = clf.predict_proba(sc.transform(X[tr]))[:, 1], clf.predict_proba(sc.transform(X[te]))[:, 1]
        best_q, best_s = 1.01, 0.0
        base_acc, base_tok = a_ref[tr].mean(), t_ref[tr].mean()
        for q in np.unique(np.quantile(ptr, np.linspace(0, 1, 101))):
            ab = ptr >= q
            acc = np.where(ab, 0, a_ref[tr]).mean()
            tok = np.where(ab, c_ab[tr], t_ref[tr]).mean()
            if base_acc - acc <= 0.005 and 1 - tok / base_tok > best_s:
                best_q, best_s = q, 1 - tok / base_tok
        dec[te] = pte >= best_q
    acc = np.where(dec, 0, a_ref).mean()
    tok = np.where(dec, c_ab, t_ref).mean()
    g = (1 - tok / pred["cost_B"]) if acc >= pred["target"] - 1e-12 else -1.0
    return dict(g=g, accuracy=acc, cost_M=tok, abandon_rate=float(dec.mean()), reduction_raw=float(1 - tok / pred["cost_B"]))


def realize_rt(p, sp, pred):
    df, n_pre = sprout_stream(sp, p)
    est = online_estimates(df)
    pts = route_points(df, est, n_pre, router_lams(est, n_pre))
    g, c = g_from(pts, pred["q_B"], pred["cost_B"])
    return dict(g=g, cost_M=c, points=pts)


def main(d, pred_path, out):
    pred = json.load(open(pred_path))
    sp = pd.read_parquet(f"{d}/sprout.parquet")
    res, cache = {}, {}
    for p, cfg in PAIRS.items():
        if cfg["sub"] in ("sc", "ab"):
            if cfg["file"] not in cache:
                units = mb_units(load_mb(d, cfg["file"]), cfg["kind"])
                cache[cfg["file"]] = (units, *sequences(units))
            units, S, sc80w = cache[cfg["file"]]
            r = realize_sc(p, cfg, units, S, pred[p]) if cfg["sub"] == "sc" else realize_ab(cfg, units, S, sc80w, pred[p])
        else:
            r = realize_rt(p, sp, pred[p])
        r["realized_win"] = bool(r["g"] >= 0.10)
        r["predicted_win"], r["g_hat"] = pred[p]["predicted_win"], pred[p]["g_hat"]
        res[p] = r
        print(p, json.dumps({k: r[k] for k in ("g", "realized_win", "predicted_win", "g_hat")}, default=float), flush=True)
    pw = [res[p]["predicted_win"] for p in PAIRS]
    rw = [res[p]["realized_win"] for p in PAIRS]
    agree = sum(a == b for a, b in zip(pw, rw))
    rho = float(spearmanr([res[p]["g_hat"] for p in PAIRS], [res[p]["g"] for p in PAIRS]).statistic)
    informative = any(pw) and not all(pw) and any(rw) and not all(rw)
    verdict = "UNINFORMATIVE" if not informative else ("PASS" if agree >= 5 and rho >= 0.6 else "FAIL")
    res["score"] = dict(label_agreement=agree, spearman=rho, informative=informative, verdict=verdict)
    print(json.dumps(res["score"]))
    dump(res, out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
