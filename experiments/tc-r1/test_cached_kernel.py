"""CachedProgressiveKernel must return states identical to the hash-bound kernel."""
import hashlib
import itertools
import random
import struct
import time
import unittest

from cached_kernel import CachedProgressiveKernel
from progressive_kernel import NativeSample, ProgressiveKernel, Region, WorkRequest


def unit(*key):
    digest = hashlib.sha256(repr(key).encode()).digest()
    return struct.unpack('>Q', digest[:8])[0]/2**64


class NumericBackend:
    """Deterministic per-(pixel, index) radiance and ray charges; optional injected failure."""
    def __init__(self, fail_on=None):
        self.calls = 0
        self.fail_on = fail_on

    def render(self, region, begin, end):
        self.calls += 1
        if self.fail_on == self.calls:
            raise RuntimeError('injected native failure')
        samples = []
        for x, y in region.pixels():
            heavy = (x//4 + y//4) % 3 == 0
            for i in range(begin, end):
                u = unit(x, y, i)
                value = (40.0 if heavy and u > 0.97 else 0.5) * (0.5 + u)
                rays = 1 + int(unit('r', x, y, i)*8)
                samples.append(NativeSample(x, y, i, (value, 0.7*value, 0.4*value), 1, 1+max(rays-1, 0), 0,
                                            1, rays-1, 0))
        return samples


def pair(width, height, regions=None, fail_on=None):
    clocks = [itertools.count(1, 7919), itertools.count(1, 7919)]
    base = ProgressiveKernel(width, height, NumericBackend(fail_on), regions, clock=lambda: next(clocks[0]))
    cached = CachedProgressiveKernel(width, height, NumericBackend(fail_on), regions, clock=lambda: next(clocks[1]))
    return base, cached


class CachedKernelTests(unittest.TestCase):
    def test_states_identical_over_random_requests(self):
        base, cached = pair(32, 32)
        rng = random.Random(5)
        self.assertEqual(base.observe(), cached.observe())
        for _ in range(120):
            region = rng.choice(base.regions)
            spp = rng.choice((1, 4, 16))
            a = base.sample_region(WorkRequest(region, spp))
            b = cached.sample_region(WorkRequest(region, spp))
            self.assertEqual(a, b)
            self.assertEqual(base.observe(), cached.observe())
        self.assertEqual(base.image(), cached.image())
        self.assertEqual(base.trace, cached.trace)

    def test_failure_rollback_states_identical(self):
        base, cached = pair(32, 32, fail_on=3)
        regions = base.regions
        for region in regions[:2]:
            base.sample_region(WorkRequest(region, 4))
            cached.sample_region(WorkRequest(region, 4))
        for kernel in (base, cached):
            with self.assertRaises(RuntimeError):
                kernel.sample_region(WorkRequest(regions[0], 4))
        self.assertEqual(base.observe(), cached.observe())
        self.assertEqual((base.work_known, base.trace), (cached.work_known, cached.trace))

    def test_custom_partition_identical(self):
        regions = (Region(0, 5, 0, 8), Region(5, 8, 0, 8))
        base, cached = pair(8, 8, regions)
        for region in (regions[1], regions[0], regions[1], regions[1]):
            base.sample_region(WorkRequest(region, 4))
            cached.sample_region(WorkRequest(region, 4))
            self.assertEqual(base.observe(), cached.observe())

    def test_observe_cost_no_longer_scales_with_every_pixel(self):
        base, cached = pair(256, 256)
        for kernel in (base, cached):
            kernel.sample_region(WorkRequest(kernel.regions[0], 1))
        timings = []
        for kernel in (base, cached):
            kernel.observe()
            start = time.perf_counter()
            for _ in range(3):
                kernel.observe()
            timings.append(time.perf_counter() - start)
        self.assertLess(timings[1], timings[0] / 5)


if __name__ == '__main__':
    unittest.main()
