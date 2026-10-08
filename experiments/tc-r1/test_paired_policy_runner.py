"""Paired synthetic backend correctness, never native rendering."""
from unittest.mock import patch
import unittest

from baselines import ConventionalPolicy
from paired_policy_runner import PairedPolicyRunner
from progressive_kernel import NativeSample, Region, WorkRequest


class NumericBackend:
    def __init__(self, stream, fail=False):
        self.identity = ('synthetic-only', 'f0', 0, stream)
        self.calls = []
        self.fail = fail

    def render(self, region, begin, end):
        self.calls.append((region, begin, end))
        if self.fail:
            raise RuntimeError('synthetic dispatch failure with unknown work')
        # Distinct pilot values and constant analytic production image; variable
        # complete/discarded continuation charges cannot be inferred from spp.
        return [NativeSample(x, y, i, ((100. + i,) * 3 if self.identity[3] == 'allocation'
                                     else (7., 7., 7.)), 1, 1, 0, 1, 1 + i % 3, 0)
                for x, y in region.pixels() for i in range(begin, end)]


def runner(allocation=None, production=None):
    ticks = iter(range(0, 100000000000, 1000000))
    return PairedPolicyRunner(3, 1, allocation or NumericBackend('allocation'),
                              production or NumericBackend('production'),
                              (Region(0, 1, 0, 1), Region(1, 3, 0, 1)), lambda: next(ticks))


class PairedRunnerTests(unittest.TestCase):
    def test_every_method_has_complete_paired_identity_cost_and_analytic_image(self):
        # Each policy is checked independently; no quality/speed comparison.
        for method in ('uniform', 'adaptive-mc-ucb-region', 'variance-guided'):
            allocation, production = NumericBackend('allocation'), NumericBackend('production')
            run = runner(allocation, production)
            result = run.run(ConventionalPolicy(method), 10)
            self.assertEqual(allocation.calls, production.calls)
            self.assertEqual(result.production_image, (((7., 7., 7.),) * 3,))
            expected = sum(region.area * sum(2 + i % 3 for i in range(begin, end))
                           for region, begin, end in allocation.calls)
            self.assertEqual(result.allocation_charged_rays, expected)
            self.assertEqual(result.production_charged_rays, expected)
            self.assertEqual(result.charged_rays, 2 * expected)
            self.assertGreater(result.elapsed_ns, 0)
            self.assertEqual(len(result.trace), 10)
            self.assertTrue(all(r['status'] == 'committed' for r in result.trace))
            final = result.trace[-1]
            self.assertEqual(final['allocation_after'].samples_per_pixel,
                             final['production_completion']['samples_per_pixel'])
            self.assertGreater(final['elapsed_ns'], 0)
            self.assertNotIn('mean', final['production_completion'])
            next_index = {region: 0 for region in run._allocation.regions}
            for region, begin, end in allocation.calls:
                self.assertEqual(begin, next_index[region])
                self.assertEqual(end - begin, 4)
                next_index[region] = end
            self.assertTrue(all(n >= 16 for n in next_index.values()))

    def test_injected_policy_observes_allocation_only_and_diagnostics_are_retained(self):
        class Policy:
            def __init__(self):
                self.inner = ConventionalPolicy('uniform')
                self.observed = []
                self.diagnostics = {'candidate': [1.]}

            def choose(self, states):
                self.observed.append(states)
                return self.inner.choose(states)
        policy = Policy()
        run = runner()
        result = run.run(policy, 8)
        observed_means = [s.mean for states in policy.observed for s in states if s.mean is not None]
        self.assertTrue(all(mean[0] >= 100. for mean in observed_means))
        self.assertEqual(result.production_image[0][0], (7., 7., 7.))
        policy.diagnostics['candidate'][0] = 99.
        self.assertEqual(result.trace[0]['candidates']['candidate'], [1.])
        result.trace[0]['candidates']['candidate'][0] = -1.
        self.assertEqual(run.trace[0]['candidates']['candidate'], [1.])

    def test_invalid_horizon_stream_and_common_requests_do_no_work(self):
        allocation, production = NumericBackend('allocation'), NumericBackend('production')
        run = runner(allocation, production)
        for horizon in (0, 7, True):
            with self.assertRaises(ValueError): run.run(ConventionalPolicy('uniform'), horizon)
        self.assertEqual(allocation.calls + production.calls, [])
        with self.assertRaises(ValueError): runner(allocation, allocation)
        production.identity = ('different-scene', 'f0', 0, 'production')
        with self.assertRaises(ValueError): runner(allocation, production)
        production.identity = ('synthetic-only', 'f0', 0, 'production')
        with patch('progressive_kernel.stream_seed', side_effect=[1, 1 + (1 << 31)]):
            with self.assertRaises(ValueError): runner(allocation, production)
        allocation._scene_sha256, production._scene_sha256 = 'one', 'two'
        with self.assertRaises(ValueError): runner(allocation, production)
        del allocation._scene_sha256, production._scene_sha256
        for request in (WorkRequest(Region(1, 3, 0, 1), 4),
                        WorkRequest(Region(0, 1, 0, 1), 16)):
            class BadPolicy:
                def choose(self, states):
                    return request
            bad = runner(allocation, production)
            with self.assertRaises(ValueError): bad.run(BadPolicy(), 8)
        self.assertEqual(allocation.calls + production.calls, [])

    def test_failed_production_retains_pilot_charge_unknown_work_and_blocks_retry(self):
        allocation, production = NumericBackend('allocation'), NumericBackend('production', fail=True)
        run = runner(allocation, production)
        with self.assertRaises(RuntimeError): run.run(ConventionalPolicy('uniform'), 8)
        self.assertGreater(run.trace[0]['allocation_charged_rays'], 0)
        self.assertEqual(run.trace[0]['status'], 'failed')
        self.assertEqual(run.trace[-1]['status'], 'failed')
        self.assertFalse(run.trace[-1]['work_known'])
        self.assertEqual(len(production.calls), 1)
        with self.assertRaises(ValueError): run.run(ConventionalPolicy('uniform'), 8)
        self.assertEqual(len(production.calls), 1)

    def test_interruptions_and_invalid_elapsed_fail_closed(self):
        run = runner()
        with patch.object(run._production, 'sample_region', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt): run.run(ConventionalPolicy('uniform'), 8)
        self.assertEqual(run.trace[-1]['error_type'], 'KeyboardInterrupt')
        self.assertFalse(run.trace[-1]['work_known'])
        with self.assertRaises(ValueError): run.run(ConventionalPolicy('uniform'), 8)
        run = runner()
        run._clock = lambda: 0
        with self.assertRaises(ValueError): run.run(ConventionalPolicy('uniform'), 8)
        self.assertEqual(run.trace[-1]['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
