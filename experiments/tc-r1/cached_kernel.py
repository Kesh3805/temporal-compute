"""Amendment 0005 section 3(b): exact-equivalent observation for the progressive kernel.

ProgressiveKernel.observe() recomputes every region from per-pixel moments,
which costs O(pixels) Python work three times per request. Region statistics
change only when that region's sample count, charge, cost or recent
improvement changes, so CachedProgressiveKernel recomputes a region only when
that key changes, using the identical formulas. Every returned RegionState is
equal to the hash-bound kernel's; test_cached_kernel.py checks this.
"""
from dataclasses import replace
import math

from progressive_kernel import ProgressiveKernel, RegionState, require


class CachedProgressiveKernel(ProgressiveKernel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._first_pixel = {region: next(region.pixels()) for region in self.regions}
        self._cache = {}

    def _region_state(self, region):
        # Identical arithmetic to ProgressiveKernel.observe for one region.
        values = [self._moments[p] for p in region.pixels()]
        n = values[0].count
        require(all(v.count == n for v in values), 'nonuniform committed region')
        mean = tuple(math.fsum(v.mean[c] for v in values)/region.area for c in range(3)) if n else None
        variance = tuple(math.fsum(v.m2[c]/(n-1) for v in values)/region.area for c in range(3)) if n > 1 else None
        stderr = tuple(math.sqrt(math.fsum(v.m2[c]/((n-1)*n) for v in values))/region.area
                       for c in range(3)) if n > 1 else None
        return RegionState(region, self._version, n*region.area, n, mean, variance,
                           stderr, self._improvement[region], self._cost[region], self._charges[region])

    def observe(self):
        states = []
        for region in self.regions:
            key = (self._moments[self._first_pixel[region]].count, self._charges[region],
                   self._cost[region], self._improvement[region])
            cached = self._cache.get(region)
            if cached is None or cached[0] != key:
                state = self._region_state(region)
                self._cache[region] = (key, state)
            else:
                state = cached[1]
                if state.version != self._version:
                    state = replace(state, version=self._version)
                    self._cache[region] = (key, state)
            states.append(state)
        return tuple(states)
