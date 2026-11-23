"""TC-IA1 synthetic testbed: progressive region allocation on heavy-tailed strata.

Exploratory and non-primary. It uses no TC-R1 scene, reference or outcome.

Model. An image has K regions of P pixels. Every pixel in region r draws iid
samples Y = base + rare, where base is lognormal and rare is a Bernoulli(p_r)
spike of size M_r (the firefly/caustic term). A sample in region r costs c_r
rays. Image relative MSE = mean over pixels of (pixel mean - true mean)^2,
divided by mean true energy. Policies see only per-pixel sums of the samples
they bought, as in TC-R1 (within-pixel variance averaged over the region).
"""

from __future__ import annotations

import numpy as np

BATCH = 4  # spp per request, as in TC-R1
INIT = 16  # common initialization spp
ALPHA = 0.5  # shared defensive floor (amendment 0004)


def make_scene(rng, family, K=64, cost_sd=0.5):
    """Draw region parameters for one synthetic scene of a given family."""
    m = rng.normal(0.0, 0.5, K)
    s = rng.uniform(0.3, 1.0, K)
    p = np.zeros(K)
    M = np.zeros(K)
    if family in ("caustic", "mixed"):
        frac = 0.2 if family == "caustic" else 0.4
        hot = rng.random(K) < frac
        p[hot] = 10 ** rng.uniform(-4, -2, hot.sum())
        base_var = (np.exp(s**2) - 1) * np.exp(2 * m + s**2)
        # rare term carries a share q of the region variance: M^2 p = q/(1-q) * base_var
        q = rng.uniform(0.3, 0.95, K)
        M[hot] = np.sqrt(q[hot] / (1 - q[hot]) * base_var[hot] / p[hot])
    logc = rng.normal(0.0, cost_sd, K)
    if family == "mixed":
        logc += 0.5 * (p > 0)  # specular paths are longer
    c = np.exp(logc - logc.mean())
    mu = np.exp(m + s**2 / 2) + p * M
    var = (np.exp(s**2) - 1) * np.exp(2 * m + s**2) + M**2 * p * (1 - p)
    return dict(m=m, s=s, p=p, M=M, c=c, mu=mu, var=var, K=K)


def draw(rng, sc, r, n, P):
    y = rng.lognormal(sc["m"][r], sc["s"][r], (n, P))
    if sc["p"][r] > 0:
        # a spike is shared by every pixel of its footprint block; marginals are unchanged
        blocks = max(P // sc.get("foot", 1), 1)
        hit = rng.random((n, blocks)) < sc["p"][r]
        y += sc["M"][r] * np.repeat(hit, P // blocks, axis=1)
    return y


class State:
    def __init__(self, rng, sc, P):
        K = sc["K"]
        self.sc, self.P, self.rng = sc, P, rng
        self.n = np.zeros(K)
        self.s1 = np.zeros((K, P))
        self.s2 = np.zeros((K, P))
        self.spent = 0.0
        for r in range(K):
            self.buy(r, INIT)

    def buy(self, r, n):
        y = draw(self.rng, self.sc, r, n, self.P)
        self.s1[r] += y.sum(0)
        self.s2[r] += (y * y).sum(0)
        self.n[r] += n
        self.spent += n * self.P * self.sc["c"][r]

    def var_hat(self):
        """Registered-style scalar: within-pixel sample variance averaged over the region."""
        n = self.n[:, None]
        v = (self.s2 - self.s1**2 / n) / (n - 1)
        return np.maximum(v, 0).mean(1)

    def rel_mse(self):
        err = self.s1 / self.n[:, None] - self.sc["mu"][:, None]
        return float((err**2).mean() / (self.sc["mu"] ** 2).mean())


# ---- policies: each returns the index to maximise, given state --------------

def idx_uniform(st, ctx):
    return -st.n


def idx_variance(st, ctx):
    v = st.var_hat()
    return v / (st.n * (st.n + BATCH))


def idx_mcucb(st, ctx):
    v = st.var_hat()
    return (np.sqrt(v) + 2.0 * ctx["S"] / np.sqrt(st.n)) / st.n


def idx_costaware(st, ctx):
    v = st.var_hat()
    return v / (st.n * (st.n + BATCH) * st.sc["c"])


def idx_oracle(st, ctx):
    v = st.sc["var"]
    return v / (st.n * (st.n + BATCH) * st.sc["c"])


def _pixel_var(st):
    n = st.n[:, None]
    return np.maximum((st.s2 - st.s1**2 / n) / (n - 1), 0)


def idx_robust(st, ctx, blocks=8):
    """ChatGPT's robust-myopic ablation: median-of-means of pixel variances, cost-aware."""
    v = _pixel_var(st)
    b = min(blocks, st.P)
    v = np.median(v[:, : (st.P // b) * b].reshape(len(v), b, -1).mean(2), 1)
    return v / (st.n * (st.n + BATCH) * st.sc["c"])


def idx_skeptical(st, ctx, n0=64.0):
    """Gemini's H1: leverage-damped variance (leave-max-pixel-out blended in), cost-aware."""
    v = _pixel_var(st)
    full = v.mean(1)
    if st.P > 1:
        lmo = (v.sum(1) - v.max(1)) / (st.P - 1)
    else:
        lmo = full
    g = st.n / (st.n + n0)
    damped = np.maximum(lmo, 1e-300) ** (1 - g) * np.maximum(full, 1e-300) ** g
    return damped / (st.n * (st.n + BATCH) * st.sc["c"])


def idx_cond_oracle(st, ctx):
    """Conditional (realized-error) oracle: knows each pixel's current error and the true variance.

    Adding b fresh samples to a pixel with n samples and realized error e gives
    expected squared error (n^2 e^2 + b sigma^2) / (n + b)^2. Rank by gain per ray.
    """
    n = st.n[:, None]
    e2 = (st.s1 / n - st.sc["mu"][:, None]) ** 2
    after = (n**2 * e2 + BATCH * st.sc["var"][:, None]) / (n + BATCH) ** 2
    return (e2 - after).mean(1) / st.sc["c"]


POLICIES = {
    "uniform": (idx_uniform, False),
    "variance": (idx_variance, True),
    "mcucb": (idx_mcucb, True),
    "costaware": (idx_costaware, True),
    "robust_myopic": (idx_robust, True),
    "skeptical": (idx_skeptical, True),
    "oracle_greedy": (idx_oracle, False),
    # same true-variance index under the shared floor: separates the floor's price from information value
    "oracle_floor": (idx_oracle, True),
    "oracle_cond": (idx_cond_oracle, True),
}


def run(policy, sc, seed, checkpoints, P=64, extra=None):
    """Run one policy; return rel MSE at each cost checkpoint (cost per pixel)."""
    rng = np.random.default_rng(seed)
    st = State(rng, sc, P)
    idx, floored = extra if extra else POLICIES[policy]
    ctx = {"S": float(np.sqrt(np.median(st.var_hat())))}
    out = []
    for cp in checkpoints:
        target = cp * P * sc["K"]
        while st.spent < target:
            if floored and (st.n < ALPHA * st.n.mean()).any():
                low = np.where(st.n < ALPHA * st.n.mean())[0]
                r = low[np.argmin(st.n[low])]
            else:
                r = int(np.argmax(idx(st, ctx)))
            st.buy(r, BATCH)
        out.append(st.rel_mse())
    return out


def floor_bound(n, c, alpha=ALPHA):
    """Worst-case MSE ratio to uniform implied by n_r >= alpha*mean(n) at equal ray budget.

    Uniform spends the same rays, so its per-region count is the cost-weighted
    mean of n. The bound is (1/alpha) * cost-weighted mean / plain mean, which
    is <= 1/alpha exactly when cov(n, c) <= 0.
    """
    return (n * c).sum() / c.sum() / (alpha * n.mean())


def oracle_static_mse(sc, budget_per_pixel):
    """Expected rel MSE of the static oracle: n_r ∝ sigma_r/sqrt(c_r), n_r >= INIT."""
    K, var, c = sc["K"], sc["var"], sc["c"]
    B = budget_per_pixel * K
    fixed = np.zeros(K, bool)
    for _ in range(K):
        free = ~fixed
        Bf = B - (INIT * c[fixed]).sum()
        w = np.sqrt(var[free] / c[free])
        n = np.full(K, float(INIT))
        n[free] = Bf * w / (w * c[free]).sum()
        newly = free & (n < INIT)
        if not newly.any():
            break
        fixed |= newly
    n = np.maximum(n, INIT)
    return float((var / n).mean() / (sc["mu"] ** 2).mean())
