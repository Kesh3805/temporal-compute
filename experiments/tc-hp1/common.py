"""TC-HP1 shared machinery — implements docs/tc-hp1/preregistration.md (commit ea9c58c).

Implementation clarification, fixed before any held-out data is read: oracle targets are found by bisection
over a fixed 401-point lambda grid (0 plus logspace(-4, 3, 400)), followed by linear interpolation between the
two bracketing grid points on the cost axis. This gives bootstrap resamples the same oracle as the point estimate
without re-solving per resample.
"""
import json, re
import numpy as np
from scipy.special import betainc
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

NMAX, R, PERM_SEED, BOOT_SEED, NBOOT, K_FEAT = 80, 20, 20261121, 734923, 2000, 4
TAUS = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99]
WINDOWS = [2, 4, 8]
LAMBDAS = np.concatenate([[0.0], np.logspace(-4, 3, 400)])
SHUFFLE_SEED, PREFIX, NBLOCKS = 20261122, 0.10, 50
PRICES = {"cheap": (0.15, 0.60), "strong": (2.50, 10.00)}  # $/M tokens (in, out)


# ---------------------------------------------------------------- answer extraction
def _last_boxed(t):
    i = t.rfind("\\boxed")
    if i < 0:
        return None
    j = t.find("{", i)
    if j < 0:
        return None
    depth, k = 0, j
    while k < len(t):
        if t[k] == "{":
            depth += 1
        elif t[k] == "}":
            depth -= 1
            if depth == 0:
                return re.sub(r"\s+", "", t[j + 1:k]) or None
        k += 1
    return None


_NUM = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


def _norm_num(s):
    s = s.replace(",", "")
    if s.endswith(".0"):
        s = s[:-2]
    return s


def extract(text, kind):
    if kind == "MATH":
        return _last_boxed(text)
    i = text.rfind("answer is")
    if i >= 0:
        m = _NUM.search(text, i)
        if m:
            return _norm_num(m.group())
    ms = _NUM.findall(text)
    return _norm_num(ms[-1]) if ms else None


def mb_units(rows, kind):
    """rows: list of dicts with samples (first NMAX), is_corrects (first NMAX), question."""
    units = []
    for q, r in enumerate(rows):
        ans = [extract(s, kind) for s in r["samples"][:NMAX]]
        labels = {}
        for a, c in zip(ans, r["is_corrects"][:NMAX]):
            if a is not None:
                labels.setdefault(a, []).append(bool(c))
        keys = sorted(labels)
        code_of = {a: i for i, a in enumerate(keys)}
        corr = np.array([sum(labels[a]) * 2 > len(labels[a]) for a in keys] + [False])  # last = no answer
        codes = np.array([code_of[a] if a is not None else -1 for a in ans])
        tok = np.array([len(s) / 4.0 for s in r["samples"][:NMAX]])
        units.append(dict(q=q, codes=codes, corr=corr, tok=tok, qlen=len(r["question"])))
    return units


# ---------------------------------------------------------------- SC machinery (as TC-01-HG; no-answer samples do not vote)
def plurality_trace(seq):
    counts, leader, out = {}, None, []
    for a in seq:
        if a >= 0:
            counts[a] = counts.get(a, 0) + 1
            if leader is None or counts[a] > counts[leader]:
                leader = a
        top = sorted(counts.values(), reverse=True)
        out.append((-1 if leader is None else leader, top[0] if top else 0, top[1] if len(top) > 1 else 0, len(counts)))
    return out


def sequences(units):
    rng = np.random.default_rng(PERM_SEED)
    U = len(units)
    S = {k: np.zeros((U, R, NMAX), t) for k, t in
         [("lc", bool), ("ct", float), ("v1", int), ("v2", int), ("nd", int), ("ld", int), ("perm", int)]}
    sc80_wrong, lead80 = np.zeros(U, bool), np.zeros(U, int)
    for u, un in enumerate(units):
        l80 = plurality_trace(un["codes"])[-1][0]
        sc80_wrong[u] = not un["corr"][l80]  # corr[-1] is False for "no answer"
        for r in range(R):
            p = rng.permutation(NMAX)
            S["perm"][u, r] = p
            tr = plurality_trace(un["codes"][p])
            S["ld"][u, r] = [x[0] for x in tr]
            S["lc"][u, r] = [un["corr"][x[0]] for x in tr]
            S["v1"][u, r] = [x[1] for x in tr]
            S["v2"][u, r] = [x[2] for x in tr]
            S["nd"][u, r] = [x[3] for x in tr]
            S["ct"][u, r] = np.cumsum(un["tok"][p])
    return S, sc80_wrong


def stop_index(S, kind, k, units):
    U = S["v1"].shape[0]
    if kind == "uniform":
        return np.full((U, R), k)
    if kind == "asc":
        prob = 1.0 - betainc(S["v1"] + 1, S["v2"] + 1, 0.5)
        ok = (prob >= k) & (S["v1"] > 0)
        ok[:, :, 0] = False
        return np.where(ok.any(-1), ok.argmax(-1) + 1, NMAX)
    if kind == "esc":
        n = np.full((U, R), NMAX)
        for u, un in enumerate(units):
            for r in range(R):
                seq = un["codes"][S["perm"][u, r]]
                for end in range(k, NMAX + 1, k):
                    win = set(seq[end - k:end])
                    if len(win) == 1 and -1 not in win:
                        n[u, r] = end
                        break
        return n
    raise ValueError(kind)


def outcome(S, n):
    idx = (n - 1)[..., None]
    return (np.take_along_axis(S["lc"], idx, -1)[..., 0].astype(float),
            np.take_along_axis(S["ct"], idx, -1)[..., 0])


def frontier_cost_at(points, target):
    """Pareto lower envelope of (cost, quality); cost to reach target; NaN if unreachable (no endpoint fallback)."""
    pts = sorted((float(c), float(q)) for c, q in points if np.isfinite(c) and np.isfinite(q))
    front = []
    for c, q in pts:
        if not front or q > front[-1][1] + 1e-15:
            front.append((c, q))
    if not front:
        return float("nan")
    if target <= front[0][1]:
        return front[0][0]
    for (c0, q0), (c1, q1) in zip(front, front[1:]):
        if q0 < target <= q1:
            return c0 + (c1 - c0) * (target - q0) / (q1 - q0)
    return float("nan")


def lambda_curve_cost(qual_l, cost_l, target):
    """qual_l/cost_l: oracle quality and cost per LAMBDAS entry (quality non-increasing in lambda).
    Bisection over the grid, then interpolation between bracketing points."""
    if qual_l[0] < target - 1e-12:
        return float("nan")
    lo, hi = 0, len(LAMBDAS) - 1
    if qual_l[hi] >= target:
        return float(cost_l[hi])
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if qual_l[mid] >= target:
            lo = mid
        else:
            hi = mid
    q0, q1, c0, c1 = qual_l[lo], qual_l[hi], cost_l[lo], cost_l[hi]
    if q0 == q1:
        return float(c0)
    return float(c1 + (c0 - c1) * (target - q1) / (q0 - q1))


def weighted_mean(x, w):
    return (x * w).sum(-1) / w.sum()


def bootstrap_groups(n_groups, seed=BOOT_SEED, nboot=NBOOT):
    rng = np.random.default_rng(seed)
    for _ in range(nboot):
        yield np.bincount(rng.integers(0, n_groups, n_groups), minlength=n_groups).astype(float)


def cv_auroc(X, y, groups):
    prob = np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, groups):
        sc = StandardScaler().fit(X[tr])
        clf = LogisticRegression(max_iter=2000).fit(sc.transform(X[tr]), y[tr])
        prob[te] = clf.predict_proba(sc.transform(X[te]))[:, 1]
    return float(roc_auc_score(y, prob)), prob


def first4_features(S, units):
    U = len(units)
    F = np.zeros((U, R, 5))
    for u, un in enumerate(units):
        for r in range(R):
            c = un["codes"][S["perm"][u, r][:K_FEAT]]
            v = c[c >= 0]
            if len(v):
                _, cnt = np.unique(v, return_counts=True)
                q = cnt / cnt.sum()
                ent = -(q * np.log(q)).sum()
            else:
                ent = 0.0
            F[u, r] = [S["v1"][u, r, K_FEAT - 1], S["v2"][u, r, K_FEAT - 1], S["nd"][u, r, K_FEAT - 1], ent,
                       (c < 0).mean()]
    return F


def quintile_bins(units):
    ql = np.array([u["qlen"] for u in units], float)
    edges = np.quantile(ql, [0.2, 0.4, 0.6, 0.8])
    return np.searchsorted(edges, ql, side="right")


# ---------------------------------------------------------------- SPROUT
def sprout_stream(df, pair):
    df = df.dropna(subset=["s_cheap", "s_strong"]).copy()
    if pair == "P5":
        df = df.sort_values(["dataset", "dataset_idx"], kind="mergesort")
    else:
        df = df.iloc[np.random.default_rng(SHUFFLE_SEED).permutation(len(df))]
    df = df.reset_index(drop=True)
    for m in ("cheap", "strong"):
        pi, po = PRICES[m]
        df["c_" + m] = (df["in_" + m] * pi + df["out_" + m] * po) / 1e6
    df["delta"] = df["s_strong"] - df["s_cheap"]
    n_pre = int(np.floor(PREFIX * len(df)))
    return df, n_pre


def tie_jitter(n):
    """Amendment A1 (pre-data): seeded 1e-9 jitter so tied router estimates can be split at any quantile."""
    return 1e-9 * np.random.default_rng(SHUFFLE_SEED + 1).random(n)


def static_estimates(df, n_pre):
    pre = df.iloc[:n_pre]
    means = pre.groupby("dataset")["delta"].mean()
    g = pre["delta"].mean()
    return df["dataset"].map(means).fillna(g).to_numpy() + tie_jitter(len(df))


def online_estimates(df):
    est = np.zeros(len(df))
    s, c, gs, gc = {}, {}, 0.0, 0
    for i, (cat, d) in enumerate(zip(df["dataset"].to_numpy(), df["delta"].to_numpy())):
        est[i] = s[cat] / c[cat] if c.get(cat) else (gs / gc if gc else 0.0)
        s[cat] = s.get(cat, 0.0) + d
        c[cat] = c.get(cat, 0) + 1
        gs += d
        gc += 1
    return est + tie_jitter(len(df))


def route_points(df, est, n_pre, lams):
    post = df.iloc[n_pre:]
    e = est[n_pre:]
    pts = []
    for lam in lams:
        strong = e > lam
        q = np.where(strong, post["s_strong"], post["s_cheap"]).mean()
        c = np.where(strong, post["c_strong"], post["c_cheap"]).mean()
        pts.append((c, q))
    return pts


def router_lams(est, n_pre):
    return np.percentile(est[n_pre:], np.linspace(2.5, 97.5, 39))


def sprout_B(df, n_pre):
    est = static_estimates(df, n_pre)
    lam = float(np.percentile(est[:n_pre], 70))
    (c, q), = route_points(df, est, n_pre, [lam])
    return q, c, est, lam


def dump(obj, path):
    json.dump(obj, open(path, "w"), indent=1, default=float)
