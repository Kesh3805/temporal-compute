"""TC-IA2 candidate estimators. Each takes a testbed.Frame and returns an (H, W) estimate.

Only legal runtime information is used: the frame's own samples. No reference, no true parameters.
"""

from __future__ import annotations

import numpy as np

from testbed import R, from_regions


def _hw(fr):
    return fr.img["H"], fr.img["W"]


def est_mean(fr):
    return from_regions(np.stack([s.mean(0, dtype=np.float64) for s in fr.samples]), *_hw(fr))


def est_mon(fr, K=8):
    """Median of K block means per pixel (robust, biased for skewed data, consistent as blocks grow)."""
    out = []
    for s in fr.samples:
        n = (len(s) // K) * K
        out.append(np.median(s[:n].reshape(K, -1, s.shape[1]).mean(1), 0))
    return from_regions(np.stack(out), *_hw(fr))


def est_clamp(fr, tau=10.0):
    """Clamp each sample at tau x the pixel's sample median (simple firefly suppression; biased)."""
    out = []
    for s in fr.samples:
        t = tau * np.median(s, 0)
        out.append(np.minimum(s, t).mean(0, dtype=np.float64))
    return from_regions(np.stack(out), *_hw(fr))


def est_box3(fr):
    """3x3 spatial box filter of the sample mean: negative control that pays edge/texture bias."""
    m = est_mean(fr)
    p = np.pad(m, 1, mode="edge")
    return sum(p[i:i + m.shape[0], j:j + m.shape[1]] for i in range(3) for j in range(3)) / 9.0


def est_b1(fr):
    """ChatGPT's preregistered B1: cross-fitted adaptive winsorization, frozen constants (8, 1/4, n0 = 32).

    Per pixel, split samples chronologically into odd/even halves A, B. Scale per half:
    s_H = max(median(H), 1.4826 * MAD(H), 1e-12); threshold T_H = 8 * s_H * (n/32)^(1/4).
    Clip A at T_B and B at T_A; average all clipped samples. For n < 32 use the plain mean.
    """
    out = []
    for s in fr.samples:
        n = len(s)
        if n < 32:
            out.append(s.mean(0, dtype=np.float64))
            continue
        halves = (s[0::2], s[1::2])
        thr = []
        for h in halves:
            med = np.median(h, 0)
            mad = np.median(np.abs(h - med), 0)
            thr.append(8.0 * np.maximum(np.maximum(med, 1.4826 * mad), 1e-12) * (n / 32.0) ** 0.25)
        clipped = (np.minimum(halves[0], thr[1]).sum(0, dtype=np.float64)
                   + np.minimum(halves[1], thr[0]).sum(0, dtype=np.float64))
        out.append(clipped / n)
    return from_regions(np.stack(out), *_hw(fr))


def _halves_stats(h):
    med = np.median(h, 0)
    scale = 1.4826 * np.median(np.abs(h - med), 0) + 1e-4 * med
    return med, np.maximum(scale, 1e-12)


def est_gem_b1(fr):
    """Gemini's preregistered B1: two-fold cross-fitted MAD winsorization, T = M + 3 S (n/16)^(1/3)."""
    out = []
    for s in fr.samples:
        n = len(s)
        A, B = s[0::2], s[1::2]
        (mA, sA), (mB, sB) = _halves_stats(A), _halves_stats(B)
        g = (n / 16.0) ** (1 / 3)
        tA, tB = mA + 3.0 * sA * g, mB + 3.0 * sB * g
        out.append((np.minimum(B, tA).sum(0) + np.minimum(A, tB).sum(0)) / n)
    return from_regions(np.stack(out), *_hw(fr))


def est_gem_b2(fr):
    """Gemini's preregistered B2: cross-fitted one-sided Catoni log-influence above the other half's median.

    alpha = sqrt(2 log(n) / n) / S; y > M is mapped to M + log(1 + a d + a^2 d^2 / 2) / a with d = y - M.
    """
    out = []
    for s in fr.samples:
        n = len(s)
        A, B = s[0::2], s[1::2]
        tot = np.zeros(s.shape[1])
        for src, dst in ((A, B), (B, A)):
            m, sc = _halves_stats(src)
            a = np.sqrt(2 * np.log(n) / n) / sc
            d = np.maximum(dst - m, 0)
            mapped = m + np.log1p(a * d + 0.5 * (a * d) ** 2) / a
            tot += np.where(dst > m, mapped, dst).sum(0)
        out.append(tot / n)
    return from_regions(np.stack(out), *_hw(fr))


BASE = {"mean": est_mean, "gpt_b1": est_b1, "gem_b1": est_gem_b1, "gem_b2": est_gem_b2,
        "mon8": est_mon, "clamp10": est_clamp, "box3": est_box3}
