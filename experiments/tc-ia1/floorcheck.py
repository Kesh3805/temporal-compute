"""Check amendment 0004's '2x uniform' rationale for the 0.5 floor under unequal costs."""
import numpy as np
from sim import POLICIES, State, make_scene, floor_bound, ALPHA, BATCH

def final_counts(policy, sc, seed, cp=256, P=16):
    rng = np.random.default_rng(seed)
    st = State(rng, sc, P)
    idx, floored = POLICIES[policy]
    ctx = {"S": float(np.sqrt(np.median(st.var_hat())))}
    while st.spent < cp * P * sc["K"]:
        low = np.where(st.n < ALPHA * st.n.mean())[0] if floored else []
        r = low[np.argmin(st.n[low])] if len(low) else int(np.argmax(idx(st, ctx)))
        st.buy(r, BATCH)
    return st.n

rng = np.random.default_rng(7)
for fam in ("diffuse", "caustic", "mixed"):
    for pol in ("variance", "mcucb", "costaware"):
        bs = []
        for s in range(6):
            sc = make_scene(rng, fam, cost_sd=1.0)
            bs.append(floor_bound(final_counts(pol, sc, s), sc["c"]))
        print(f"{fam:8s} {pol:10s} implied worst-case ratio to uniform: median {np.median(bs):.2f}  max {max(bs):.2f}  (2.00 claimed)")
