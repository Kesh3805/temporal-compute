"""Pre-outcome conventional candidates; allocation observations only."""
from dataclasses import dataclass
import math

from progressive_kernel import Region, RegionState, WorkRequest, require

MINIMUM_SPP = 16
BATCH_SPP = 4
ADAPTIVE_BETA = 1.0


def geometry(region):
    return region.y0, region.x0, region.y1, region.x1


def validate_observations(observations):
    states = tuple(observations)
    require(bool(states), 'empty allocation observation')
    require(all(isinstance(s, RegionState) for s in states), 'invalid allocation state')
    require(all(isinstance(s.region, Region) for s in states), 'invalid region type')
    require(len({s.region for s in states}) == len(states), 'duplicate region')
    require(len({s.version for s in states}) == 1, 'mixed snapshot versions')
    for state in states:
        region = state.region
        require(all(type(v) is int for v in geometry(region)) and
                0 <= region.x0 < region.x1 and 0 <= region.y0 < region.y1,
                'invalid region geometry')
        require(all(type(v) is int and v >= 0 for v in
                    (state.version, state.samples_per_pixel, state.sample_count, state.charged_rays)),
                'invalid state count')
        n = state.samples_per_pixel
        require(n <= 0x7fffffff, 'native sample index exhausted')
        require(state.sample_count == n * region.area, 'inconsistent sample counts')
        for name in ('mean', 'variance', 'standard_error'):
            value = getattr(state, name)
            defined = n > (0 if name == 'mean' else 1)
            require((value is not None) == defined, 'invalid undefined statistic')
            if defined:
                require(isinstance(value, tuple) and len(value) == 3 and
                        all(type(v) in (int, float) and math.isfinite(v) for v in value),
                        'invalid RGB statistic')
                if name != 'mean':
                    require(all(v >= 0 for v in value), 'negative uncertainty')
        for name in ('recent_improvement', 'estimated_sample_cost'):
            value = getattr(state, name)
            require(value is None or (type(value) in (int, float) and math.isfinite(value)),
                    'invalid scalar statistic')
        require(state.estimated_sample_cost is None or state.estimated_sample_cost > 0,
                'invalid measured sample cost')
    return tuple(sorted(states, key=lambda s: geometry(s.region)))


def initial_request(states):
    least = min(states, key=lambda s: (s.samples_per_pixel, geometry(s.region)))
    return WorkRequest(least.region, BATCH_SPP) if least.samples_per_pixel < MINIMUM_SPP else None


def scalar_variance(state):
    # Divide before summing so finite channel values cannot overflow their mean.
    return math.fsum(v / 3 for v in state.variance)


@dataclass(frozen=True)
class Candidate:
    region: Region
    index: float


class ConventionalPolicy:
    """No kernel, stream, production image or reference belongs to this object."""
    def __init__(self, method):
        require(method in ('uniform', 'adaptive-mc-ucb-region', 'variance-guided'),
                'unknown conventional method')
        self.method = method
        self._diagnostics = ()

    @property
    def diagnostics(self):
        return self._diagnostics

    def choose(self, observations):
        states = validate_observations(observations)
        self._diagnostics = ()
        request = initial_request(states)
        if request is not None:
            return request
        if self.method == 'uniform':
            selected = min(states, key=lambda s: (s.samples_per_pixel, geometry(s.region)))
            return WorkRequest(selected.region, BATCH_SPP)
        candidates = []
        for state in states:
            n = state.samples_per_pixel
            variance = scalar_variance(state)
            if self.method == 'adaptive-mc-ucb-region':
                index = (math.sqrt(variance) + 2 * ADAPTIVE_BETA / math.sqrt(n)) / n
            else:
                index = variance / n / (n + BATCH_SPP)
            require(math.isfinite(index) and index >= 0, 'invalid allocation index')
            candidates.append(Candidate(state.region, index))
        self._diagnostics = tuple(candidates)
        if self.method == 'variance-guided' and all(c.index == 0 for c in candidates):
            selected = min(states, key=lambda s: (s.samples_per_pixel, geometry(s.region))).region
        else:
            selected = min(candidates, key=lambda c: (-c.index, geometry(c.region))).region
        return WorkRequest(selected, BATCH_SPP)
