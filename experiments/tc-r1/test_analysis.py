import copy
import math
import unittest

from analysis import (BUDGETS, FAMILIES, PREREQUISITES, Inconclusive, analyze, median_observation,
                      pass_gate, percentile, quality_effect, resamples, restricted_mean, select, target_observations)


class Analysis(unittest.TestCase):
    def test_km_hand_integrals_tied_events_and_unsupported_tail(self):
        self.assertEqual(restricted_mean([(2, True), (4, True)], 10), 3)
        self.assertEqual(restricted_mean([(10, False), (10, False)], 10), 10)
        self.assertAlmostEqual(restricted_mean([(2, True), (2, False), (10, False)], 10), 2+8*2/3)
        with self.assertRaises(Inconclusive):
            restricted_mean([(2, False)], 10)
        with self.assertRaises(ValueError):
            restricted_mean([(math.nan, True)], 10)

    def test_median_mixed_observations_identifiability(self):
        self.assertEqual(median_observation([(2, True), (3, True), (10, False)], 10), (3, True))
        self.assertEqual(median_observation([(2, True), (10, False), (10, False)], 10), (10, False))
        self.assertEqual(median_observation([(1, True), (4, True), (3, True)], 10), (3, True))
        with self.assertRaises(Inconclusive):
            median_observation([(2, False), (3, True), (4, True)], 10)

    def test_selection_exact_ties_and_geometric_aggregation(self):
        scores = {'uniform': (math.log(15)+math.log(15))/2,
                  'adaptive': (math.log(1)+math.log(100))/2,
                  'variance': (math.log(100)+math.log(2))/2}
        self.assertEqual(select(scores), 'adaptive')
        self.assertEqual(select({'variance': 1., 'uniform': 1.}), 'uniform')
        self.assertAlmostEqual(quality_effect([math.log(.5), math.log(2)]), 0)

    def test_stratification_pairing_percentiles(self):
        samples = list(resamples(replicates=2))
        self.assertEqual(samples, list(resamples(replicates=2)))
        self.assertNotEqual(samples[0], samples[1])
        for sample in samples:
            self.assertEqual(len(sample), 80)
            for scene in range(10):
                self.assertTrue(all(scene*8 <= i < (scene+1)*8 for i in sample[scene*8:(scene+1)*8]))
        self.assertEqual(percentile([0, 10], .025), .25)

    def test_first_sustained_joint_targets(self):
        points = [{'time': 1, 'mse': .001, 'ssim': .98, 'lpips': .01},
                  {'time': 2, 'mse': .02, 'ssim': .98, 'lpips': .01},
                  {'time': 3, 'mse': .001, 'ssim': .98, 'lpips': .01}]
        values = target_observations(points, 4, 10)
        self.assertEqual(values['first']['joint'], (1, True))
        self.assertEqual(values['sustained']['joint'], (3, True))
        self.assertEqual(target_observations([], 4, 10)['first']['joint'], (4, False))

    def test_every_pass_conjunct_and_invalid_preconditions(self):
        quality = {'reduction': .10, 'against_all': {p: {'interval': [.001, .5]} for p in ('uniform', 'adaptive', 'variance')}}
        families = dict(zip(FAMILIES, [.1, .1, .1, .1, -.1]))
        guard = {'regional_fraction': .90, 'ssim_degradation': .01, 'lpips_degradation': .01}
        guards = {'pooled': guard, 'families': {f: dict(guard) for f in FAMILIES}}
        time = {'valid': True, 'reduction': .05, 'interval': [.001, .5]}
        prerequisites = dict.fromkeys(PREREQUISITES, True)
        self.assertEqual(pass_gate(quality, families, guards, time, prerequisites), 'PASS')
        fixtures = []
        for key in ('reduction',):
            q = copy.deepcopy(quality); q[key] = .099; fixtures.append((q, families, guards, time))
        q = copy.deepcopy(quality); q['against_all']['uniform']['interval'][0] = 0; fixtures.append((q, families, guards, time))
        f = dict(families); f[FAMILIES[0]] = 0; fixtures.append((quality, f, guards, time))
        for key, value in [('regional_fraction', .899), ('ssim_degradation', .01001), ('lpips_degradation', .01001)]:
            g = copy.deepcopy(guards); g['pooled'][key] = value; fixtures.append((quality, families, g, time))
        for key in ('ssim_degradation', 'lpips_degradation'):
            g = copy.deepcopy(guards); g['families'][FAMILIES[0]][key] = .02; fixtures.append((quality, families, g, time))
        t = dict(time); t['reduction'] = .049; fixtures.append((quality, families, guards, t))
        t = dict(time); t['interval'] = [0, .5]; fixtures.append((quality, families, guards, t))
        for args in fixtures:
            self.assertEqual(pass_gate(*args, prerequisites), 'FAIL')
        for key in prerequisites:
            p = dict(prerequisites); p[key] = False
            self.assertEqual(pass_gate(quality, families, guards, time, p), 'INCONCLUSIVE')
        t = dict(time); t['valid'] = False
        self.assertEqual(pass_gate(quality, families, guards, t, prerequisites), 'INCONCLUSIVE')

    def test_complete_synthetic_report_ablations_missing_units_and_early_censoring(self):
        manifest = {family: [f's{i}-0', f's{i}-1'] for i, family in enumerate(FAMILIES)}
        policies = ['uniform', 'adaptive', 'variance', 'controller', 'no-feedback', 'equal-cost']
        quality, timing = [], []
        for p in policies:
            for scenes in manifest.values():
                for s in scenes:
                    for seed in range(8):
                        for f in ('f0', 'f1', 'f2'):
                            for b in BUDGETS:
                                quality.append(dict(policy=p, scene_id=s, frame_id=f, replicate=seed, checkpoint=b,
                                                    mse=.5 if p == 'controller' else 1, ssim=.99, lpips=.01, worst_region=1.))
                            for repeat in range(3):
                                events = dict.fromkeys(('mse', 'ssim', 'lpips', 'joint'), (4. if p == 'controller' else 5., True))
                                timing.append(dict(policy=p, scene_id=s, frame_id=f, replicate=seed, repeat=repeat,
                                                   first=events, sustained=events))
        args = (manifest, quality, timing, ['uniform', 'adaptive', 'variance'], 10., dict.fromkeys(PREREQUISITES, True))
        result = analyze(*args, replicates=20)
        self.assertEqual(result['quality']['comparator'], 'uniform')
        self.assertEqual(result['time']['comparator'], 'uniform')
        self.assertAlmostEqual(result['quality']['reduction'], .5)
        self.assertAlmostEqual(result['time']['reduction'], .2)
        self.assertEqual(result['classification'], 'INCONCLUSIVE')  # test bootstrap not registered10000
        self.assertEqual(len(result['retained_quality_rows']), 5760)
        with self.assertRaises(ValueError):
            analyze(manifest, quality[:-1], *args[2:], replicates=20)
        with self.assertRaises(ValueError):
            analyze(manifest, quality, timing[:-1], *args[3:], replicates=20)
        for row in timing:
            if row['replicate'] == 0:
                row['first'] = dict.fromkeys(('mse', 'ssim', 'lpips', 'joint'), (2., False))
                row['sustained'] = row['first']
        result = analyze(*args, replicates=20)
        self.assertFalse(result['time']['valid'])
        self.assertEqual(result['classification'], 'INCONCLUSIVE')


if __name__ == '__main__':
    unittest.main()
