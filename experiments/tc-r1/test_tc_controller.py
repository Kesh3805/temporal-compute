"""Independent hand-calculated allocation fixtures; no renderer comparisons."""
from dataclasses import replace
import math
import unittest

from progressive_kernel import Region, RegionState
from tc_controller import TcPolicy


def state(region, n=16, se=(1., 0., 0.), recent=None, cost=1.):
    return RegionState(region, 1, n * region.area, n, (0., 0., 0.), (1., 0., 0.),
                       se, recent, cost, n * region.area)


def completed(states, request, **changes):
    return tuple(replace(s, sample_count=s.sample_count + s.region.area * request.additional_samples,
                         samples_per_pixel=s.samples_per_pixel + request.additional_samples,
                         charged_rays=s.charged_rays + s.region.area * request.additional_samples,
                         version=s.version + 1, **changes)
                 if s.region == request.region else replace(s, version=s.version + 1, **changes) for s in states)


class TcControllerTests(unittest.TestCase):
    def test_minimum_coverage_batch_and_geometric_ties(self):
        left, right = Region(0, 1, 0, 1), Region(1, 2, 0, 1)
        states = (state(right, 0, None, cost=None), state(left, 0, None, cost=None))
        policy = TcPolicy()
        requests = []
        for _ in range(8):
            request = policy.choose(states)
            requests.append(request.region)
            self.assertEqual(request.additional_samples, 4)
            states = completed(states, request)
        self.assertEqual(requests, [left, right] * 4)
        self.assertTrue(all(s.samples_per_pixel == 16 for s in states))
        self.assertTrue(all(r['reason'] == 'minimum-coverage' for r in policy.history))

    def test_hand_calculated_gain_cost_area_and_signed_recent(self):
        # A=2, Q=4*(1²+2²)=20; model=20*4/20=4.
        # Recent negative clamps0. gain2+bonus1=3, requestcost=.5*2*4=4.
        region = Region(0, 2, 0, 1)
        policy = TcPolicy()
        policy.choose((state(region, se=(1., 2., 0.), recent=-7., cost=.5),))
        candidate = policy.history[-1]['candidates'][0]
        self.assertEqual(candidate['model_gain'], 4.)
        self.assertEqual(candidate['recent_gain'], 0.)
        self.assertEqual(candidate['gain'], 2.)
        self.assertEqual(candidate['uncertainty_bonus'], 1.)
        self.assertEqual(candidate['allocation_request_cost_seconds'], 4.)
        self.assertEqual(candidate['score'], .75)
        policy = TcPolicy()
        policy.choose((state(region, se=(1., 2., 0.), recent=None, cost=.5),))
        candidate = policy.history[-1]['candidates'][0]
        self.assertEqual(candidate['recent_gain'], 4.)
        self.assertEqual(candidate['score'], 1.25)

    def test_equal_total_request_cost_equivalence_with_unequal_areas(self):
        regions = (Region(0, 1, 0, 1), Region(1, 3, 0, 1))
        # Seconds/sample differ to make total requestcost equal across areas.
        states = (state(regions[0], se=(2., 0., 0.), cost=2.),
                  state(regions[1], se=(1.5, 0., 0.), cost=1.))
        full, equal = TcPolicy(), TcPolicy('equal-cost')
        self.assertEqual(full.choose(states), equal.choose(states))
        self.assertEqual(full.choose(tuple(reversed(states))), equal.choose(tuple(reversed(states))))
        costs = [c['allocation_request_cost_seconds'] for c in full.history[-1]['candidates']]
        self.assertEqual(costs, [8., 8.])

    def test_cost_information_can_change_ranking(self):
        left, right = Region(0, 1, 0, 1), Region(1, 2, 0, 1)
        states = (state(left, se=(2., 0., 0.), cost=100.), state(right, cost=1.))
        self.assertEqual(TcPolicy().choose(states).region, right)
        self.assertEqual(TcPolicy('equal-cost').choose(states).region, left)

    def test_positive_variance_heuristic_equivalence_is_not_hidden(self):
        # Equal areas, n and costs plus missing recent => all TC numerator
        # factors constant, ranking follows variance as the conventional index.
        left, right = Region(0, 1, 0, 1), Region(1, 2, 0, 1)
        states = (state(left, se=(1., 0., 0.)), state(right, se=(2., 0., 0.)))
        conventional_winner = max(states, key=lambda s: sum(v * v for v in s.standard_error) /
                                   (s.samples_per_pixel + 4))
        self.assertEqual(TcPolicy().choose(states).region, conventional_winner.region)

    def test_no_feedback_ignores_later_radiance_uncertainty_and_cost(self):
        left, right = Region(0, 1, 0, 1), Region(1, 2, 0, 1)
        original = (state(left, se=(2., 0., 0.), recent=.25), state(right))
        a, b = TcPolicy('no-feedback'), TcPolicy('no-feedback')
        states_a = states_b = original
        for _ in range(20):
            request_a, request_b = a.choose(states_a), b.choose(states_b)
            self.assertEqual(request_a, request_b)
            states_a = completed(states_a, request_a)
            states_b = completed(states_b, request_b, mean=(1e5, -1e5, 8.),
                                 variance=(1e10, 1e10, 1e10), standard_error=(99., 99., 99.),
                                 recent_improvement=-1000., estimated_sample_cost=1e6)
        for da, db in zip(a.history, b.history):
            self.assertEqual(da['candidates'], db['candidates'])
        a.choose(states_a)
        with self.assertRaises(ValueError):
            a.choose(states_a)  # Its last request has not been committed again.

    def test_no_feedback_initial_coefficients_follow_declared_n_scaling(self):
        region = Region(0, 2, 0, 1)
        policy = TcPolicy('no-feedback')
        states = (state(region, se=(1., 2., 0.), recent=.5, cost=.5),)
        request = policy.choose(states)
        policy.choose(completed(states, request))
        candidate = policy.history[-1]['candidates'][0]
        # modelcoefficient20*16=320 =>320*4/(20*24)=8/3.
        # recentcoefficient4*.5*16*12/4=96 =>96*4/(20*24)=.8.
        self.assertAlmostEqual(candidate['model_gain'], 8 / 3)
        self.assertAlmostEqual(candidate['recent_gain'], .8)
        self.assertEqual(candidate['allocation_request_cost_seconds'], 4.)

    def test_periodic_exploration_and_full_trace(self):
        left, right = Region(0, 1, 0, 1), Region(1, 2, 0, 1)
        policy = TcPolicy()
        states = (state(left, se=(10., 0., 0.)), state(right, se=(0., 0., 0.)))
        for _ in range(16):
            request = policy.choose(states)
            states = completed(states, request)
        last = policy.history[-1]
        self.assertEqual(last['reason'], 'exploration')
        self.assertEqual(request.region, right)
        self.assertEqual(len(last['allocation_state']), 2)
        self.assertEqual(len(last['candidates']), 2)
        snapshot = policy.history
        snapshot[-1]['chosen']['additional_samples'] = 999
        self.assertEqual(policy.history[-1]['chosen']['additional_samples'], 4)

    def test_invalid_uncertainty_cost_counts_and_partition_fail_closed(self):
        region = Region(0, 1, 0, 1)
        base = state(region)
        for invalid in (replace(base, standard_error=None), replace(base, standard_error=(-1., 0., 0.)),
                        replace(base, standard_error=(math.inf, 0., 0.)),
                        replace(base, estimated_sample_cost=0.), replace(base, estimated_sample_cost=math.nan),
                        replace(base, recent_improvement=math.nan), replace(base, sample_count=1),
                        replace(base, samples_per_pixel=True), replace(base, charged_rays=-1),
                        replace(base, version=True), replace(base, region=Region(-1, 0, 0, 1)),
                        replace(base, region=Region(0., 1., 0, 1))):
            policy = TcPolicy()
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                policy.choose((invalid,))
            self.assertEqual(policy.history, ())
            with self.assertRaises(ValueError):
                policy.choose((base,))
        for states in ((), (base, base), [base]):
            with self.assertRaises(ValueError):
                TcPolicy().choose(states)
        policy = TcPolicy()
        policy.choose((base,))
        with self.assertRaises(ValueError):
            policy.choose((state(Region(1, 2, 0, 1)),))

    def test_mixed_versions_fail_and_latest_diagnostics_avoid_history_embedding(self):
        left, right = Region(0, 1, 0, 1), Region(1, 2, 0, 1)
        with self.assertRaises(ValueError):
            TcPolicy().choose((state(left), replace(state(right), version=2)))
        policy = TcPolicy()
        self.assertIsNone(policy.diagnostics)
        states = (state(left), state(right))
        for _ in range(3):
            request = policy.choose(states)
            states = completed(states, request)
        self.assertEqual(len(policy.history), 3)
        self.assertEqual(policy.diagnostics, policy.history[-1])
        self.assertNotIn('history', policy.diagnostics)
        latest = policy.diagnostics
        latest['chosen']['additional_samples'] = 999
        self.assertEqual(policy.diagnostics['chosen']['additional_samples'], 4)


if __name__ == '__main__':
    unittest.main()
