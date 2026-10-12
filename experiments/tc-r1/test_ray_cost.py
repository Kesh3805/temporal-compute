"""Deterministic ray-cost controller checks; v1-namespace fields and hand states only."""
from dataclasses import replace
import unittest

import offline_gate as gate
from amended_policies import AmendedTcPolicy
from progressive_kernel import Region, RegionState
from ray_cost import RayCostTcPolicy, ray_cost


def trajectory(policy, field, measure, decisions=700):
    sim = gate.Simulator(field, ('wall', 'deterministic'))
    chosen = []
    for _ in range(decisions):
        region = policy.choose(sim.states(measure)).region
        gate.drop_history(policy)
        chosen.append(region)
        sim.sample(region)
    return chosen


class RayCostTests(unittest.TestCase):
    def test_ray_cost_definition(self):
        region = Region(0, 2, 0, 2)
        empty = RegionState(region, 0, 0, 0, None, None, None, None, None, 0)
        self.assertIsNone(ray_cost(empty))
        used = replace(empty, sample_count=64, samples_per_pixel=16, charged_rays=320)
        self.assertEqual(ray_cost(used), 5.0)
        with self.assertRaises(ValueError):
            ray_cost(replace(used, charged_rays=10))

    def test_decisions_ignore_wall_clock_and_match_explicit_ray_cost(self):
        field = gate.Field('lognormal', 11, rays='heterogeneous')
        for mode in ('full', 'no-feedback'):
            with_wall = trajectory(RayCostTcPolicy(mode), field, 'wall')
            with_det = trajectory(RayCostTcPolicy(mode), field, 'deterministic')
            explicit = trajectory(AmendedTcPolicy(mode), field, 'deterministic')
            self.assertEqual(with_wall, with_det, mode)
            self.assertEqual(with_det, explicit, mode)

    def test_cost_changes_ranking_when_rays_differ(self):
        # Equal uncertainty at n=16: the cheaper region wins under ray cost, so
        # making the right region cheaper must override the left-first tie order.
        # Equal-cost ranking ignores rays and falls back to that tie order.
        left, right = Region(0, 1, 0, 1), Region(1, 2, 0, 1)

        def states(left_rays, right_rays):
            return tuple(RegionState(r, 1, 16, 16, (0.,)*3, (1.,)*3, (.25, 0., 0.), None, 1.0, 16*rays)
                         for r, rays in ((left, left_rays), (right, right_rays)))
        self.assertEqual(RayCostTcPolicy('full').choose(states(1, 4)).region, left)
        self.assertEqual(RayCostTcPolicy('full').choose(states(4, 1)).region, right)
        self.assertEqual(RayCostTcPolicy('equal-cost').choose(states(4, 1)).region, left)


if __name__ == '__main__':
    unittest.main()
