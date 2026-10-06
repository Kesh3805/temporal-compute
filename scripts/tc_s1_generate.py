"""Policy-blind TC-S1 corpus reproduction. Phase A never evaluates a scheduler."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASK = (1 << 64) - 1
SECOND = 1_000_000


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True) + '\n').encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def config():
    return json.loads((ROOT / 'research/tc-s1/preregistration.json').read_text())


class SplitMix64:
    def __init__(self, seed):
        self.state = seed & MASK

    def next(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK
        return (z ^ (z >> 31)) & MASK

    def below(self, bound):
        # Rejection sampling is used for analysis/shuffling, not latent generation.
        limit = (1 << 64) - ((1 << 64) % bound)
        while True:
            value = self.next()
            if value < limit:
                return value % bound


def derive_seed(master, kind, mix, load, replicate):
    text = f'tc-s1-v1|{master}|{kind}|{mix}|{load}|{replicate}'
    return int.from_bytes(hashlib.sha256(text.encode('ascii')).digest()[:8], 'big')


def draw(raw, limits):
    low, high = limits
    return low + ((raw * (high - low + 1)) >> 64)


def weighted(raw, names, weights):
    total = sum(weights)
    target = (raw * total) >> 64
    for name, weight in zip(names, weights):
        if target < weight:
            return name
        target -= weight
    raise ValueError('invalid categorical weights')


def primary(cfg, mix, load, replicate, number, profile='primary'):
    seed = derive_seed(cfg['master_seed'], 'primary', mix, load, replicate)
    rng = SplitMix64(seed)
    names = cfg['class_order']
    weights = list(cfg['mission_mixes'][mix])
    sensitivity = cfg['sensitivity'].get(profile, {})
    axis, percent = sensitivity.get('axis'), sensitivity.get('percent', 100)
    if axis in ('cloud-weight', 'event-weight'):
        weights = [w * (percent if (axis == 'cloud-weight' and n == 'CLOUD_SCREEN') or
                    (axis == 'event-weight' and cfg['classes'][n]['critical']) else 100)
                   for n, w in zip(names, weights)]
    tasks = []
    arrivals = []
    for i in range(cfg['tasks_per_instance']):
        latent = [rng.next() for _ in range(cfg['generation']['latent_draws_per_task'])]
        name = weighted(latent[0], names, weights)
        cls = cfg['classes'][name]
        base = draw(latent[2], cls['base'])
        utility = {'kind': cls['curve']}
        if cls['curve'] == 'exponential':
            utility.update(interval_us=draw(latent[5], cls['interval_s']) * SECOND,
                           retention_ppm=draw(latent[6], cls['retention_ppm']))
        if cls['curve'] == 'step':
            utility['steps'] = [dict(after_us=draw(latent[7+j], cls[f'step{j+1}_s']) * SECOND,
                                     utility=base * cls['step_values_ppm'][j] // 1_000_000) for j in range(2)]
        tasks.append(dict(id=f't{i:03}-{name}', arrival_time_us=0,
                          execution_cost_us=draw(latent[1], cls['cost_s']) * SECOND,
                          deadline_us=draw(latent[3], cls['deadline_s']) * SECOND,
                          fresh_until_us=draw(latent[4], cls['fresh_s']) * SECOND,
                          input_time_us=0, priority=cls['priority'], base_utility=base, utility=utility))
        arrivals.append(latent[9])
    numerator, denominator = cfg['load_regimes'][load]
    cost_s = sum(t['execution_cost_us'] for t in tasks) // SECOND
    horizon_s = (cost_s * denominator + numerator - 1) // numerator
    # Weight sensitivities regenerate classes with common latent draws; horizon follows new base costs.
    for task, arrival in zip(tasks, arrivals):
        at = ((arrival * horizon_s) >> 64) * SECOND
        if axis == 'intensity':
            at = at * 100 // percent
        if axis == 'cost':
            task['execution_cost_us'] = task['execution_cost_us'] * percent // 100
        if axis == 'age':
            task['deadline_us'] = task['deadline_us'] * percent // 100
            task['fresh_until_us'] = task['fresh_until_us'] * percent // 100
            curve = task['utility']
            if 'interval_us' in curve:
                curve['interval_us'] = curve['interval_us'] * percent // 100
            for step in curve.get('steps', []):
                step['after_us'] = step['after_us'] * percent // 100
        if axis == 'emergency-value' and cfg['classes'][task_class(task)]['critical']:
            task['base_utility'] = task['base_utility'] * percent // 100
            for step in task['utility'].get('steps', []):
                step['utility'] = step['utility'] * percent // 100
        task['arrival_time_us'] = task['input_time_us'] = at
        task['deadline_us'] += at
        task['fresh_until_us'] += at
    scenario = dict(schema_version=1, name=f'eo-{number:04}',
                    description='TC-S1 fictional EO product requests; all numeric parameters are D assumptions.', tasks=tasks)
    effective_horizon_us = horizon_s * SECOND * (100 if axis == 'intensity' else 1) // (percent if axis == 'intensity' else 1)
    entry = dict(id=scenario['name'], seed=seed, family='primary', mission_mix=mix, load_regime=load,
                 replicate=replicate, profile=profile, task_count=len(tasks), acquisition_horizon_us=effective_horizon_us,
                 offered_load=sum(t['execution_cost_us'] for t in tasks) / effective_horizon_us,
                 sha256=digest(scenario))
    return entry, scenario


def task_class(task):
    return task['id'].split('-', 1)[1]


def simple_task(id, cost, value, deadline=None, arrival=0, priority=0):
    return dict(id=id, arrival_time_us=arrival*SECOND, input_time_us=arrival*SECOND,
                execution_cost_us=cost*SECOND, deadline_us=None if deadline is None else deadline*SECOND,
                fresh_until_us=None, priority=priority, base_utility=value, utility={'kind': 'constant'})


def controls(cfg):
    definitions = {
        'constant-value': [simple_task(f't{i:03}-IMAGE_COMPRESSION', 1+i%7, 10+i%11) for i in range(24)],
        'underload-equivalence': [simple_task(f't{i:03}-IMAGE_COMPRESSION', 1+i%7, 10+i%11, arrival=i*20, deadline=i*20+15) for i in range(24)],
        'long-urgent': [simple_task('t000-DISASTER_MAPPING', 8, 100, 8, priority=4), simple_task('t001-IMAGE_COMPRESSION', 2, 30, 12)],
        'density-starvation': [simple_task('t000-DISASTER_MAPPING', 20, 100, 30, priority=4)] + [simple_task(f't{i+1:03}-IMAGE_COMPRESSION', 1, 10, 100) for i in range(20)],
        'absolute-starvation': [simple_task('t000-WILDFIRE_ALERT', 1, 70, 10, priority=5)] + [simple_task(f't{i+1:03}-DISASTER_MAPPING', 10, 100, 100, priority=4) for i in range(8)],
        'deadline-dominant': [simple_task('t000-IMAGE_COMPRESSION', 6, 100, 20), simple_task('t001-WILDFIRE_ALERT', 4, 60, 4, priority=5)],
        'priority-dominant': [simple_task('t000-IMAGE_COMPRESSION', 4, 80, 20), simple_task('t001-WILDFIRE_ALERT', 4, 100, 6, priority=5)],
    }
    for i, name in enumerate(cfg['controls']):
        scenario = dict(schema_version=1, name=name, description='Synthetic E control; not a mission-frequency claim.', tasks=definitions[name])
        yield dict(id=name, seed=derive_seed(cfg['master_seed'], 'control', name, 'none', 0), family='control',
                   mission_mix='control', load_regime='control', replicate=i, profile='control',
                   task_count=len(scenario['tasks']), sha256=digest(scenario)), scenario


def oracle_subset(cfg, entry, scenario):
    seed = derive_seed(cfg['master_seed'], 'oracle', entry['mission_mix'], entry['load_regime'], entry['replicate'])
    rng = SplitMix64(seed)
    indices = list(range(len(scenario['tasks'])))
    for i in range(len(indices)-1, 0, -1):
        j = rng.below(i+1)
        indices[i], indices[j] = indices[j], indices[i]
    selected = sorted(indices[:cfg['oracle']['tasks']])
    tasks = copy.deepcopy([scenario['tasks'][i] for i in selected])
    numerator, denominator = cfg['load_regimes'][entry['load_regime']]
    demand = sum(t['execution_cost_us'] for t in tasks)
    horizon = (demand*denominator + numerator-1)//numerator
    for t in tasks:
        old = t['arrival_time_us']
        at = old * horizon // entry['acquisition_horizon_us']
        for key in ('deadline_us', 'fresh_until_us'):
            t[key] = t[key] - old + at
        t['arrival_time_us'] = t['input_time_us'] = at
    value = dict(schema_version=1, name=entry['id']+'-oracle', description='Preregistered reduced instance; same nominal load, nine selected products.', tasks=tasks)
    meta = dict(entry, id=value['name'], family='oracle', profile='oracle', seed=seed,
                selected_indices=selected, task_count=len(tasks), acquisition_horizon_us=horizon,
                offered_load=demand/horizon, sha256=digest(value))
    return meta, value


def corpus(cfg=None, sensitivities=False):
    cfg = cfg or config()
    number = 0
    for mix in cfg['mission_mixes']:
        for load in cfg['load_regimes']:
            for replicate in range(cfg['instances_per_cell']):
                number += 1
                entry, scenario = primary(cfg, mix, load, replicate, number)
                yield entry, scenario
                if sensitivities:
                    for profile in cfg['sensitivity']:
                        yield primary(cfg, mix, load, replicate, number, profile)
                if replicate in cfg['oracle']['replicates']:
                    yield oracle_subset(cfg, entry, scenario)
    yield from controls(cfg)


def manifest(cfg=None):
    cfg = cfg or config()
    entries = [entry for entry, _ in corpus(cfg, sensitivities=True)]
    return dict(schema_version=1, generator_version=cfg['generator_version'], master_seed=cfg['master_seed'],
                preregistration_sha256=digest(cfg), scenario_count=cfg['scenario_count'], entries=entries)


def verify():
    stored = json.loads((ROOT/'research/tc-s1/corpus-manifest.json').read_text())
    generated = manifest()
    if generated != stored:
        raise ValueError('corpus/manifest mismatch: never silently replace the frozen primary corpus')
    return generated


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=True)+'\n').encode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-manifest', action='store_true')
    parser.add_argument('--export', type=Path)
    args = parser.parse_args()
    if args.write_manifest:
        if (ROOT/'research/tc-s1/freeze.json').exists():
            raise ValueError('freeze exists; manifest replacement is prohibited')
        write_json(ROOT/'research/tc-s1/corpus-manifest.json', manifest())
    else:
        verify()
    if args.export:
        for entry, scenario in corpus(sensitivities=True):
            path = args.export / entry['profile'] / (entry['id']+'.json')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(canonical(scenario))
    print('Static hash verification complete; no scheduler outcomes generated.')


if __name__ == '__main__':
    main()
