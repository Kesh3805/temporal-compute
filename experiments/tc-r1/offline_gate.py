"""TC-R1 offline identifiability and competence gate (contract tc-r1-offline-gate-v1).

PBRT-free. Unchanged conventional and controller policies observe RegionState
snapshots computed with the progressive kernel's statistic formulas from NumPy
per-pixel moments on synthetic noise fields. Competence uses true variances and
an oracle allocation; the controller is only compared by decision agreement.
No rendering, primary scene, reference or controller image-quality score.
"""
import argparse
import hashlib
import json
import math
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from baselines import ConventionalPolicy
from progressive_kernel import Region, RegionState, require
from tc_controller import TcPolicy

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT/'research/tc-r1/offline-gate/contract.json'
SIDE, CELL = 32, 4
REGIONS = tuple(Region(x, x+CELL, y, y+CELL) for y in range(0, SIDE, CELL) for x in range(0, SIDE, CELL))
AREA = CELL*CELL
BATCH, MINIMUM = 4, 16
CHANNELS = np.array((1.0, 0.7, 0.4))
FIELDS = ('gaussian', 'lognormal', 'rare-spike')
SCALES = (0.001, 0.01, 0.1, 1, 10, 100, 1000)
SEEDS = (0, 1, 2)
HORIZONS = (64, 256)
CONVENTIONAL = ('uniform', 'adaptive-mc-ucb-region', 'variance-guided')
LAUNCH_SECONDS, RAY_SECONDS, TIMING_SIGMA = 0.3, 1e-6, 0.1


def field_seed(field, seed):
    value = f'tc-r1-offline-gate-v1|{field}|{seed}'.encode('utf-8')
    return int.from_bytes(hashlib.sha256(value).digest()[:8], 'big')


class Field:
    """Per-region sample distributions; draws keyed by (region, batch) for common random numbers."""
    def __init__(self, field, seed, scale=1.0, rays='homogeneous'):
        require(field in FIELDS and rays in ('homogeneous', 'heterogeneous'), 'unknown field')
        self.field, self.scale, self.seed = field, float(scale), field_seed(field, seed)
        rng = np.random.default_rng(self.seed)
        count = len(REGIONS)
        self.mu = rng.uniform(0.2, 1.0, count)
        if field == 'gaussian':
            self.param = 0.5*np.exp(rng.normal(0.0, 1.0, count))
            base = self.param**2
        elif field == 'lognormal':
            self.param = rng.uniform(0.25, 1.75, count)
            base = self.mu**2*np.expm1(self.param**2)
        else:
            self.param = np.zeros(count)
            spikes = rng.choice(count, 8, replace=False)
            self.param[spikes] = rng.uniform(0.002, 0.02, 8)
            base = 0.05**2 + 200.0**2*self.param*(1-self.param)
        # True per-sample variance per region/channel, including scale.
        self.variance = (self.scale**2)*base[:, None]*CHANNELS[None, :]**2
        self.rays = (np.full(count, 2, dtype=np.int64) if rays == 'homogeneous'
                     else rng.integers(1, 18, count))

    def draw(self, region, batch):
        rng = np.random.default_rng([self.seed, region, batch])
        z = rng.standard_normal((AREA, BATCH))
        if self.field == 'gaussian':
            x = self.mu[region] + self.param[region]*z
        elif self.field == 'lognormal':
            s = self.param[region]
            x = self.mu[region]*np.exp(s*z - s*s/2)
        else:
            x = self.mu[region] + 0.05*z + 200.0*(rng.random((AREA, BATCH)) < self.param[region])
        return self.scale*x[:, :, None]*CHANNELS[None, None, :]

    def timing_factor(self, region, batch):
        return float(np.exp(TIMING_SIGMA*np.random.default_rng([self.seed, region, batch, 1]).standard_normal()))


class Simulator:
    """Kernel-equivalent region statistics from per-pixel moments (progressive_kernel.py:160-213)."""
    def __init__(self, field, cost_measures=('deterministic',)):
        count = len(REGIONS)
        self.field, self.cost_measures = field, cost_measures
        self.n = np.zeros(count, dtype=np.int64)
        self.mean = np.zeros((count, AREA, 3))
        self.m2 = np.zeros((count, AREA, 3))
        self.charges = np.zeros(count, dtype=np.int64)
        self.improvement = [None]*count
        self.cost = {m: [None]*count for m in cost_measures}
        self.version = 0

    def _stats(self, r):
        n = int(self.n[r])
        mean = tuple(float(v) for v in self.mean[r].mean(axis=0)) if n else None
        if n > 1:
            variance = tuple(float(v) for v in (self.m2[r]/(n-1)).mean(axis=0))
            stderr = tuple(float(v) for v in np.sqrt((self.m2[r]/((n-1)*n)).sum(axis=0))/AREA)
        else:
            variance = stderr = None
        return n, mean, variance, stderr

    def states(self, measure):
        result = []
        for r, region in enumerate(REGIONS):
            n, mean, variance, stderr = self._stats(r)
            result.append(RegionState(region, self.version, n*AREA, n, mean, variance, stderr,
                                      self.improvement[r], self.cost[measure][r], int(self.charges[r])))
        return tuple(result)

    def sample(self, region):
        r = REGIONS.index(region)
        before = self._stats(r)[3]
        batch = int(self.n[r])//BATCH
        x = self.field.draw(r, batch)
        n0, k = self.n[r], BATCH
        bmean = x.mean(axis=1)
        bm2 = ((x - bmean[:, None, :])**2).sum(axis=1)
        delta = bmean - self.mean[r]
        total = n0 + k
        self.mean[r] = self.mean[r] + delta*k/total
        self.m2[r] = self.m2[r] + bm2 + delta**2*n0*k/total
        self.n[r] = total
        samples = AREA*BATCH
        rays = int(self.field.rays[r])*samples
        self.charges[r] += rays
        self.version += 1
        after = self._stats(r)[3]
        self.improvement[r] = (math.fsum(v*v for v in before) - math.fsum(v*v for v in after)
                               if before is not None else None)
        for measure in self.cost_measures:
            if measure == 'deterministic':
                self.cost[measure][r] = rays/samples
            else:
                self.cost[measure][r] = ((LAUNCH_SECONDS + RAY_SECONDS*rays)*self.field.timing_factor(r, batch)
                                         / samples)


def drop_history(policy):
    # The retained diagnostic history is never read by TcPolicy's choice logic;
    # discarding it bounds memory over thousands of shadow decisions.
    policy._diagnostics.clear()


def oracle_error(weights, total, floor=MINIMUM):
    """Continuous minimum of sum w/n subject to sum n = total and n >= floor."""
    root = np.sqrt(weights)
    fixed = np.zeros(len(weights), dtype=bool)
    while True:
        free_total = total - floor*fixed.sum()
        n = np.where(fixed, floor, root*free_total/root[~fixed].sum())
        low = (~fixed) & (n < floor)
        if not low.any():
            return float((weights/n).sum())
        fixed |= low


def allocation_error(weights, spp):
    return float((weights/spp).sum())


def weights_of(field):
    return AREA*field.variance.mean(axis=1)


def run_conventional(job):
    method, field_name, scale, seed = job
    field = Field(field_name, seed, scale)
    sim = Simulator(field)
    policy = ConventionalPolicy(method)
    snapshots = {}
    marks = {h*len(REGIONS)//BATCH: h for h in HORIZONS}
    for step in range(1, max(marks)+1):
        sim.sample(policy.choose(sim.states('deterministic')).region)
        if step in marks:
            snapshots[marks[step]] = sim.n.copy()
    weights = weights_of(field)
    result = {}
    for horizon, spp in snapshots.items():
        require(int(spp.sum()) == horizon*len(REGIONS), 'allocation total mismatch')
        result[horizon] = oracle_error(weights, float(spp.sum()))/allocation_error(weights, spp)
    return dict(method=method, field=field_name, scale=scale, seed=seed,
                efficiency={str(h): v for h, v in sorted(result.items())})


def run_identifiability(job):
    field_name, seed = job
    decisions = HORIZONS[-1]*len(REGIONS)//BATCH
    variants = [('wall', 'homogeneous'), ('wall', 'heterogeneous'),
                ('deterministic', 'homogeneous'), ('deterministic', 'heterogeneous')]
    sims = {v: Simulator(Field(field_name, seed, 1, v[1]), ('wall', 'deterministic')) for v in variants}
    reference = ConventionalPolicy('variance-guided')
    shadows = {('full',)+v: TcPolicy('full') for v in variants}
    shadows[('equal-cost', 'deterministic', 'homogeneous')] = TcPolicy('equal-cost')
    counts = {k: dict(post=0, differ=0, nonexplore=0, nonexplore_differ=0) for k in shadows}
    for _ in range(decisions):
        # Variance-guided ignores cost and ray fields: one shared trajectory.
        base = sims[variants[0]]
        choice = reference.choose(base.states('wall')).region
        post = min(base.n) >= MINIMUM
        for key, policy in shadows.items():
            sim = sims[key[1:]]
            shadow = policy.choose(sim.states(key[1])).region
            reason = policy.diagnostics['reason']
            drop_history(policy)
            if post:
                c = counts[key]
                c['post'] += 1
                c['differ'] += shadow != choice
                if reason != 'exploration':
                    c['nonexplore'] += 1
                    c['nonexplore_differ'] += shadow != choice
        for sim in sims.values():
            sim.sample(choice)
    for sim in sims.values():
        require(np.array_equal(sim.n, base.n), 'shared trajectory diverged')
    # No-feedback ablation on its own trajectory, deterministic heterogeneous cost.
    own = Simulator(Field(field_name, seed, 1, 'heterogeneous'))
    policy = TcPolicy('no-feedback')
    for _ in range(decisions):
        own.sample(policy.choose(own.states('deterministic')).region)
        drop_history(policy)
    tv = 0.5*float(np.abs(own.n/own.n.sum() - base.n/base.n.sum()).sum())
    rates = {'|'.join(k): dict(d=c['differ']/c['post'], d_nonexplore=c['nonexplore_differ']/c['nonexplore'],
                               post_decisions=c['post'])
             for k, c in counts.items()}
    return dict(field=field_name, seed=seed, rates=rates, no_feedback_total_variation=tv)


def evaluate(conventional, identifiability):
    def mean(values):
        return float(np.mean(values))
    eta = {}
    for row in conventional:
        for horizon, value in row['efficiency'].items():
            eta.setdefault((row['method'], row['field'], row['scale'], horizon), []).append(value)
    eta = {k: mean(v) for k, v in eta.items()}
    competence = {}
    for method in CONVENTIONAL[1:]:
        failures = []
        for field in FIELDS:
            for horizon in map(str, HORIZONS):
                values = []
                for scale in SCALES:
                    m, u = eta[(method, field, scale, horizon)], eta[('uniform', field, scale, horizon)]
                    values.append(m)
                    where = f'{field}/scale={scale}/h={horizon}'
                    if field != 'rare-spike':
                        if m < 0.80:
                            failures.append(f'C1 {where}: {m:.4f} < 0.80')
                        if m < u - 0.01:
                            failures.append(f'C2 {where}: {m:.4f} < uniform {u:.4f} - 0.01')
                    elif m < 0.90*u:
                        failures.append(f'C3 {where}: {m:.4f} < 0.90*uniform {u:.4f}')
                drift = max(values) - min(values)
                if drift > 0.05:
                    failures.append(f'C4 {field}/h={horizon}: scale drift {drift:.4f} > 0.05')
        competence[method] = dict(verdict='COMPETENT' if not failures else 'NOT COMPETENT', failures=failures)

    def rate(key, field='d'):
        return mean([row['rates'][key][field] for row in identifiability])
    d_eq = rate('equal-cost|deterministic|homogeneous')
    d_eq_nonexplore = rate('equal-cost|deterministic|homogeneous', 'd_nonexplore')
    levers = dict(
        d_full={f'{m}|{r}': rate(f'full|{m}|{r}') for m in ('wall', 'deterministic')
                for r in ('homogeneous', 'heterogeneous')},
        d_eq=d_eq, d_eq_nonexplore=d_eq_nonexplore,
        delta_cost=rate('full|deterministic|heterogeneous') - d_eq,
        delta_noise=rate('full|wall|homogeneous') - d_eq,
        no_feedback_total_variation=mean([row['no_feedback_total_variation'] for row in identifiability]))
    distinct = levers['delta_cost'] >= 0.10 or d_eq_nonexplore >= 0.10
    noise = levers['delta_noise'] >= 0.10
    strong = competence['adaptive-mc-ucb-region']['verdict'] == 'COMPETENT'
    verdict = 'STOP-RETHINK' if not distinct else ('GO' if strong else 'AMEND-BASELINE')
    table = {f'{m}|{f}|{s}|{h}': v for (m, f, s, h), v in sorted(eta.items(), key=lambda kv: str(kv[0]))}
    return dict(gate_verdict=verdict, controller='DISTINCT' if distinct else 'COLLAPSED',
                noise_driven=noise, competence=competence, identifiability=levers, mean_efficiency=table)


def file_sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    output = Path(args.output)
    require(not output.exists(), 'result already exists; the gate executes once')
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    require(contract['schema'] == 'tc-r1-offline-gate-v1', 'wrong gate contract')
    jobs = [(m, f, s, seed) for m in CONVENTIONAL for f in FIELDS for s in SCALES for seed in SEEDS]
    with ProcessPoolExecutor(args.workers) as pool:
        conventional = list(pool.map(run_conventional, jobs))
        identifiability = list(pool.map(run_identifiability, [(f, s) for f in FIELDS for s in SEEDS]))
    here = Path(__file__).resolve().parent
    result = dict(schema='tc-r1-offline-gate-result-v1', contract_sha256=file_sha256(CONTRACT),
                  source_sha256={name: file_sha256(here/name) for name in
                                 ('offline_gate.py', 'baselines.py', 'tc_controller.py', 'progressive_kernel.py')},
                  numpy=np.__version__, **evaluate(conventional, identifiability),
                  raw=dict(conventional=conventional, identifiability=identifiability),
                  rendering_performed=False, primary_scenes_used=False, controller_quality_computed=False)
    output.write_text(json.dumps(result, indent=1, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: result[k] for k in ('gate_verdict', 'controller', 'noise_driven')}))


if __name__ == '__main__':
    main()
