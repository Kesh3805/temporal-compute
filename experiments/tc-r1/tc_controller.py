"""Frozen minimal allocation-only marginal heuristic and its two ablations.

No renderer, reference, stopping gate or generic runtime lives in this module.
The caller executes/charges matched allocation and production requests.
"""
from copy import deepcopy
from dataclasses import asdict
import math

from progressive_kernel import Region, RegionState, WorkRequest, require


BATCH = 4
MINIMUM = 16
EXPLORATION_PERIOD = 16


def geometry_key(region):
    return region.y0, region.x0, region.y1, region.x1


def nonnegative_finite(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def uncertainty(state):
    require(isinstance(state.standard_error, tuple) and len(state.standard_error) == 3 and
            all(nonnegative_finite(v) for v in state.standard_error), 'invalid allocation uncertainty')
    q = state.region.area ** 2 * math.fsum(v * v for v in state.standard_error)
    require(math.isfinite(q), 'uncertainty overflow')
    return q


def allocation_cost(state):
    value = state.estimated_sample_cost
    require(type(value) in (int, float) and math.isfinite(value) and value > 0,
            'invalid measured allocation cost')
    cost = value * state.region.area * BATCH
    require(math.isfinite(cost) and cost > 0, 'request cost overflow')
    return cost


def recent_coefficient(state, model_coefficient):
    if state.recent_improvement is None:
        return model_coefficient
    value = state.recent_improvement
    require(type(value) in (int, float) and math.isfinite(value), 'invalid recent improvement')
    coefficient = max(state.region.area ** 2 * value, 0.) * state.samples_per_pixel * (
        state.samples_per_pixel - BATCH) / BATCH
    require(math.isfinite(coefficient), 'recent coefficient overflow')
    return coefficient


class TcPolicy:
    """Synchronous policy only; the shared caller owns execution and stopping.

    no-feedback observes later counts solely to validate completion of its own
    actions. Subsequent radiance, uncertainty and cost never enter its estimates.
    """
    def __init__(self, mode='full'):
        require(mode in ('full', 'equal-cost', 'no-feedback'), 'unknown TC ablation')
        self.mode = mode
        self._regions = None
        self._frozen = None
        self._expected_counts = None
        self._post_initialization = 0
        self._diagnostics = []
        self._failed = False

    @property
    def diagnostics(self):
        return deepcopy(self._diagnostics[-1]) if self._diagnostics else None

    @property
    def history(self):
        return tuple(deepcopy(self._diagnostics))

    def choose(self, states):
        require(not self._failed, 'failed policy cannot be reused')
        try:
            return self._choose(states)
        except BaseException:
            self._failed = True
            raise

    def _choose(self, states):
        require(isinstance(states, tuple) and states and
                all(isinstance(s, RegionState) for s in states), 'allocation state interface')
        for state in states:
            region = state.region
            require(isinstance(region, Region) and
                    all(type(v) is int for v in (region.x0, region.x1, region.y0, region.y1)) and
                    0 <= region.x0 < region.x1 and 0 <= region.y0 < region.y1,
                    'invalid observed region bounds')
            require(type(state.version) is int and state.version >= 0,
                    'invalid allocation version')
        require(len({s.version for s in states}) == 1, 'mixed allocation observation versions')
        ordered = tuple(sorted(states, key=lambda s: geometry_key(s.region)))
        regions = tuple(s.region for s in ordered)
        require(len(set(regions)) == len(regions), 'duplicate observed region')
        if self._regions is not None:
            require(regions == self._regions, 'allocation partition changed')
        for state in ordered:
            require(type(state.samples_per_pixel) is int and state.samples_per_pixel >= 0 and
                    state.samples_per_pixel <= 0x7fffffff - BATCH and
                    type(state.sample_count) is int and
                    state.sample_count == state.samples_per_pixel * state.region.area and
                    type(state.charged_rays) is int and state.charged_rays >= state.sample_count,
                    'allocation count/area/charge identity')
        counts = {s.region: s.samples_per_pixel for s in ordered}
        if self._expected_counts is not None:
            require(counts == self._expected_counts, 'no-feedback caller count transition mismatch')

        candidates = []
        post = self._post_initialization
        frozen = self._frozen
        if min(counts.values()) < MINIMUM:
            require(frozen is None, 'no-feedback coverage regressed')
            selected = min(ordered, key=lambda s: (s.samples_per_pixel, geometry_key(s.region)))
            reason = 'minimum-coverage'
        else:
            if self.mode == 'no-feedback' and frozen is None:
                frozen = {}
                for state in ordered:
                    model_coefficient = uncertainty(state) * state.samples_per_pixel
                    frozen[state.region] = (model_coefficient,
                                            recent_coefficient(state, model_coefficient),
                                            allocation_cost(state))
            for state in ordered:
                n = state.samples_per_pixel
                if self.mode == 'no-feedback':
                    model_coefficient, recent, cost = frozen[state.region]
                    model = model_coefficient * BATCH / (n * (n + BATCH))
                    recent_gain = recent * BATCH / (n * (n + BATCH))
                else:
                    model = uncertainty(state) * BATCH / (n + BATCH)
                    # Validate common measured cost even when the ablation ranks
                    # with denominator1; unknown allocation evidence cannot pass.
                    cost = allocation_cost(state)
                    recent = recent_coefficient(state, uncertainty(state) * n)
                    recent_gain = recent * BATCH / (n * (n + BATCH))
                denominator = 1. if self.mode == 'equal-cost' else cost
                gain = .5 * model + .5 * recent_gain
                bonus = .25 * model
                score = (gain + bonus) / denominator
                require(all(nonnegative_finite(v) for v in (model, recent_gain, gain, bonus, score)),
                        'invalid candidate estimate')
                candidates.append(dict(region=geometry_key(state.region), samples_per_pixel=n,
                                       model_gain=model, recent_gain=recent_gain, gain=gain,
                                       uncertainty_bonus=bonus, allocation_request_cost_seconds=cost,
                                       ranking_denominator=denominator, score=score))
            post += 1
            if post % EXPLORATION_PERIOD == 0:
                selected = min(ordered, key=lambda s: (s.samples_per_pixel, geometry_key(s.region)))
                reason = 'exploration'
            else:
                winner = min(candidates, key=lambda c: (-c['score'], c['region']))
                selected = next(s for s in ordered if geometry_key(s.region) == winner['region'])
                reason = 'marginal-score'
        request = WorkRequest(selected.region, BATCH)
        record = dict(mode=self.mode, reason=reason,
                      allocation_state=tuple(asdict(s) for s in ordered),
                      candidates=tuple(candidates), chosen=dict(region=geometry_key(selected.region),
                                                               additional_samples=BATCH))
        # Publish internal predictor/count transitions only after valid choice.
        self._regions = regions
        self._frozen = frozen
        self._post_initialization = post
        if frozen is not None:
            self._expected_counts = dict(counts)
            self._expected_counts[selected.region] += BATCH
        self._diagnostics.append(record)
        return request
