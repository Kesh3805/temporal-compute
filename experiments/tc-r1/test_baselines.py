"""Independent synthetic numeric checks; no renderer or policy comparisons."""
from dataclasses import replace
from fractions import Fraction
import math
import unittest

from baselines import ADAPTIVE_BETA, ConventionalPolicy, validate_observations
from progressive_kernel import Region, RegionState

METHODS = ('uniform', 'adaptive-mc-ucb-region', 'variance-guided')
LEFT = Region(0, 1, 0, 1)
RIGHT = Region(1, 3, 0, 1)


def state(region=LEFT, n=16, variance=(4., 4., 4.)):
    return RegionState(region, 7, n * region.area, n,
                       (1., 1., 1.) if n else None,
                       variance if n > 1 else None,
                       tuple(math.sqrt(v / n / region.area) for v in variance) if n > 1 else None,
                       None, .002 if n else None, n * region.area * 5)


class BaselineTests(unittest.TestCase):
    def test_contract_constants_and_independent_equation_answers(self):
        self.assertEqual(ADAPTIVE_BETA, 1.)
        # For V=4,n=16, sigma=2,bonus=1/2 gives index 5/32.
        adaptive = ConventionalPolicy('adaptive-mc-ucb-region')
        adaptive.choose((state(),))
        self.assertEqual(adaptive.diagnostics[0].index, float(Fraction(5, 32)))
        variance = ConventionalPolicy('variance-guided')
        variance.choose((state(),))
        self.assertEqual(variance.diagnostics[0].index, float(Fraction(1, 80)))

    def test_rgb_scalarization_and_unequal_area_do_not_pool_pixel_means(self):
        # Equal within-pixel RGB variance yields equal per-camera indices despite
        # unequal areas: area cancels in variance reduction/request camera cost.
        for method in METHODS[1:]:
            policy = ConventionalPolicy(method)
            request = policy.choose((state(RIGHT, variance=(0., 0., 12.)), state()))
            self.assertEqual(request.region, LEFT)
            self.assertEqual(policy.diagnostics[0].index, policy.diagnostics[1].index)

    def test_every_method_has_identical_minimum_coverage_and_geometry_ties(self):
        for method in METHODS:
            policy = ConventionalPolicy(method)
            for n in (0, 1, 4, 12):
                chosen = policy.choose((state(RIGHT, n=n), state(LEFT, n=n)))
                self.assertEqual(chosen.region, LEFT)
                self.assertEqual(chosen.additional_samples, 4)
            chosen = policy.choose((state(LEFT, n=16), state(RIGHT, n=12)))
            self.assertEqual(chosen.region, RIGHT)

    def test_repeated_update_known_rank_change(self):
        for method in METHODS[1:]:
            policy = ConventionalPolicy(method)
            self.assertEqual(policy.choose((state(LEFT, variance=(1.,) * 3),
                                            state(RIGHT, variance=(16.,) * 3))).region, RIGHT)
            # More samples reduce priority even when variance stays high.
            self.assertEqual(policy.choose((state(LEFT, variance=(1.,) * 3),
                                            state(RIGHT, n=128, variance=(16.,) * 3))).region, LEFT)

    def test_positive_exploration_constant_and_rare_observations(self):
        policy = ConventionalPolicy('adaptive-mc-ucb-region')
        chosen = policy.choose((state(LEFT, n=32, variance=(0.,) * 3),
                                state(RIGHT, variance=(0.,) * 3)))
        self.assertEqual(chosen.region, RIGHT)
        self.assertTrue(all(c.index > 0 for c in policy.diagnostics))
        # Rare large pilot observations raise variance; no convergence claim or
        # clipping removes them from the independent arithmetic fixture.
        chosen = policy.choose((state(LEFT, variance=(0.,) * 3),
                                state(RIGHT, variance=(10000.,) * 3)))
        self.assertEqual(chosen.region, RIGHT)
        variance = ConventionalPolicy('variance-guided')
        self.assertEqual(variance.choose((state(LEFT, n=32, variance=(0.,) * 3),
                                          state(RIGHT, variance=(0.,) * 3))).region, RIGHT)

    def test_nonfinite_undefined_and_malformed_states_fail_closed(self):
        bad = [replace(state(), variance=None), replace(state(), mean=None),
               replace(state(), variance=(-1., 1., 1.)),
               replace(state(), variance=(float('nan'), 1., 1.)),
               replace(state(), standard_error=(float('inf'), 1., 1.)),
               replace(state(), estimated_sample_cost=0.),
               replace(state(), recent_improvement=float('nan')),
               replace(state(), samples_per_pixel=True),
               replace(state(), sample_count=999), replace(state(), region='invalid')]
        for method in METHODS:
            for observation in bad:
                with self.subTest(method=method, observation=observation), self.assertRaises(ValueError):
                    ConventionalPolicy(method).choose((observation,))
        for observations in ((), (state(), state()), (state(), replace(state(RIGHT), version=8))):
            with self.assertRaises(ValueError):
                validate_observations(observations)

    def test_request_does_not_depend_on_reference_like_means_or_cost(self):
        for method in METHODS:
            policy = ConventionalPolicy(method)
            states = (state(), state(RIGHT, variance=(9.,) * 3))
            first = policy.choose(states)
            altered = tuple(replace(s, mean=(1e100, -1e100, 0.), estimated_sample_cost=1e100,
                                    recent_improvement=-1e100) for s in states)
            self.assertEqual(policy.choose(altered), first)


if __name__ == '__main__':
    unittest.main()
