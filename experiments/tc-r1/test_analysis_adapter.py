"""Adapter plumbing on fabricated unit-job outputs; no real outcome is used."""
import json
import tempfile
import unittest
from pathlib import Path

import analysis
import analysis_adapter as adapter

CAP = 600.0


def fabricate(root, drop=None, perturb=None):
    families = adapter.family_manifest()
    scenes = [s for f in analysis.FAMILIES for s in families[f]]
    for scene in scenes:
        for frame in ('f0', 'f1', 'f2'):
            for replicate in range(8):
                for repeat in range(3):
                    if drop == (scene, frame, replicate, repeat):
                        continue
                    job = Path(root)/f'{scene}-{frame}-{replicate}-{repeat}'
                    job.mkdir(parents=True)
                    order = list(adapter.NAMES)
                    for k, policy in enumerate(order):
                        scores = []
                        for i in range(1, 70):
                            seconds = 8.0*i + k + repeat
                            mse = 0.5/(i*(1+0.05*k))
                            sha = f'{policy}-{i}' + ('x' if perturb == (scene, frame, replicate, repeat, policy) else '')
                            scores.append(dict(index=i, seconds=seconds, actual=i, sha256=sha, mse=mse,
                                               ssim=min(0.999, 0.6+0.01*i), lpips=max(0.01, 0.4-0.01*i),
                                               worst_region=2*mse, joint=False))
                        result = dict(record=dict(status='complete', initialization=4_000_000), scores=scores)
                        (job/f'{policy}-result.json').write_text(json.dumps(result))
                    summary = dict(unit=dict(scene_id=scene, frame_id=frame, replicate=replicate), repeat=repeat,
                                   order=order, initialization_parity=dict(status='identical', initialization=4_000_000))
                    (job/'summary.json').write_text(json.dumps(summary))


class AdapterTests(unittest.TestCase):
    def test_complete_outputs_feed_frozen_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            fabricate(tmp)
            jobs = adapter.load_jobs(tmp)
            self.assertEqual(len(jobs), 720)
            quality, timing, problems = adapter.build(jobs, CAP)
            self.assertEqual(problems, [])
            self.assertEqual(len(quality), 6*240*4)
            self.assertEqual(len(timing), 6*240*3)
            report = analysis.analyze(adapter.family_manifest(), quality, timing, ['uniform', 'adaptive', 'variance'],
                                      CAP, dict.fromkeys(analysis.PREREQUISITES, True), replicates=20)
            self.assertEqual(report['classification'], 'INCONCLUSIVE')   # forced by the non-registered replicate count
            self.assertIn('controller', report['quality']['policy_mean_log_mse'])
            self.assertTrue(report['time']['valid'])

    def test_missing_and_nondeterministic_units_are_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            fabricate(tmp, drop=('uniform-01', 'f1', 3, 2), perturb=('diffuse-02', 'f0', 5, 1, 'tc-full'))
            _, _, problems = adapter.build(adapter.load_jobs(tmp), CAP)
            self.assertTrue(any(p.startswith('missing repeat for uniform-01/f1/3') for p in problems))
            self.assertTrue(any(p.startswith('nondeterministic checkpoint images tc-full diffuse-02/f0/5') for p in problems))


if __name__ == '__main__':
    unittest.main()
