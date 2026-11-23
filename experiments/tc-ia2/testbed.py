"""TC-IA2 synthetic testbed: estimators on structured images with heavy-tailed, footprint-correlated spikes.

Exploratory and non-primary. It uses no TC-R1 scene, reference or outcome.

Image: H x W pixels in 16x16 regions. The true mean image has a smooth gradient, hard edges and texture, so a
spatial estimator pays its real bias. Each sample at pixel x is base(x) * lognormal noise + spike, where spikes
live in "caustic" blobs, fire with probability p per sample, and are shared by every pixel of a k x k footprint
block within that sample (marginals per pixel are unchanged by k).

Allocation is fixed across estimators: plug-in cost-aware Neyman on region variance with the 0.5 floor, driven
by the sample mean's statistics. Every estimator sees exactly the same samples (paired comparison).
"""

from __future__ import annotations

import numpy as np

R = 16  # region side
BATCH, INIT, ALPHA = 4, 16, 0.5
DTYPE = np.float64  # sample storage; E2 switches to float32 to fit 16384 spp in memory


def make_image(rng, H=128, W=128, family="caustic", k=1, cost_sd=0.52, fixed_p=None):
    yy, xx = np.mgrid[0:H, 0:W] / max(H, W)
    g = rng.normal(size=3)
    base = np.exp(0.6 * (g[0] * xx + g[1] * yy) + 0.3 * g[2] * xx * yy)
    # hard edges: a few random half-planes scaling radiance up or down
    for _ in range(3):
        a, b, c = rng.normal(size=3)
        base *= np.where(a * (xx - 0.5) + b * (yy - 0.5) + 0.2 * c > 0, rng.uniform(1.5, 4.0), 1.0)
    # texture: high-frequency checker with random amplitude
    period = rng.integers(2, 6)
    base *= 1 + rng.uniform(0.1, 0.4) * np.sign(np.sin(np.pi * np.arange(W) / period)[None, :]
                                                 * np.sin(np.pi * np.arange(H) / period)[:, None])
    s = rng.uniform(0.3, 0.8)  # lognormal shape of the base noise
    p = np.zeros((H, W))
    M = np.zeros((H, W))
    if family != "diffuse":
        nblobs = 3 if family == "caustic" else 6
        for _ in range(nblobs):
            cy, cx = rng.uniform(0, 1, 2)
            rad = rng.uniform(0.05, 0.15)
            blob = ((yy - cy) ** 2 + (xx - cx) ** 2) < rad**2
            pv = fixed_p if fixed_p else 10 ** rng.uniform(-4, -2)
            q = rng.uniform(0.5, 0.95)  # share of the pixel variance carried by the spike
            base_var = (np.exp(s**2) - 1) * base**2
            p[blob] = pv
            M[blob] = np.sqrt(q / (1 - q) * base_var[blob] / pv)
    nr = (H // R) * (W // R)
    logc = rng.normal(0, cost_sd, nr)
    if family == "mixed":
        hot = p.reshape(H // R, R, W // R, R).max((1, 3)).ravel() > 0
        logc += 0.5 * hot
    c = np.exp(logc - logc.mean())
    mu = base + p * M  # E[lognormal(-s^2/2, s)] = 1, so the base mean is `base`
    var = (np.exp(s**2) - 1) * base**2 + M**2 * p * (1 - p)
    return dict(H=H, W=W, k=k, s=s, base=base, p=p, M=M, c=c, mu=mu, var=var)


def to_regions(a, H, W):
    """(H, W) -> (n_regions, R*R) with pixels of each region contiguous."""
    return a.reshape(H // R, R, W // R, R).transpose(0, 2, 1, 3).reshape(-1, R * R)


def from_regions(a, H, W):
    return a.reshape(H // R, W // R, R, R).transpose(0, 2, 1, 3).reshape(H, W)


class Frame:
    """Holds every sample (per region: array n_r x R*R) so any estimator can be applied afterwards."""

    def __init__(self, rng, img):
        self.rng, self.img = rng, img
        H, W = img["H"], img["W"]
        self.base = to_regions(img["base"], H, W)
        self.p = to_regions(img["p"], H, W)
        self.M = to_regions(img["M"], H, W)
        self.nr = self.base.shape[0]
        self.chunks = [[] for _ in range(self.nr)]
        self.s1 = np.zeros((self.nr, R * R))
        self.s2 = np.zeros((self.nr, R * R))
        self.n = np.zeros(self.nr)
        self.spent = 0.0
        # pixel index -> footprint block within the region
        k = img["k"]
        iy, ix = np.divmod(np.arange(R * R), R)
        self.block = (iy // k) * (R // k) + ix // k
        self.nblocks = (R // k) ** 2
        for r in range(self.nr):
            self.buy(r, INIT)

    def buy(self, r, n):
        s = self.img["s"]
        y = self.base[r] * self.rng.lognormal(-s * s / 2, s, (n, R * R))
        if self.p[r].max() > 0:
            u = self.rng.random((n, self.nblocks))[:, self.block]  # one draw per footprint block
            y = y + self.M[r] * (u < self.p[r])
        self.chunks[r].append(y.astype(DTYPE, copy=False))
        self.s1[r] += y.sum(0)
        self.s2[r] += (y * y).sum(0)
        self.n[r] += n
        self.spent += n * R * R * self.img["c"][r]

    def region_var(self):
        n = self.n[:, None]
        return np.maximum((self.s2 - self.s1**2 / n) / (n - 1), 0).mean(1)

    @property
    def samples(self):
        """Per region, every sample so far as an (n_r, R*R) array (compacted on access)."""
        for r, ch in enumerate(self.chunks):
            if len(ch) > 1:
                self.chunks[r] = [np.vstack(ch)]
        return [ch[0] for ch in self.chunks]


def run_frame(seed, img, checkpoints, estimators):
    """Progress one frame with the fixed allocator; at each checkpoint apply every estimator."""
    rng = np.random.default_rng(seed)
    fr = Frame(rng, img)
    H, W = img["H"], img["W"]
    mu = img["mu"]
    energy = (mu**2).mean()
    c = img["c"]
    out = {name: [] for name in estimators}
    for cp in checkpoints:
        while fr.spent < cp * H * W:
            if (fr.n < ALPHA * fr.n.mean()).any():
                low = np.where(fr.n < ALPHA * fr.n.mean())[0]
                r = low[np.argmin(fr.n[low])]
            else:
                v = fr.region_var()
                r = int(np.argmax(v / (fr.n * (fr.n + BATCH) * c)))
            fr.buy(r, BATCH)
        for name, est in estimators.items():
            e = est(fr)  # (H, W) estimate
            err = (e - mu) ** 2
            reg = to_regions(err, H, W).mean(1) / np.maximum(to_regions(mu**2, H, W).mean(1), 1e-12)
            out[name].append((float(err.mean() / energy), float(reg.max())))
    return out


# ---- estimators -----------------------------------------------------------------

def est_mean(fr):
    return from_regions(np.stack([s.mean(0) for s in fr.samples]), fr.img["H"], fr.img["W"])
