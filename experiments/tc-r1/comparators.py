"""Corpus-level comparator selection; no renderer or controller execution."""
import math

ORDER = ('uniform', 'adaptive', 'variance', 'native')


def select_quality(errors):
    """Inputs are complete, equally weighted unit summaries, not missing-case pools."""
    if not errors or set(errors)-set(ORDER):
        raise ValueError('unknown or empty conventional methods')
    lengths = {len(v) for v in errors.values()}
    if len(lengths)!=1 or 0 in lengths:
        raise ValueError('methods require identical complete unit counts')
    scores = {}
    for method, values in errors.items():
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise ValueError('invalid error')
        scores[method] = math.fsum(math.log(max(v, 1e-12)) for v in values)/len(values)
    return min(scores, key=lambda m:(scores[m],ORDER.index(m))), scores


def restricted_mean(observations, cap):
    """Complete common-cap observations: (first observed attainment, reached).

    Unreached units run to cap. For this complete administrative-censoring
    design, area under the empirical survival curve equals mean(min(T,cap)).
    Earlier censoring is rejected; execution must not invent unobserved tails.
    """
    if not observations or not math.isfinite(cap) or cap<=0:
        raise ValueError('positive cap and complete observations required')
    values = []
    for time, reached in observations:
        if not math.isfinite(time) or not 0<=time<=cap or not isinstance(reached,bool):
            raise ValueError('invalid target-time observation')
        if not reached and time!=cap:
            raise ValueError('earlier censoring requires a separately validated estimator')
        values.append(time)
    return math.fsum(values)/len(values)


def select_time(observations, cap):
    if not observations or set(observations)-set(ORDER):
        raise ValueError('unknown or empty conventional methods')
    if len({len(v) for v in observations.values()})!=1:
        raise ValueError('methods require complete matched observations')
    scores = {m:restricted_mean(v,cap) for m,v in observations.items()}
    return min(scores,key=lambda m:(scores[m],ORDER.index(m))),scores
