"""Frozen-plan numeric analysis; callers must verify execution provenance first.

No renderer or controller is invoked. Synthetic fixtures are legal before the
execution freeze; production reports require a separately verified input bundle.
"""
import math
import random
import statistics
from collections import Counter

ORDER = ('uniform', 'adaptive', 'variance', 'native')
BUDGETS = (2**20, 2**22, 2**24, 2**26)
FAMILIES = ('uniformly-noisy', 'highly-specular', 'simple-diffuse', 'motion-heavy', 'adaptive-sampling-friendly')
PREREQUISITES = ('references', 'estimator', 'baselines', 'accounting', 'provenance', 'execution_complete')


class Inconclusive(ValueError):
    """Data cannot support the preregistered inference."""


def observation(value, cap):
    t, event = value
    if not isinstance(event, bool) or not math.isfinite(t) or not 0 <= t <= cap:
        raise ValueError('invalid time observation')
    return float(t), event


def median_observation(repeats, cap):
    if len(repeats) != 3:
        raise ValueError('exactly three timing repeats required')
    values = [observation(x, cap) for x in repeats]
    lower = sorted(t for t, _ in values)[1]
    upper = sorted(t if event else math.inf for t, event in values)[1]
    if lower == upper:
        return lower, True
    if math.isinf(upper):
        return lower, False
    raise Inconclusive('three-repeat median is interval-censored, not an exact/right-censored observation')


def restricted_mean(observations, cap):
    """KM area to cap, with event-before-censor ties and no unsupported tail.

    This numeric estimator does not establish independent censoring. Production
    inference separately rejects data-dependent early censoring without proof.
    """
    if not observations or not math.isfinite(cap) or cap <= 0:
        raise ValueError('positive finite cap and observations required')
    groups = {}
    for value in observations:
        t, event = observation(value, cap)
        groups.setdefault(t, [0, 0])[0 if event else 1] += 1
    at_risk, survival, previous, area = len(observations), 1., 0., 0.
    for t, (events, censors) in sorted(groups.items()):
        area += survival*(t-previous)
        survival *= 1-events/at_risk
        at_risk -= events+censors
        previous = t
    if previous < cap and survival > 0:
        raise Inconclusive('positive-survival tail lacks observed follow-up to common cap')
    return area


def percentile(values, p):
    if not values or not 0 <= p <= 1:
        raise ValueError('nonempty percentile sample and probability required')
    values = sorted(values)
    x = (len(values)-1)*p
    lo, hi = math.floor(x), math.ceil(x)
    return values[lo]+(values[hi]-values[lo])*(x-lo)


def resamples(scene_count=10, seeds=8, replicates=10000):
    rng = random.Random(734922)
    for _ in range(replicates):
        yield [scene*seeds+rng.randrange(seeds) for scene in range(scene_count) for _ in range(seeds)]


def quality_effect(log_ratios):
    return 1-math.exp(statistics.fmean(log_ratios))


def select(scores):
    if not scores or set(scores)-set(ORDER):
        raise ValueError('unknown conventional method')
    if not all(math.isfinite(v) for v in scores.values()):
        raise ValueError('nonfinite comparator aggregate')
    return min(scores, key=lambda p: (scores[p], ORDER.index(p)))


def validate_quality(manifest, records, policies):
    if set(manifest) != set(FAMILIES) or any(len(v) != 2 for v in manifest.values()):
        raise ValueError('ten scenes, two per each registered family required')
    scenes = [s for family in FAMILIES for s in manifest[family]]
    if len(set(scenes)) != 10:
        raise ValueError('duplicate scene identity')
    expected = {(p, s, f, seed, b) for p in policies for s in scenes for f in ('f0', 'f1', 'f2')
                for seed in range(8) for b in BUDGETS}
    table = {}
    for row in records:
        key = tuple(row[k] for k in ('policy', 'scene_id', 'frame_id', 'replicate', 'checkpoint'))
        if key not in expected or key in table:
            raise ValueError('unexpected or duplicate quality unit')
        values = [row[k] for k in ('mse', 'ssim', 'lpips', 'worst_region')]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values):
            raise ValueError('nonfinite metric')
        if values[0] < 0 or not -1 <= values[1] <= 1 or values[2] < 0 or values[3] < 0:
            raise ValueError('invalid metric range')
        table[key] = row
    if set(table) != expected:
        raise ValueError('missing quality units; failed units cannot be dropped')
    return scenes, table


def validate_timing(scenes, records, policies, cap):
    expected = {(p, s, f, seed, repeat) for p in policies for s in scenes for f in ('f0', 'f1', 'f2')
                for seed in range(8) for repeat in range(3)}
    table = {}
    for row in records:
        key = tuple(row[k] for k in ('policy', 'scene_id', 'frame_id', 'replicate', 'repeat'))
        if key not in expected or key in table:
            raise ValueError('unexpected or duplicate timing unit')
        for kind in ('first', 'sustained'):
            if set(row[kind]) != {'mse', 'ssim', 'lpips', 'joint'}:
                raise ValueError('every metric and joint target required')
            for metric in row[kind]:
                observation(row[kind][metric], cap)
                first, sustained = row['first'][metric], row['sustained'][metric]
                if sustained[1] and (not first[1] or sustained[0] < first[0]):
                    raise ValueError('sustained target must follow first attainment')
        table[key] = row
    if set(table) != expected:
        raise ValueError('missing timing repeats; failures cannot be omitted')
    return table


def target_observations(checkpoints, followup, cap):
    """Derive observed first and sustained target times from complete checkpoints."""
    if not math.isfinite(followup) or not 0 <= followup <= cap:
        raise ValueError('invalid follow-up')
    times = [r['time'] for r in checkpoints]
    if any(not math.isfinite(t) or not 0 <= t <= followup for t in times) or times != sorted(set(times)):
        raise ValueError('unique increasing checkpoint times required')
    predicates = {
        'mse': lambda r: r['mse'] <= 0.01,
        'ssim': lambda r: r['ssim'] >= 0.95,
        'lpips': lambda r: r['lpips'] <= 0.10,
        'joint': lambda r: r['mse'] <= 0.01 and r['ssim'] >= 0.95 and r['lpips'] <= 0.10,
    }
    result = {'first': {}, 'sustained': {}}
    for metric, predicate in predicates.items():
        flags = []
        for row in checkpoints:
            if not all(math.isfinite(row[k]) for k in ('mse', 'ssim', 'lpips')):
                raise ValueError('invalid checkpoint metric')
            flags.append(predicate(row))
        first = next((i for i, flag in enumerate(flags) if flag), None)
        sustained = next((i for i in range(len(flags)) if all(flags[i:])), None)
        for kind, i in (('first', first), ('sustained', sustained)):
            result[kind][metric] = (times[i], True) if i is not None else (followup, False)
    return result


def guard_summary(rows, conventions):
    regional, ssim_degradation, lpips_degradation = [], [], []
    for controller, baseline in rows:
        regional.append(controller['worst_region'] <= 1.2*min(baseline[p]['worst_region'] for p in conventions))
        ssim_degradation.append(max(baseline[p]['ssim'] for p in conventions)-controller['ssim'])
        lpips_degradation.append(controller['lpips']-min(baseline[p]['lpips'] for p in conventions))
    return {'regional_fraction': statistics.fmean(regional), 'ssim_degradation': statistics.fmean(ssim_degradation),
            'lpips_degradation': statistics.fmean(lpips_degradation)}


def pass_gate(quality, families, guards, time, prerequisites):
    if set(prerequisites) != set(PREREQUISITES) or any(v is not True for v in prerequisites.values()) or not time['valid']:
        return 'INCONCLUSIVE'
    if (set(families) != set(FAMILIES) or set(guards['families']) != set(FAMILIES)
            or not quality['against_all'] or not {'uniform', 'adaptive', 'variance'} <= set(quality['against_all'])):
        return 'INCONCLUSIVE'
    passed = (quality['reduction'] >= .10 and all(v['interval'][0] > 0 for v in quality['against_all'].values())
              and sum(v > 0 for v in families.values()) >= 4
              and guards['pooled']['regional_fraction'] >= .90
              and all(v['ssim_degradation'] <= .01 and v['lpips_degradation'] <= .01
                      for v in [guards['pooled'], *guards['families'].values()])
              and time['reduction'] >= .05 and time['interval'][0] > 0)
    return 'PASS' if passed else 'FAIL'


def analyze(manifest, quality_records, timing_records, conventional, cap, prerequisites, replicates=10000):
    """Complete paired report. Integration must fix provenance before calling.

    Replicate override is solely a numeric test hook, reported in output. The
    execution runner must require 10000 and the execution-preregistered input tag.
    """
    if not math.isfinite(cap) or cap <= 0 or not {'uniform', 'adaptive', 'variance'} <= set(conventional) or set(conventional)-set(ORDER):
        raise ValueError('positive cap and all registered conventional policies required')
    if not isinstance(replicates, int) or isinstance(replicates, bool) or replicates <= 0:
        raise ValueError('positive bootstrap replicate count required')
    policies = [*conventional, 'controller', 'no-feedback', 'equal-cost']
    scenes, table = validate_quality(manifest, quality_records, policies)
    timing = validate_timing(scenes, timing_records, policies, cap)
    units = [(s, seed) for s in scenes for seed in range(8)]
    logs = {p: [statistics.fmean(math.log(max(table[p, s, f, seed, b]['mse'], 1e-12))
                                for f in ('f0', 'f1', 'f2') for b in BUDGETS) for s, seed in units] for p in policies}
    comparator = select({p: statistics.fmean(logs[p]) for p in conventional})
    boot = list(resamples(replicates=replicates))
    against = {}
    for p in conventional:
        ratios = [a-b for a, b in zip(logs['controller'], logs[p])]
        samples = [quality_effect([ratios[i] for i in indices]) for indices in boot]
        log_samples = [statistics.fmean(ratios[i] for i in indices) for indices in boot]
        against[p] = {'reduction': quality_effect(ratios), 'interval': [percentile(samples, .025), percentile(samples, .975)],
                      'mean_log_ratio_interval': [percentile(log_samples, .025), percentile(log_samples, .975)],
                      'paired_log_ratios': ratios,
                      'families': {family: quality_effect([ratios[i] for i, (s, _) in enumerate(units) if s in manifest[family]])
                                   for family in FAMILIES},
                      'wins_ties_losses': dict(Counter('win' if r < 0 else 'loss' if r > 0 else 'tie' for r in ratios)),
                      'quantiles': [percentile(ratios, q) for q in (.05, .25, .5, .75, .95)]}
    families = {family: quality_effect([logs['controller'][i]-logs[comparator][i]
                                        for i, (s, _) in enumerate(units) if s in manifest[family]]) for family in FAMILIES}
    case_rows = []
    for s, seed in units:
        for f in ('f0', 'f1', 'f2'):
            for b in BUDGETS:
                case_rows.append((s, table['controller', s, f, seed, b], {p: table[p, s, f, seed, b] for p in conventional}))
    guards = {'pooled': guard_summary([(c, bs) for _, c, bs in case_rows], conventional),
              'families': {family: guard_summary([(c, bs) for s, c, bs in case_rows if s in manifest[family]], conventional) for family in FAMILIES},
              'individual': {p: {'pooled': guard_summary([(c, bs) for _, c, bs in case_rows], [p]),
                                  'families': {family: guard_summary([(c, bs) for s, c, bs in case_rows if s in manifest[family]], [p])
                                               for family in FAMILIES}} for p in conventional},
              'label': 'per-case conventional guard envelope; never a primary/time policy'}
    quality = {'comparator': comparator, 'reduction': against[comparator]['reduction'], 'against_all': against,
               'policy_mean_log_mse': {p: statistics.fmean(v) for p, v in logs.items()},
               'per_budget_mean_log_mse': {p: {str(b): statistics.fmean(math.log(max(r['mse'], 1e-12))
                                          for k, r in table.items() if k[0] == p and k[-1] == b) for b in BUDGETS} for p in policies}}
    time = {'valid': False, 'reason': None, 'cap': cap}
    descriptive = {}
    try:
        observations = {}
        for kind in ('first', 'sustained'):
            for metric in ('mse', 'ssim', 'lpips', 'joint'):
                key = f'{kind}:{metric}'
                obs = {p: [median_observation([timing[p, s, f, seed, repeat][kind][metric] for repeat in range(3)], cap)
                           for s, seed in units for f in ('f0', 'f1', 'f2')] for p in policies}
                descriptive[key] = {p: restricted_mean(v, cap) for p, v in obs.items()}
                if key == 'first:joint':
                    observations = obs
        early = any(not event and t < cap for v in observations.values() for t, event in v)
        if early:
            raise Inconclusive('early censoring lacks independent-censoring justification; KM is descriptive only')
        time_comparator = select({p: descriptive['first:joint'][p] for p in conventional})
        time_against = {}
        for p in conventional:
            original_denominator = descriptive['first:joint'][p]
            if original_denominator <= 0:
                raise Inconclusive('zero comparator target time does not support relative time benefit')
            samples = []
            for indices in boot:
                ids = [i*3+f for i in indices for f in range(3)]
                denominator = restricted_mean([observations[p][i] for i in ids], cap)
                if denominator <= 0:
                    raise Inconclusive('zero comparator target time does not support relative time benefit')
                samples.append(1-restricted_mean([observations['controller'][i] for i in ids], cap)/denominator)
            time_against[p] = {'reduction': 1-descriptive['first:joint']['controller']/original_denominator,
                               'interval': [percentile(samples, .025), percentile(samples, .975)]}
        time.update(valid=True, comparator=time_comparator, **time_against[time_comparator], against_all=time_against,
                    observations=observations)
    except (Inconclusive, ZeroDivisionError) as exc:
        time['reason'] = str(exc)
    time['descriptive_rmst'] = descriptive
    result = pass_gate(quality, families, guards, time, prerequisites)
    if replicates != 10000:
        result = 'INCONCLUSIVE'
    return {'schema': 'tc-r1-analysis-v1', 'classification': result, 'quality': quality, 'families': families,
            'guards': guards, 'time': time, 'prerequisites': prerequisites, 'bootstrap_replicates': replicates,
            'retained_quality_rows': quality_records, 'retained_timing_rows': timing_records}
