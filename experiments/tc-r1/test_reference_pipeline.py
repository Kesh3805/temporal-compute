"""Synthetic reference histories, hash corruption and timing semantics only."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import reference_pipeline as ref


class ReferencePipelineTests(unittest.TestCase):
    def plan(self, spp=8192):
        return ref.reference_plan('diffuse-01', 'f0', 'a' * 64, 'b' * 64, spp)

    def metrics(self, passes=False):
        return dict(relative_mse_ab=0. if passes else .001,
                    relative_mse_ba=0. if passes else .001, ssim=1., lpips=0.)

    def test_stream_derivation_and_independence(self):
        key = b'tc-r1-v1|20261007|diffuse-01|f0|0|reference-a'
        self.assertEqual(ref.stream_seed('diffuse-01', 'f0', 0, 'reference-a'),
                         int.from_bytes(hashlib.sha256(key).digest()[:8], 'big'))
        self.assertNotEqual(*self.plan()['streams'].values())
        with self.assertRaises(ValueError):
            ref.stream_seed('bad|id', 'f0', 0, 'reference-a')

    def test_escalation_and_terminal_halt_preserve_history(self):
        rows = []
        for level in ref.LEVELS:
            ref.validate_progression(rows, self.plan(level))
            decision = ref.convergence_decision(level, self.metrics())
            rows.append(dict(plan=self.plan(level), decision=decision, metrics=self.metrics()))
        self.assertEqual([r['decision'] for r in rows], ['escalate', 'escalate', 'halt'])
        self.assertEqual(len(rows), 3)
        with self.assertRaises(ValueError):
            ref.validate_progression(rows, self.plan())

    def test_no_skipping_retry_identity_drift_or_after_success_failure(self):
        with self.assertRaises(ValueError):
            ref.validate_progression([], self.plan(16384))
        rows = [dict(plan=self.plan(), decision='escalate', metrics=self.metrics())]
        with self.assertRaises(ValueError):
            ref.validate_progression(rows, self.plan())
        altered = self.plan(16384)
        altered['asset_sha256'] = 'c' * 64
        with self.assertRaises(ValueError):
            ref.validate_progression(rows, altered)
        for row in [dict(plan=self.plan(), decision='converged', metrics=self.metrics(True)),
                    ref.failure_record(self.plan(), 'render', 'synthetic failure')]:
            with self.assertRaises(ValueError):
                ref.validate_progression([row], self.plan(16384))

    def test_convergence_boundaries_nonfinite_and_directional_guard(self):
        values = dict(relative_mse_ab=.0001, relative_mse_ba=.0001, ssim=.995, lpips=.01)
        self.assertEqual(ref.convergence_decision(8192, values), 'converged')
        values['relative_mse_ba'] = .000101
        self.assertEqual(ref.convergence_decision(8192, values), 'escalate')
        values['lpips'] = float('nan')
        with self.assertRaises(ValueError):
            ref.convergence_decision(8192, values)

    def test_immutable_failed_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'failure.json'
            row = ref.failure_record(self.plan(), 'synthetic', 'test')
            ref.retain_record(path, row)
            with self.assertRaises(FileExistsError):
                ref.retain_record(path, dict(row, decision='converged'))
            self.assertEqual(json.loads(path.read_text()), row)

    def test_canonical_image_corruption_dtype_shape_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'test.npy'
            image = np.full((2, 2, 3), -1., dtype='<f8')
            np.save(path, image, allow_pickle=False)
            parsed, evidence = ref.image_evidence(path, (2, 2, 3))
            self.assertEqual(evidence['sha256'], ref.sha256(path))
            np.testing.assert_array_equal(parsed, image)
            with path.open('ab') as output:
                output.write(b'corruption')
            with self.assertRaises(ValueError):
                ref.image_evidence(path, (2, 2, 3))
            for broken in (image.astype('<f4'), image[:, :, :2], image * float('inf')):
                np.save(path, broken, allow_pickle=False)
                with self.assertRaises(ValueError):
                    ref.image_evidence(path, (2, 2, 3))

    def test_model_binding_and_independent_mse_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a, b, model, code, report = [root / name for name in
                                       ('a.npy', 'b.npy', 'model.bin', 'metric.py', 'metrics.json')]
            np.save(a, np.ones((256, 256, 3), dtype='<f8'), allow_pickle=False)
            np.save(b, np.ones((256, 256, 3), dtype='<f8'), allow_pickle=False)
            model.write_bytes(b'synthetic model only')
            code.write_bytes(b'synthetic metric implementation only')
            data = dict(bindings=dict(a_sha256=ref.sha256(a), b_sha256=ref.sha256(b),
                                     implementation_sha256=ref.sha256(code),
                                     model_sha256=dict(alexnet=ref.sha256(model), lpips=ref.sha256(model))),
                        metrics=self.metrics(True))
            report.write_text(json.dumps(data))
            model_paths = dict(alexnet=model, lpips=model)
            self.assertEqual(ref.pair_record(self.plan(), a, b, report, code, model_paths)['decision'], 'converged')
            model.write_bytes(b'corrupted model')
            with self.assertRaises(ValueError):
                ref.pair_record(self.plan(), a, b, report, code, model_paths)
            data['bindings']['model_sha256'] = dict(alexnet=ref.sha256(model), lpips=ref.sha256(model))
            data['metrics']['relative_mse_ab'] = .1
            report.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                ref.pair_record(self.plan(), a, b, report, code, model_paths)

    def test_actual_ledger_retains_failure_and_rejects_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            def broken():
                raise ValueError('synthetic corrupt model')
            row = ref.retain_attempt(directory, self.plan(), broken)
            self.assertEqual(row['decision'], 'failed')
            self.assertIn('synthetic corrupt model', row['error'])
            self.assertEqual(len(list(Path(directory).glob('*.json'))), 1)
            with self.assertRaises(ValueError):
                ref.retain_attempt(directory, self.plan(16384), broken)

    def test_corpus_planner_hash_count_and_escape_guards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            asset = root / 'scene.pbrt'
            asset.write_bytes(b'synthetic bytes only; not a rendered scene')
            digest = ref.sha256(asset)
            manifest = dict(schema_version=1, resolution=[256, 256], inputs={'scene.pbrt': digest},
                            scenes=[dict(scene_id=scene, frames=[dict(frame_id=frame, path='scene.pbrt',
                                                                    sha256=digest) for frame in ('f0', 'f1', 'f2')])
                                    for scene in sorted(ref.SCENE_IDS)])
            path = root / 'manifest.json'
            path.write_text(json.dumps(manifest))
            plan = ref.corpus_plans(root, path)
            self.assertEqual(len(plan['pairs']), 30)
            self.assertEqual(plan['initial_camera_samples'], 32212254720)
            self.assertFalse(plan['final_generation_authorized'])
            asset.write_bytes(b'corrupt')
            with self.assertRaises(ValueError):
                ref.corpus_plans(root, path)
            asset.write_bytes(b'synthetic bytes only; not a rendered scene')
            manifest['scenes'][0]['frames'][0]['path'] = '../escape.pbrt'
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                ref.corpus_plans(root, path)
            manifest['scenes'].pop()
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                ref.corpus_plans(root, path)

    def test_scoring_mean_preserves_negatives_and_large_finite_values(self):
        a = np.full((1, 1, 3), 1e308, dtype='<f8')
        np.testing.assert_array_equal(ref.scoring_reference(a, a), a)
        np.testing.assert_array_equal(ref.scoring_reference(-a, a), np.zeros_like(a))

    def test_timing_orders_and_completion_boundary(self):
        policies = ['uniform', 'adaptive', 'variance', 'tc']
        orders = ref.timing_orders('diffuse-01', 'f0', 0, policies)
        self.assertEqual(orders, ref.timing_orders('diffuse-01', 'f0', 0, policies))
        self.assertEqual(len(orders), 3)
        self.assertTrue(all(set(order) == set(policies) for order in orders))
        calls = []
        with patch.object(ref.time, 'perf_counter_ns', side_effect=[100, 170]):
            result, elapsed = ref.time_completed_cpu_work(lambda: calls.append('work'),
                                                         lambda: calls.append('completed'))
        self.assertEqual(calls, ['work', 'completed'])
        self.assertIsNone(result)
        self.assertEqual(elapsed, 70)

    def test_timing_censor_reason_cap_and_overshoot_retained(self):
        self.assertTrue(ref.timing_record(10, 1., 3, True, 'target')['event'])
        capped = ref.timing_record(1200000000, 1., 10, False, 'time-cap')
        self.assertEqual(capped['followup_seconds'], 1.)
        self.assertAlmostEqual(capped['completion_overshoot_seconds'], .2)
        self.assertTrue(capped['primary_time_eligible'])
        self.assertFalse(ref.timing_record(10, 1., 10, False, 'ray-cap')['primary_time_eligible'])
        for args in [(10, None, 3, False, 'ray-cap'), (10, 1., 3, False, 'time-cap'),
                     (10, 1., 3, True, 'ray-cap'), (2000000000, 1., 3, True, 'target')]:
            with self.assertRaises(ValueError):
                ref.timing_record(*args)

    def test_host_inspection_is_not_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = ref.inspect_host(directory)
        self.assertFalse(manifest['selected_execution_host'])
        self.assertGreater(manifest['storage_free_bytes'], 0)
        self.assertIn('time_cap_seconds', manifest['missing_execution_fields'])


if __name__ == '__main__':
    unittest.main()
