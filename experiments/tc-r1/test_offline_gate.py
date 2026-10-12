"""Offline gate harness checks on tiny inputs; never computes the gate verdict."""
import itertools
import math
import unittest

import numpy as np

import offline_gate as gate
from progressive_kernel import NativeSample, ProgressiveKernel, WorkRequest


class FieldBackend:
    def __init__(self, field):
        self.field = field

    def render(self, region, begin, end):
        r = gate.REGIONS.index(region)
        x = self.field.draw(r, begin//gate.BATCH)
        rays = int(self.field.rays[r])
        return [NativeSample(px, py, begin+k, tuple(float(v) for v in x[p, k]), 1, 1, 0, 1, rays-1, 0)
                for p, (px, py) in enumerate(region.pixels()) for k in range(end-begin)]


class OfflineGateTests(unittest.TestCase):
    def test_simulator_matches_progressive_kernel_statistics(self):
        for name in gate.FIELDS:
            field = gate.Field(name, 7, 3.0, 'heterogeneous')
            ticks = itertools.count(1, 1000)
            kernel = ProgressiveKernel(gate.SIDE, gate.SIDE, FieldBackend(field), gate.REGIONS,
                                       clock=lambda: next(ticks))
            sim = gate.Simulator(field)
            order = [gate.REGIONS[i] for i in (0, 5, 0, 0, 5, 63, 0)]
            for region in order:
                kernel.sample_region(WorkRequest(region, gate.BATCH))
                sim.sample(region)
            for k, s in zip(kernel.observe(), sim.states('deterministic')):
                self.assertEqual((k.samples_per_pixel, k.sample_count, k.charged_rays),
                                 (s.samples_per_pixel, s.sample_count, s.charged_rays))
                for attr in ('mean', 'variance', 'standard_error'):
                    a, b = getattr(k, attr), getattr(s, attr)
                    self.assertEqual(a is None, b is None)
                    if a is not None:
                        np.testing.assert_allclose(a, b, rtol=1e-9, atol=1e-12)
                a, b = k.recent_improvement, s.recent_improvement
                self.assertEqual(a is None, b is None)
                if a is not None:
                    self.assertTrue(math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-12))

    def test_common_random_numbers_across_scales(self):
        low, high = gate.Field('lognormal', 1, 1), gate.Field('lognormal', 1, 10)
        np.testing.assert_allclose(high.draw(3, 2), 10*low.draw(3, 2))
        np.testing.assert_allclose(high.variance, 100*low.variance)

    def test_true_variance_matches_draws(self):
        for name in gate.FIELDS:
            field = gate.Field(name, 2)
            r = int(np.argmax(field.variance[:, 0]))
            x = np.concatenate([field.draw(r, b)[:, :, 0].ravel() for b in range(4000)])
            self.assertTrue(math.isclose(x.var(ddof=1), field.variance[r, 0], rel_tol=0.1), name)

    def test_oracle_matches_brute_force_with_floor(self):
        w = np.array([1., 4., 400.])
        best = min(sum(w/np.array([a, b, 120.-a-b])) for a in np.arange(16, 89, .25)
                   for b in np.arange(16, 89, .25) if 120.-a-b >= 16)
        self.assertTrue(math.isclose(gate.oracle_error(w, 120.), best, rel_tol=1e-4))
        self.assertTrue(math.isclose(gate.oracle_error(np.ones(4), 64.), 4/16))

    def test_uniform_conventional_run_is_exact_uniform(self):
        row = gate.run_conventional(('uniform', 'gaussian', 1, 0))
        weights = gate.weights_of(gate.Field('gaussian', 0))
        for h in gate.HORIZONS:
            expected = gate.oracle_error(weights, float(h*len(gate.REGIONS)))/float((weights/h).sum())
            self.assertAlmostEqual(row['efficiency'][str(h)], expected, places=12)
        self.assertEqual(row, gate.run_conventional(('uniform', 'gaussian', 1, 0)))

    def test_verdict_logic_on_fabricated_rows(self):
        def rows(adaptive):
            return [dict(method=m, field=f, scale=s, seed=0,
                         efficiency={str(h): (0.5 if m == 'uniform' else adaptive) for h in gate.HORIZONS})
                    for m in gate.CONVENTIONAL for f in gate.FIELDS for s in gate.SCALES]

        def ident(full_det_het, eq, eq_nonexplore, full_wall_hom):
            keys = {'full|wall|homogeneous': full_wall_hom, 'full|wall|heterogeneous': 0.,
                    'full|deterministic|homogeneous': 0., 'full|deterministic|heterogeneous': full_det_het}
            rates = {k: dict(d=v, d_nonexplore=v, post_decisions=1) for k, v in keys.items()}
            rates['equal-cost|deterministic|homogeneous'] = dict(d=eq, d_nonexplore=eq_nonexplore, post_decisions=1)
            return [dict(field='gaussian', seed=0, rates=rates, no_feedback_total_variation=0.)]
        go = gate.evaluate(rows(0.9), ident(0.3, 0.05, 0.02, 0.06))
        self.assertEqual((go['gate_verdict'], go['controller'], go['noise_driven']), ('GO', 'DISTINCT', False))
        amend = gate.evaluate(rows(0.7), ident(0.3, 0.05, 0.02, 0.2))
        self.assertEqual((amend['gate_verdict'], amend['noise_driven']), ('AMEND-BASELINE', True))
        self.assertTrue(any(f.startswith('C1') for f in amend['competence']['adaptive-mc-ucb-region']['failures']))
        stop = gate.evaluate(rows(0.9), ident(0.12, 0.05, 0.09, 0.05))
        self.assertEqual((stop['gate_verdict'], stop['controller']), ('STOP-RETHINK', 'COLLAPSED'))

    def test_wall_cost_is_launch_dominated_and_deterministic_cost_is_rays(self):
        field = gate.Field('gaussian', 0, rays='heterogeneous')
        sim = gate.Simulator(field, ('wall', 'deterministic'))
        sim.sample(gate.REGIONS[4])
        self.assertEqual(sim.cost['deterministic'][4], float(field.rays[4]))
        self.assertGreater(sim.cost['wall'][4], 0.9*0.3/64)


if __name__ == '__main__':
    unittest.main()
