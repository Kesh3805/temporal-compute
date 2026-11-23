"""TC-01-HG Stage 0 headroom audit — implements docs/tc-01-hg/preregistration.md (commit 7aa47fd).

Usage: python audit.py <dir with column-only parquet files> <output json>
"""
import glob, json, sys
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.special import betainc
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

NMAX, R, PERM_SEED, BOOT_SEED, NBOOT, K_FEAT = 80, 20, 20261121, 734923, 2000, 4
UNIFORM = [1, 2, 4, 8, 16, 32, 64, 80]
TAUS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
WINDOWS = [2, 4, 8]
CAP_MULTS = [0.25, 0.5, 1, 2, 4]


def load(d):
    t = pd.concat([pq.read_table(f).to_pandas() for f in sorted(glob.glob(f"{d}/*.parquet"))], ignore_index=True)
    t["ans"] = t["extracted_answer"].map(lambda a: "<none>" if a is None or str(a).strip() == "" else str(a).strip())
    t["is_correct"] = t["is_correct"].fillna(False).astype(bool) & (t["ans"] != "<none>")
    return t


def build_units(t, log):
    units, excluded = [], 0
    for (m, task, did), g in t.groupby(["model_key", "task", "data_id"], sort=True):
        g = g.sort_values("seed")
        if len(g) < NMAX:
            excluded += 1
            continue
        g = g.iloc[:NMAX]
        codes, uniq = pd.factorize(g["ans"])
        correct_ans = set(g.loc[g["is_correct"], "ans"])
        is_corr_code = np.array([u in correct_ans for u in uniq])
        units.append(dict(model=m, task=task, problem=f"{task}/{did}", codes=codes, corr=is_corr_code,
                          tok=g["num_completion_tokens"].to_numpy(float),
                          trunc=(g["finish_reason"].astype(str) != "stop").to_numpy(),
                          none=(g["ans"] == "<none>").to_numpy(),
                          prompt=float(g["num_prompt_tokens"].iloc[0])))
    log["units"], log["excluded_units_lt80"] = len(units), excluded
    return units


def sequences(units):
    """Per unit-permutation prefix statistics for n = 1..NMAX."""
    rng = np.random.default_rng(PERM_SEED)
    U = len(units)
    S = dict(lc=np.zeros((U, R, NMAX), bool), ct=np.zeros((U, R, NMAX)), v1=np.zeros((U, R, NMAX), int),
             v2=np.zeros((U, R, NMAX), int), perm=np.zeros((U, R, NMAX), int))
    sc80_wrong = np.zeros(U, bool)
    for u, un in enumerate(units):
        # SC@80 plurality in canonical seed order, ties to earliest-reaching answer
        sc80_wrong[u] = not un["corr"][plurality_trace(un["codes"])[-1][0]]
        for r in range(R):
            p = rng.permutation(NMAX)
            S["perm"][u, r] = p
            tr = plurality_trace(un["codes"][p])
            S["lc"][u, r] = [un["corr"][x[0]] for x in tr]
            S["v1"][u, r] = [x[1] for x in tr]
            S["v2"][u, r] = [x[2] for x in tr]
            S["ct"][u, r] = np.cumsum(un["tok"][p])
    return S, sc80_wrong


def plurality_trace(seq):
    counts, leader, out = {}, None, []
    for a in seq:
        counts[a] = counts.get(a, 0) + 1
        if leader is None or counts[a] > counts[leader]:
            leader = a
        top = sorted(counts.values(), reverse=True)
        out.append((leader, top[0], top[1] if len(top) > 1 else 0))
    return out


def stop_index(S, kind, k, units):
    """Return n (1-based samples drawn) per unit-perm for a base policy."""
    U = S["v1"].shape[0]
    if kind == "uniform":
        return np.full((U, R), k)
    if kind == "asc":
        v1, v2 = S["v1"], S["v2"]
        prob = 1.0 - betainc(v1 + 1, v2 + 1, 0.5)  # P(p1 > p2) under Beta(v1+1, v2+1)
        ok = prob >= k
        ok[:, :, 0] = False  # min 2 samples
        n = np.where(ok.any(-1), ok.argmax(-1) + 1, NMAX)
        return n
    if kind == "esc":
        w = k
        n = np.full((U, R), NMAX)
        for u, un in enumerate(units):
            for r in range(R):
                seq = un["codes"][S["perm"][u, r]]
                for end in range(w, NMAX + 1, w):
                    if len(set(seq[end - w:end])) == 1:
                        n[u, r] = end
                        break
        return n
    raise ValueError(kind)


def apply_cap(S, n, cap):
    if cap is None:
        return n
    within = (S["ct"] <= cap).sum(-1)  # largest n with cumtok <= cap
    return np.maximum(1, np.minimum(n, within))


def outcome(S, n):
    idx = (n - 1)[..., None]
    return np.take_along_axis(S["lc"], idx, -1)[..., 0].astype(float), np.take_along_axis(S["ct"], idx, -1)[..., 0]


def frontier_tokens_at(points, target):
    """points: list of (tokens, acc). Pareto lower envelope with linear interpolation; tokens to reach target."""
    pts = sorted(points)
    front = []
    for tk, ac in pts:
        if not front or ac > front[-1][1]:
            front.append((tk, ac))
    if target <= front[0][1]:
        return front[0][0]
    for (t0, a0), (t1, a1) in zip(front, front[1:]):
        if a0 < target <= a1:
            return t0 + (t1 - t0) * (target - a0) / (a1 - a0)
    return float("nan")  # unreachable


def main(d, out):
    log = {}
    t = load(d)
    log["rows"], log["models"], log["problems"] = len(t), t["model_key"].nunique(), t[["task", "data_id"]].drop_duplicates().shape[0]
    units = build_units(t, log)
    S, sc80w = sequences(units)
    U = len(units)
    med = float(np.median(np.concatenate([u["tok"] for u in units])))
    caps = [None] + [m * med * 8 for m in CAP_MULTS]
    log["median_sample_tokens"], log["sc80_wrong_rate"] = med, float(sc80w.mean())

    base = [("uniform", k) for k in UNIFORM] + [("asc", k) for k in TAUS] + [("esc", k) for k in WINDOWS]
    policies, acc_u, tok_u = [], [], []  # per policy: per-unit means over perms
    base_n = {b: stop_index(S, *b, units) for b in base}
    for b in base:
        for c in caps:
            n = apply_cap(S, base_n[b], c)
            a, tk = outcome(S, n)
            policies.append(dict(base=b, cap=c, n=n))
            acc_u.append(a.mean(1)); tok_u.append(tk.mean(1))
    acc_u, tok_u = np.array(acc_u), np.array(tok_u)  # [P, U]
    keep = ~sc80w
    pid = [i for i, p in enumerate(policies) if p["base"] == ("asc", 0.95) and p["cap"] is None][0]

    problems = sorted({u["problem"] for u in units})
    prob_idx = np.array([problems.index(u["problem"]) for u in units])

    def headroom(w_units, sel=None):
        sel = np.ones(U, bool) if sel is None else sel
        w = w_units * sel
        W = w.sum()
        accB, tokB = (acc_u * w).sum(1) / W, (tok_u * w).sum(1) / W
        accO, tokO = (acc_u * w * keep).sum(1) / W, (tok_u * w * keep).sum(1) / W
        target = accB[pid]
        if np.nanmax(accB) < target:
            target = np.nanmax(accB)
        # Amendment A1 (pre-data): if O_abandon cannot reach A*, compare both frontiers at its max accuracy
        target = min(target, float(np.nanmax(accO)))
        tb = frontier_tokens_at(list(zip(tokB, accB)), target)
        to = frontier_tokens_at(list(zip(tokO, accO)), target)
        return target, tb, to, 1 - to / tb, accB, tokB

    A, TB, TO, H, accB, tokB = headroom(np.ones(U))
    A_asc = float(accB[pid])
    res = dict(log=log, A_star=A, A_star_asc_default=A_asc, tokens_B=TB, tokens_O_abandon=TO, H=H)

    # bootstrap over problems
    rng = np.random.default_rng(BOOT_SEED)
    hs = []
    for _ in range(NBOOT):
        cnt = np.bincount(rng.integers(0, len(problems), len(problems)), minlength=len(problems))
        hs.append(headroom(cnt[prob_idx].astype(float))[3])
    hs = np.array(hs)
    res["H_ci95"] = [float(np.nanpercentile(hs, 2.5)), float(np.nanpercentile(hs, 97.5))]

    # per-model headroom (context)
    res["per_model"] = {}
    for m in sorted({u["model"] for u in units}):
        sel = np.array([u["model"] == m for u in units])
        a, tb, to, h, _, _ = headroom(np.ones(U), sel)
        res["per_model"][m] = dict(A_star=a, H=h, sc80_wrong=float(sc80w[sel].mean()), tokens_B=tb)

    # P*: cheapest frontier policy with acc >= A*
    cand = [i for i in range(len(policies)) if accB[i] >= A - 1e-12]
    pstar = min(cand, key=lambda i: tokB[i])
    a_star_u, t_star_u = outcome(S, policies[pstar]["n"])  # [U, R]
    t_star_u = np.maximum(t_star_u, S["ct"][:, :, K_FEAT - 1])  # 4 samples are drawn to decide
    res["P_star"] = dict(base=list(policies[pstar]["base"]), cap=policies[pstar]["cap"], acc=float(accB[pstar]), tokens=float(tokB[pstar]))

    # features
    models = sorted({u["model"] for u in units}); tasks = sorted({u["task"] for u in units})
    onehot_m = np.array([[u["model"] == m for m in models] for u in units], float)
    onehot_t = np.array([[u["task"] == x for x in tasks] for u in units], float)
    F4 = np.zeros((U, R, 7))
    for u, un in enumerate(units):
        for r in range(R):
            p = S["perm"][u, r][:K_FEAT]
            c = un["codes"][p]
            _, counts = np.unique(c, return_counts=True)
            q = counts / counts.sum()
            F4[u, r] = [len(counts), counts.max() / K_FEAT, -(q * np.log(q)).sum(), un["none"][p].mean(),
                        un["tok"][p].mean(), un["tok"][p].max(), un["trunc"][p].mean()]
    X4 = np.concatenate([F4.reshape(U * R, -1), np.repeat(onehot_m, R, 0)], 1)
    X0u = np.concatenate([onehot_m, onehot_t, np.array([[u["prompt"]] for u in units])], 1)
    y_u = sc80w.astype(int)
    groups_u = prob_idx

    def realized(X, per_perm, decide_cost):
        """CV grouped by problem; returns held-out token reduction vs TB, accuracy change, AUROC."""
        y = np.repeat(y_u, R) if per_perm else y_u
        g = np.repeat(groups_u, R) if per_perm else groups_u
        a_ref = a_star_u.reshape(-1) if per_perm else a_star_u.mean(1)
        t_ref = t_star_u.reshape(-1) if per_perm else t_star_u.mean(1)
        c_ab = decide_cost.reshape(-1) if per_perm else np.zeros(U)
        prob = np.zeros(len(y)); dec = np.zeros(len(y), bool)
        for tr, te in GroupKFold(5).split(X, y, g):
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
            prob[te], dec[te] = pte, pte >= best_q
        acc = np.where(dec, 0, a_ref).mean(); tok = np.where(dec, c_ab, t_ref).mean()
        return dict(reduction_vs_B=float(1 - tok / TB), accuracy=float(acc), accuracy_change_vs_A_star=float(acc - A),
                    auroc=float(roc_auc_score(y, prob)), abandon_rate=float(dec.mean()))

    res["R4"] = realized(X4, True, S["ct"][:, :, K_FEAT - 1])
    res["S0"] = realized(X0u, False, None)

    # context oracles
    grid = [0] + list(range(1, NMAX + 1))
    pn = np.concatenate([np.zeros((U, 1)), S["lc"].mean(1)], 1)
    tn = np.concatenate([np.zeros((U, 1)), S["ct"].mean(1)], 1)
    lo, hi = 0.0, 1.0
    for _ in range(60):
        lam = (lo + hi) / 2
        ch = (pn - lam * tn / TB).argmax(1)
        if pn[np.arange(U), ch].mean() >= A: lo = lam
        else: hi = lam
    ch = (pn - lo * tn / TB).argmax(1)
    res["O_diff"] = dict(acc=float(pn[np.arange(U), ch].mean()), tokens=float(tn[np.arange(U), ch].mean()),
                         reduction_vs_B=float(1 - tn[np.arange(U), ch].mean() / TB))
    first = np.where(S["lc"].any(-1), S["lc"].argmax(-1), -1)
    hind_tok = np.where(first >= 0, np.take_along_axis(S["ct"], np.maximum(first, 0)[..., None], -1)[..., 0], 0)
    res["O_hind"] = dict(acc=float((first >= 0).mean()), tokens=float(hind_tok.mean()))

    g1 = res["H_ci95"][0] >= 0.20
    g2 = res["R4"]["auroc"] >= 0.70 and res["R4"]["reduction_vs_B"] >= 0.10 and res["R4"]["accuracy_change_vs_A_star"] >= -0.005
    g3 = res["R4"]["reduction_vs_B"] - res["S0"]["reduction_vs_B"] >= 0.10
    res["gates"] = dict(G1=g1, G2=g2, G3=g3, PASS=bool(g1 and g2 and g3))
    json.dump(res, open(out, "w"), indent=1, default=float)
    print(json.dumps({k: res[k] for k in ["A_star", "tokens_B", "tokens_O_abandon", "H", "H_ci95", "P_star", "R4", "S0", "O_diff", "O_hind", "gates"]}, indent=1, default=float))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
