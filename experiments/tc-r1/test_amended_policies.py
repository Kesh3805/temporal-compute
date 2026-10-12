"""Amendment 0004 policy checks on hand states and v1-namespace fields; no v2 seeds."""
import math
import unittest

import offline_gate as gate
from amended_policies import AmendedConventionalPolicy, AmendedTcPolicy, floor_request
from progressive_kernel import Region, RegionState


def state(region, n, variance=1.0, version=1, cost=1.0):
    se = (math.sqrt(variance/n),)*3 if n > 1 else None
    return RegionState(region, version, n*region.area, n, (0.5,)*3 if n else None,
                       (variance,)*3 if n > 1 else None, se, None, cost, 2*n*region.area)


REGIONS = tuple(Region(x, x+1, 0, 1) for x in range(4))


def run(policy, field, decisions):
    sim = gate.Simulator(field)
    reasons, regions = [], []
    for _ in range(decisions):
        request = policy.choose(sim.states('deterministic'))
        reason = getattr(policy, 'last_reason', None)
        if isinstance(policy, AmendedTcPolicy):
            reason = policy.diagnostics['reason']
            gate.drop_history(policy)
        reasons.append(reason)
        regions.append(request.region)
        sim.sample(request.region)
    return sim, reasons, regions


class AmendedPolicyTests(unittest.TestCase):
    def test_floor_rule_is_exact_alpha_half(self):
        self.assertIsNone(floor_request(tuple(state(r, 16) for r in REGIONS)))
        # mean 16, least 8 == 0.5*mean: not below the floor.
        at = (state(REGIONS[0], 8),) + tuple(state(r, n) for r, n in zip(REGIONS[1:], (16, 20, 20)))
        self.assertIsNone(floor_request(at))
        below = (state(REGIONS[0], 20), state(REGIONS[1], 4), state(REGIONS[2], 20), state(REGIONS[3], 20))
        self.assertEqual(floor_request(below).region, REGIONS[1])

    def test_mc_ucb_is_scale_equivariant(self):
        a = run(AmendedConventionalPolicy('adaptive-mc-ucb-region'), gate.Field('gaussian', 9, 1), 900)[2]
        b = run(AmendedConventionalPolicy('adaptive-mc-ucb-region'), gate.Field('gaussian', 9, 1000), 900)[2]
        self.assertEqual(a, b)

    def test_mc_ucb_scale_frozen_at_initialization_and_zero_fallback(self):
        policy = AmendedConventionalPolicy('adaptive-mc-ucb-region')
        variances = (1.0, 4.0, 9.0, 100.0)
        states = tuple(state(r, 16, v) for r, v in zip(REGIONS, variances))
        policy.choose(states)
        self.assertEqual(policy.noise_scale, math.sqrt((4.0+9.0)/2))
        zero = AmendedConventionalPolicy('adaptive-mc-ucb-region')
        self.assertEqual(zero.choose(tuple(state(r, 16, 0.0) for r in REGIONS)).region, REGIONS[0])
        self.assertEqual(zero.noise_scale, 0.0)

    def test_amended_variance_guided_takes_floor_then_index(self):
        sim, reasons, _ = run(AmendedConventionalPolicy('variance-guided'), gate.Field('gaussian', 4), 1024)
        self.assertIn('defensive-floor', reasons)
        self.assertGreaterEqual(2*int(sim.n.min())*len(sim.n), int(sim.n.sum()) - 2*4*len(sim.n))

    def test_controller_floor_keeps_ablation_transitions_and_exploration_counter(self):
        for mode in ('full', 'equal-cost', 'no-feedback'):
            policy = AmendedTcPolicy(mode)
            _, reasons, _ = run(policy, gate.Field('gaussian', 4), 1024)
            self.assertIn('defensive-floor', reasons, mode)
            self.assertEqual(policy._post_initialization,
                             sum(r in ('marginal-score', 'exploration') for r in reasons), mode)

    def test_floor_never_preempts_initialization(self):
        policy = AmendedTcPolicy('full')
        states = (state(REGIONS[0], 0, cost=None),) + tuple(state(r, 16) for r in REGIONS[1:])
        policy.choose(states)
        self.assertEqual(policy.diagnostics['reason'], 'minimum-coverage')


if __name__ == '__main__':
    unittest.main()
