"""Frozen analysis primitives, tested on known fixtures before EO measurement."""
import math
from tc_s1_generate import SplitMix64, task_class


def quantile(values, p):
    if not values:
        return None
    values = sorted(values)
    at = (len(values)-1)*p
    i = math.floor(at)
    return values[i] + (values[min(i+1, len(values)-1)]-values[i])*(at-i)


def distribution(values):
    return dict(count=len(values), mean=sum(values)/len(values) if values else None,
                median=quantile(values, .5), **{f'p{int(p*100)}': quantile(values, p) for p in [.1,.25,.5,.75,.9]})


def ratio(a, b):
    return a/b if b else None


def utility_at(task, completion):
    arrival = task['arrival_time_us']
    if completion < arrival or any(task.get(k) is not None and completion > task[k] for k in ('deadline_us','fresh_until_us')):
        return 0
    base = task['base_utility']
    curve = task['utility']
    age = completion-arrival
    if curve['kind'] == 'constant':
        return base
    if curve['kind'] == 'linear':
        return base*(task['deadline_us']-completion)//(task['deadline_us']-arrival)
    if curve['kind'] == 'step':
        for step in curve['steps']:
            if step['after_us'] <= age:
                base = step['utility']
        return base
    scale = 1_000_000_000_000
    exponent = age//curve['interval_us']
    factor = curve['retention_ppm']*scale//1_000_000
    retained = scale
    while exponent:
        if exponent & 1:
            retained = retained*factor//scale
        factor = factor*factor//scale
        exponent >>= 1
    return base*retained//scale


def oracle(scenario):
    tasks = scenario['tasks']
    if len(tasks) > 9:
        raise ValueError('exact oracle is restricted to preregistered <=9-task problems')
    frontiers = [dict() for _ in range(1 << len(tasks))]
    frontiers[0][0] = (0, ())
    best = (0, 0, ())
    for mask, states in enumerate(frontiers):
        frontier = []
        maximum = -1
        for finish, (value, schedule) in sorted(states.items()):
            if value > maximum:
                frontier.append((finish,value,schedule))
                maximum = value
        for finish, value, schedule in frontier:
            if value > best[0] or (value == best[0] and finish < best[1]):
                best = (value,finish,schedule)
            for j, task in enumerate(tasks):
                if mask & (1 << j):
                    continue
                completion = max(finish,task['arrival_time_us'])+task['execution_cost_us']
                reward = utility_at(task,completion)
                if not reward:
                    continue
                target = frontiers[mask | (1 << j)]
                candidate = (value+reward, schedule+(task['id'],))
                if completion not in target or candidate[0] > target[completion][0]:
                    target[completion] = candidate
    return dict(utility=best[0], completion_us=best[1], schedule=list(best[2]), exact=True)


def run_projection(run, cfg):
    tasks = {t['id']: t for t in run['scenario']['tasks']}
    classes = {n: dict(tasks=0, completed=0, expired_unstarted=0, zero_utility_completions=0,
                       base_utility=0, utility=0, critical_successes=0, max_waiting_us=0) for n in cfg['class_order']}
    starts = {}
    for task in tasks.values():
        c = classes[task_class(task)]
        c['tasks'] += 1
        c['base_utility'] += task['base_utility']
    for event in run['events']:
        kind = event['event']
        if kind == 'task_started':
            starts[event['task_id']] = event['sim_time_us']
        if kind not in ('task_completed','task_expired'):
            continue
        task = tasks[event['task_id']]
        name = task_class(task)
        c = classes[name]
        wait_end = starts[task['id']] if kind == 'task_completed' else event['sim_time_us']
        c['max_waiting_us'] = max(c['max_waiting_us'],wait_end-task['arrival_time_us'])
        if kind == 'task_expired':
            c['expired_unstarted'] += 1
        else:
            actual = event['utility']
            if actual != utility_at(task,event['sim_time_us']):
                raise ValueError('Python utility and unchanged Rust kernel disagree')
            c['completed'] += 1
            c['utility'] += actual
            c['zero_utility_completions'] += int(actual == 0)
            c['critical_successes'] += int(cfg['classes'][name]['critical'] and 2*actual >= task['base_utility'])
    return classes


def aggregate(rows, cfg):
    result = {}
    for policy in cfg['schedulers']:
        selected = [r for r in rows if r['scheduler']==policy]
        metrics = [r['metrics'] for r in selected]
        total = sum(m['total_utility'] for m in metrics)
        base = sum(m['maximum_task_utility_sum'] for m in metrics)
        completed = sum(m['tasks_completed'] for m in metrics)
        classes = {}
        for name in cfg['class_order']:
            values = [r['classes'][name] for r in selected]
            c = {k: (max(v[k] for v in values) if k=='max_waiting_us' else sum(v[k] for v in values)) for k in values[0]}
            c.update(completion_rate=ratio(c['completed'],c['tasks']), utility_retained=ratio(c['utility'],c['base_utility']),
                     utility_lost=c['base_utility']-c['utility'], critical_success_rate=ratio(c['critical_successes'],c['tasks']) if cfg['classes'][name]['critical'] else None)
            classes[name] = c
        result[policy] = dict(total_utility=total, base_utility=base, normalized_utility=ratio(total,base),
                              utility_distribution=distribution([m['total_utility'] for m in metrics]),
                              completed=completed, expired_unstarted=sum(m['tasks_expired'] for m in metrics),
                              compute_used_us=sum(m['compute_time_used_us'] for m in metrics),
                              compute_wasted_us=sum(m['compute_time_wasted_us'] for m in metrics),
                              deadline_hit_rate=ratio(sum(m['deadline_hits'] for m in metrics),sum(m['deadline_tasks_total'] for m in metrics)),
                              average_result_age_us=ratio(sum((m['average_result_age_us'] or 0)*m['tasks_completed'] for m in metrics), completed),
                              average_completion_latency_us=ratio(sum((m['average_completion_latency_us'] or 0)*m['tasks_completed'] for m in metrics), completed),classes=classes)
    return result


def paired(rows, cfg, bootstrap=True):
    policies = cfg['schedulers']
    lookup = {(r['id'],r['scheduler']): r for r in rows}
    primary = [r for r in rows if r['scheduler']==cfg['primary_scheduler']]
    deltas = {b: [r['metrics']['total_utility']-lookup[(r['id'],b)]['metrics']['total_utility'] for r in primary] for b in cfg['baselines']}
    intervals = {b: [] for b in cfg['baselines']}
    if bootstrap:
        cells = {}
        for i, r in enumerate(primary):
            cells.setdefault((r['mission_mix'],r['load_regime']),[]).append(i)
        rng = SplitMix64(cfg['analysis_seed'])
        for _ in range(cfg['analysis']['bootstrap_resamples']):
            indices = [cell[rng.below(len(cell))] for cell in cells.values() for _ in cell]
            for b in cfg['baselines']:
                intervals[b].append(sum(deltas[b][i] for i in indices)/len(indices))
    output = {}
    for policy in policies:
        if policy == cfg['primary_scheduler']:
            continue
        delta = [r['metrics']['total_utility']-lookup[(r['id'],policy)]['metrics']['total_utility'] for r in primary]
        normalized = [d/r['metrics']['maximum_task_utility_sum'] for d,r in zip(delta,primary)]
        denominator = sum(lookup[(r['id'],policy)]['metrics']['total_utility'] for r in primary)
        output[policy] = dict(paired_deltas=delta, raw_delta_distribution=distribution(delta), normalized_delta_distribution=distribution(normalized),
                             relative_aggregate_gain=ratio(sum(delta),denominator), wins=sum(d>0 for d in delta), ties=delta.count(0), losses=sum(d<0 for d in delta),
                             bootstrap_mean_delta_ci=[quantile(intervals[policy],.025),quantile(intervals[policy],.975)] if policy in intervals and bootstrap else None)
    return output


def critical_gate(rows, cfg):
    outcomes = {}
    lookup = {(r['id'],r['scheduler']): r for r in rows}
    primary = [r for r in rows if r['scheduler']==cfg['primary_scheduler']]
    critical = [n for n in cfg['class_order'] if cfg['classes'][n]['critical']]
    for label, names in [('all-critical',critical)]+[(n,[n]) for n in critical]:
        def counts(row):
            return (sum(row['classes'][n]['critical_successes'] for n in names),sum(row['classes'][n]['tasks'] for n in names))
        rates = {p: ratio(sum(counts(lookup[(r['id'],p)])[0] for r in primary),sum(counts(r)[1] for r in primary)) for p in cfg['schedulers']}
        best = max(rates[b] for b in cfg['baselines'] if rates[b] is not None)
        differences = []
        for r in primary:
            n,d = counts(r)
            if d:
                differences.append(n/d-max(counts(lookup[(r['id'],b)])[0]/d for b in cfg['baselines']))
        tail = sum(v >= -cfg['gates']['critical_tail_loss_max']-1e-12 for v in differences)/len(differences)
        outcomes[label] = dict(rates=rates, best_conventional_rate=best, primary_delta=rates[cfg['primary_scheduler']]-best,
                               tail_fraction_within_tolerance=tail, per_scenario_rate_deltas=differences,
                               passed=rates[cfg['primary_scheduler']] >= best-cfg['gates']['critical_rate_loss_max']-1e-12 and tail>=cfg['gates']['critical_tail_fraction_required'])
    return outcomes


def gain(aggregates, cfg):
    best = max(cfg['baselines'],key=lambda p: aggregates[p]['total_utility'])
    return best, ratio(aggregates[cfg['primary_scheduler']]['total_utility']-aggregates[best]['total_utility'],aggregates[best]['total_utility'])


def verdict(rows, aggregates, comparisons, sensitivities, cfg):
    best, overall = gain(aggregates,cfg)
    groups = {}
    for field, names in [('load_regime',cfg['load_regimes']),('mission_mix',cfg['mission_mixes'])]:
        groups[field] = {name: dict(zip(['strongest_baseline','relative_gain'],gain(aggregate([r for r in rows if r[field]==name],cfg),cfg))) for name in names}
    critical = critical_gate(rows,cfg)
    g = cfg['gates']
    checks = dict(aggregate=overall>=g['aggregate_gain_min'] and all(comparisons[b]['bootstrap_mean_delta_ci'][0]>0 for b in cfg['baselines']),
                  median=comparisons[best]['normalized_delta_distribution']['median']>=g['median_normalized_paired_delta_min'],
                  breadth=sum(groups['load_regime'][n]['relative_gain']>=g['load_gain_min'] for n in ['moderate','overloaded','severe'])>=g['pressured_loads_required'] and sum(v['relative_gain']>=g['mix_gain_min'] for v in groups['mission_mix'].values())>=g['mixes_required'],
                  sensitivity=sum(v['relative_gain']>=0 for v in sensitivities.values())>=g['sensitivity_nonnegative_required'] and sum(v['relative_gain']>=g['sensitivity_gain_min'] for v in sensitivities.values())>=g['sensitivity_gain_required'],
                  critical=all(v['passed'] for v in critical.values()))
    return dict(verdict='PASS' if all(checks.values()) else 'FAIL', gates=checks, strongest_baseline=best, relative_gain=overall, groups=groups,critical=critical)
