"""Extended-level decision rule and shard prefix check (amendment 0007)."""
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from reference_convergence_extended import CEILING, EXTENDED_LEVELS, decide, verified_mse

HERE = Path(__file__).resolve().parent
GOOD = dict(relative_mse_ab=5e-5, relative_mse_ba=5e-5, ssim=0.996, lpips=0.005)


def save(path, image):
    buffer = io.BytesIO()
    np.save(buffer, np.ascontiguousarray(image, dtype='<f8'), allow_pickle=False)
    Path(path).write_bytes(buffer.getvalue())
    return hashlib.sha256(buffer.getvalue()).hexdigest()


class ExtendedTests(unittest.TestCase):
    def test_levels_and_decisions(self):
        self.assertEqual((EXTENDED_LEVELS[0], CEILING), (32768, 2**21))
        self.assertEqual(decide(65536, GOOD), 'converged')
        self.assertEqual(decide(65536, dict(GOOD, relative_mse_ba=1.01e-4)), 'escalate')
        self.assertEqual(decide(65536, dict(GOOD, ssim=0.9949)), 'escalate')
        self.assertEqual(decide(CEILING, dict(GOOD, lpips=0.02)), 'halt')
        with self.assertRaises(ValueError):
            decide(50000, GOOD)

    def test_verified_mse_matches_registered_formula(self):
        a = np.full((2, 2, 3), 2.0)
        b = np.full((2, 2, 3), 1.0)
        ab, ba = verified_mse(a, b)
        self.assertAlmostEqual(ab, 12/(12+12e-12))
        self.assertAlmostEqual(ba, 12/(48+12e-12))

    def run_check(self, shard_image, registered_image, seed=7):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root/'s').mkdir()
            (root/'r').mkdir()
            sha = save(root/'s'/'x.npy', shard_image)
            (root/'s'/'x.json').write_text(json.dumps(dict(
                schema='tc-r1-reference-shard-v1', path='x.npy', identity=['specular-01', 'f0', 0, 'reference-a'],
                begin=0, end=32768, sha256=sha, binary_sha256='b', seed=7)))
            rsha = save(root/'r'/'specular-01-f0-reference-a-32768.npy', registered_image)
            (root/'r'/'specular-01-f0-reference-a-32768.json').write_text(json.dumps(dict(
                sha256=rsha, binary_sha256='b', seed=seed)))
            proc = subprocess.run([sys.executable, str(HERE/'check_shard_prefix.py'), '--shards', str(root/'s'),
                                   '--registered', str(root/'r'), '--output', str(root/'out.json')],
                                  capture_output=True, text=True)
            return proc.returncode, json.loads((root/'out.json').read_text())

    def test_prefix_check(self):
        image = np.random.default_rng(1).random((4, 4, 3))
        code, report = self.run_check(image, image)
        self.assertEqual((code, report['verdict'], report['rows'][0]['identical']), (0, 'PASS', True))
        code, report = self.run_check(image, image*(1+3e-5))
        self.assertEqual((code, report['verdict']), (1, 'FAIL'))
        code, report = self.run_check(image, image, seed=8)
        self.assertEqual(report['verdict'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
