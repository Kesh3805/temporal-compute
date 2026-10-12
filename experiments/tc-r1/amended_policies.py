"""Amendment 0004 policies: scale-equivariant MC-UCB and a shared defensive floor.

baselines.py and tc_controller.py stay byte-identical (native-validation binds
their hashes); this module wraps them. Allocation observations only.
"""
from dataclasses import asdict
import math
import statistics

from baselines import (BATCH_SPP, MINIMUM_SPP, ConventionalPolicy, geometry, initial_request,
                       scalar_variance, validate_observations)
from progressive_kernel import RegionState, WorkRequest, require
from tc_controller import TcPolicy

ALPHA_NUMERATOR, ALPHA_DENOMINATOR = 1, 2   # alpha = 0.5, exact integer comparison
BETA = 1.0                                  # registered value, now dimensionless


def floor_request(states):
    """Least-covered region if any region is below alpha times the mean coverage."""
    counts = [s.samples_per_pixel for s in states]
    least = min(states, key=lambda s: (s.samples_per_pixel, geometry(s.region)))
    # n_min < alpha*mean(n)  <=>  n_min*len*den < num*sum(n)
    if least.samples_per_pixel*len(counts)*ALPHA_DENOMINATOR < ALPHA_NUMERATOR*sum(counts):
        return WorkRequest(least.region, BATCH_SPP)
    return None


class AmendedConventionalPolicy:
    """Amended adaptive conventional methods; uniform is unchanged and not wrapped."""
    def __init__(self, method):
        require(method in ('adaptive-mc-ucb-region', 'variance-guided'), 'unknown amended method')
        self.method = method
        self._variance_guided = ConventionalPolicy('variance-guided')
        self._scale = None
        self.last_reason = None

    @property
    def noise_scale(self):
        return self._scale

    def choose(self, observations):
        states = validate_observations(observations)
        request = initial_request(states)
        if request is not None:
            self.last_reason = 'minimum-coverage'
            return request
        request = floor_request(states)
        if request is not None:
            self.last_reason = 'defensive-floor'
            return request
        self.last_reason = 'index'
        if self.method == 'variance-guided':
            return self._variance_guided.choose(states)
        if self._scale is None:
            # Frozen once, at the first post-initialization decision, when every
            # region holds exactly the common minimum coverage.
            require(all(s.samples_per_pixel == MINIMUM_SPP for s in states), 'scale not frozen at initialization')
            self._scale = math.sqrt(statistics.median(scalar_variance(s) for s in states))
            require(math.isfinite(self._scale), 'invalid noise scale')
        if self._scale == 0:
            selected = min(states, key=lambda s: (s.samples_per_pixel, geometry(s.region)))
            return WorkRequest(selected.region, BATCH_SPP)
        best = None
        for state in states:
            n = state.samples_per_pixel
            index = (math.sqrt(scalar_variance(state)) + 2*BETA*self._scale/math.sqrt(n))/n
            require(math.isfinite(index) and index >= 0, 'invalid allocation index')
            key = (-index, geometry(state.region))
            if best is None or key < best[0]:
                best = (key, state.region)
        return WorkRequest(best[1], BATCH_SPP)


class AmendedTcPolicy(TcPolicy):
    """Controller or ablation with the shared defensive floor (amendment 0004, option A).

    Floor decisions bypass ranking, are recorded as 'defensive-floor', do not
    advance the exploration counter and keep no-feedback count transitions valid.
    """
    def choose(self, states):
        require(not self._failed, 'failed policy cannot be reused')
        try:
            request = self._floor(states)
            return request if request is not None else self._choose(states)
        except BaseException:
            self._failed = True
            raise

    def _floor(self, states):
        require(isinstance(states, tuple) and states and all(isinstance(s, RegionState) for s in states),
                'allocation state interface')
        require(len({s.version for s in states}) == 1, 'mixed allocation observation versions')
        ordered = tuple(sorted(states, key=lambda s: geometry(s.region)))
        if min(s.samples_per_pixel for s in ordered) < MINIMUM_SPP:
            return None
        request = floor_request(ordered)
        if request is None:
            return None
        regions = tuple(s.region for s in ordered)
        require(len(set(regions)) == len(regions), 'duplicate observed region')
        require(self._regions is None or regions == self._regions, 'allocation partition changed')
        require(all(type(s.sample_count) is int and s.sample_count == s.samples_per_pixel*s.region.area and
                    type(s.charged_rays) is int and s.charged_rays >= s.sample_count for s in ordered),
                'allocation count/area/charge identity')
        counts = {s.region: s.samples_per_pixel for s in ordered}
        if self._expected_counts is not None:
            require(counts == self._expected_counts, 'no-feedback caller count transition mismatch')
        require(self.mode != 'no-feedback' or self._frozen is not None, 'floor before no-feedback freeze')
        self._regions = regions
        if self._frozen is not None:
            self._expected_counts = dict(counts)
            self._expected_counts[request.region] += BATCH_SPP
        self._diagnostics.append(dict(mode=self.mode, reason='defensive-floor',
                                      allocation_state=tuple(asdict(s) for s in ordered), candidates=(),
                                      chosen=dict(region=geometry(request.region),
                                                  additional_samples=BATCH_SPP)))
        return request
