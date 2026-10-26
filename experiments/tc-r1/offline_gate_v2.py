"""TC-R1 offline gate v2 (contract tc-r1-offline-gate-v2): validates amendment 0004.

Reuses the unchanged v1 simulator, metric and criteria; differs only in fresh
seeds under a v2 namespace and in the policies run. One execution.
"""
import argparse
import hashlib
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

import offline_gate as v1
from amended_policies import AmendedConventionalPolicy, AmendedTcPolicy
from baselines import ConventionalPolicy
from progressive_kernel import require

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT/'research/tc-r1/offline-gate/contract-v2.json'
SEEDS = (3, 4, 5)
AMENDED = ('amended-adaptive-mc-ucb-region', 'amended-variance-guided')
ORIGINAL = ('adaptive-mc-ucb-region', 'variance-guided')
METHODS = ('uniform',) + AMENDED + ORIGINAL


def field_seed(field, seed):
    value = f'tc-r1-offline-gate-v2|{field}|{seed}'.encode('utf-8')
    return int.from_bytes(hashlib.sha256(value).digest()[:8], 'big')


class FieldV2(v1.Field):
    """v1 field definitions with the v2 seed namespace (contract-v2 overrides.seed_derivation)."""
    def __init__(self, field, seed, scale=1.0, rays='homogeneous'):
        require(field in v1.FIELDS and rays in ('homogeneous', 'heterogeneous'), 'unknown field')
        self.field, self.scale, self.seed = field, float(scale), field_seed(field, seed)
        rng = np.random.default_rng(self.seed)
        count = len(v1.REGIONS)
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
        self.variance = (self.scale**2)*base[:, None]*v1.CHANNELS[None, :]**2
        self.rays = (np.full(count, 2, dtype=np.int64) if rays == 'homogeneous'
                     else rng.integers(1, 18, count))


def conventional(method):
    if method.startswith('amended-'):
        return AmendedConventionalPolicy(method[len('amended-'):])
    return ConventionalPolicy(method)


def run_conventional(job):
    method, field_name, scale, seed = job
    field = FieldV2(field_name, seed, scale)
    sim = v1.Simulator(field)
    policy = conventional(method)
    snapshots = {}
    marks = {h*len(v1.REGIONS)//v1.BATCH: h for h in v1.HORIZONS}
    for step in range(1, max(marks)+1):
        sim.sample(policy.choose(sim.states('deterministic')).region)
        if step in marks:
            snapshots[marks[step]] = sim.n.copy()
    weights = v1.weights_of(field)
    efficiency = {}
    for horizon, spp in snapshots.items():
        require(int(spp.sum()) == horizon*len(v1.REGIONS), 'allocation total mismatch')
        efficiency[str(horizon)] = v1.oracle_error(weights, float(spp.sum()))/v1.allocation_error(weights, spp)
    return dict(method=method, field=field_name, scale=scale, seed=seed, efficiency=efficiency)


def run_identifiability(job):
    field_name, seed = job
    decisions = v1.HORIZONS[-1]*len(v1.REGIONS)//v1.BATCH
    variants = [('wall', 'homogeneous'), ('wall', 'heterogeneous'),
                ('deterministic', 'homogeneous'), ('deterministic', 'heterogeneous')]
    sims = {v: v1.Simulator(FieldV2(field_name, seed, 1, v[1]), ('wall', 'deterministic')) for v in variants}
    reference = AmendedConventionalPolicy('variance-guided')
    shadows = {('full',)+v: AmendedTcPolicy('full') for v in variants}
    shadows[('equal-cost', 'deterministic', 'homogeneous')] = AmendedTcPolicy('equal-cost')
    counts = {k: dict(post=0, differ=0, nonexplore=0, nonexplore_differ=0) for k in shadows}
    base = sims[variants[0]]
    for _ in range(decisions):
        choice = reference.choose(base.states('wall')).region
        post = min(base.n) >= v1.MINIMUM
        for key, policy in shadows.items():
            shadow = policy.choose(sims[key[1:]].states(key[1])).region
            reason = policy.diagnostics['reason']
            v1.drop_history(policy)
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
    own = v1.Simulator(FieldV2(field_name, seed, 1, 'heterogeneous'))
    policy = AmendedTcPolicy('no-feedback')
    for _ in range(decisions):
        own.sample(policy.choose(own.states('deterministic')).region)
        v1.drop_history(policy)
    tv = 0.5*float(np.abs(own.n/own.n.sum() - base.n/base.n.sum()).sum())
    rates = {'|'.join(k): dict(d=c['differ']/c['post'], d_nonexplore=c['nonexplore_differ']/c['nonexplore'],
                               post_decisions=c['post'])
             for k, c in counts.items()}
    return dict(field=field_name, seed=seed, rates=rates, no_feedback_total_variation=tv)


def competence(eta, method):
    """v1 criteria C1-C4, unchanged, for one method against uniform."""
    failures = []
    for field in v1.FIELDS:
        for horizon in map(str, v1.HORIZONS):
            values = []
            for scale in v1.SCALES:
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
    return dict(verdict='COMPETENT' if not failures else 'NOT COMPETENT', failures=failures)


def evaluate(rows, identifiability):
    eta = {}
    for row in rows:
        for horizon, value in row['efficiency'].items():
            eta.setdefault((row['method'], row['field'], row['scale'], horizon), []).append(value)
    eta = {k: float(np.mean(v)) for k, v in eta.items()}
    results = {m: competence(eta, m) for m in AMENDED + ORIGINAL}

    def rate(key, field='d'):
        return float(np.mean([row['rates'][key][field] for row in identifiability]))
    d_eq = rate('equal-cost|deterministic|homogeneous')
    d_eq_nonexplore = rate('equal-cost|deterministic|homogeneous', 'd_nonexplore')
    levers = dict(
        d_full={f'{m}|{r}': rate(f'full|{m}|{r}') for m in ('wall', 'deterministic')
                for r in ('homogeneous', 'heterogeneous')},
        d_eq=d_eq, d_eq_nonexplore=d_eq_nonexplore,
        delta_cost=rate('full|deterministic|heterogeneous') - d_eq,
        delta_noise=rate('full|wall|homogeneous') - d_eq,
        no_feedback_total_variation=float(np.mean([r['no_feedback_total_variation'] for r in identifiability])))
    distinct = levers['delta_cost'] >= 0.10 or d_eq_nonexplore >= 0.10
    effective = results['amended-adaptive-mc-ucb-region']['verdict'] == 'COMPETENT'
    verdict = 'STOP-RETHINK' if not distinct else ('GO' if effective else 'AMEND-BASELINE-FAILED')
    table = {f'{m}|{f}|{s}|{h}': v for (m, f, s, h), v in sorted(eta.items(), key=lambda kv: str(kv[0]))}
    return dict(gate_verdict=verdict, amendment_effective=effective,
                controller='DISTINCT' if distinct else 'COLLAPSED', noise_driven=levers['delta_noise'] >= 0.10,
                competence=results, identifiability=levers, mean_efficiency=table)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    output = Path(args.output)
    require(not output.exists(), 'result already exists; the gate executes once')
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    require(contract['schema'] == 'tc-r1-offline-gate-v2' and contract['overrides']['seeds'] == list(SEEDS),
            'wrong gate contract')
    jobs = [(m, f, s, seed) for m in METHODS for f in v1.FIELDS for s in v1.SCALES for seed in SEEDS]
    with ProcessPoolExecutor(args.workers) as pool:
        identifiability = list(pool.map(run_identifiability, [(f, s) for f in v1.FIELDS for s in SEEDS]))
        rows = list(pool.map(run_conventional, jobs))
    here = Path(__file__).resolve().parent
    sources = ('offline_gate_v2.py', 'offline_gate.py', 'amended_policies.py', 'baselines.py',
               'tc_controller.py', 'progressive_kernel.py')
    result = dict(schema='tc-r1-offline-gate-result-v2', contract_sha256=v1.file_sha256(CONTRACT),
                  amendment_sha256=v1.file_sha256(ROOT/'research/tc-r1/comparator-amendment-0004.json'),
                  source_sha256={name: v1.file_sha256(here/name) for name in sources},
                  numpy=np.__version__, **evaluate(rows, identifiability),
                  raw=dict(conventional=rows, identifiability=identifiability),
                  rendering_performed=False, primary_scenes_used=False, controller_quality_computed=False)
    output.write_text(json.dumps(result, indent=1, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: result[k] for k in ('gate_verdict', 'amendment_effective', 'controller', 'noise_driven')}))


if __name__ == '__main__':
    main()
