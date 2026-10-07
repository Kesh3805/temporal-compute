"""Synthetic known answers only; no primary corpus or policy rendering."""
import hashlib
import io
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np

from metrics import Perceptual, display, load_image, regional_mse, relative_mse, ssim


class Metrics(unittest.TestCase):
    def test_model_provisioning_timeout_stream_hash_and_failure(self):
        from unittest.mock import patch
        from prepare_metric_models import prepare
        payload = b'synthetic backbone bytes'
        digest = hashlib.sha256(payload).hexdigest()
        # The real packaged calibration remains checked against its frozen
        # digest. Substitute only the synthetic backbone and response.
        with tempfile.TemporaryDirectory() as directory:
            with patch('prepare_metric_models.WEIGHTS', {'alexnet-owt-7be5be79.pth': digest,
                       'alex.pth': 'df73285e35b22355a2df87cdb6b70b343713b667eddbda73e1977e0c860835c0'}), \
                    patch('prepare_metric_models.urllib.request.urlopen', return_value=io.BytesIO(payload)) as opener:
                prepare(directory)
                opener.assert_called_once_with('https://download.pytorch.org/models/alexnet-owt-7be5be79.pth', timeout=30)
                self.assertEqual((Path(directory)/'alexnet-owt-7be5be79.pth').read_bytes(), payload)
            # A provisioning timeout never publishes an unverified backbone.
            (Path(directory)/'alexnet-owt-7be5be79.pth').unlink()
            with patch('prepare_metric_models.urllib.request.urlopen', side_effect=TimeoutError('fixture')):
                with self.assertRaises(TimeoutError):
                    prepare(directory)
            self.assertFalse((Path(directory)/'alexnet-owt-7be5be79.pth').exists())

    def test_mse_known_answers_floor_only_denominator(self):
        a = np.full((16, 16, 3), 2.)
        b = np.ones_like(a)
        self.assertAlmostEqual(relative_mse(a, b), 1/(1+1e-12))
        self.assertEqual(relative_mse(b, b), 0.)
        self.assertAlmostEqual(relative_mse(b, np.zeros_like(b)), 1e12)
        self.assertAlmostEqual(relative_mse(-b, b), 4/(1+1e-12))

    def test_display_transfer_boundary_and_negative(self):
        boundary = .0031308/(1-.0031308)
        a = np.array([[[-1., 0., boundary], [1., 3., 1e6]]])
        result = display(a)
        self.assertEqual(result[0, 0, 0], 0)
        self.assertEqual(result[0, 0, 1], 0)
        self.assertAlmostEqual(result[0, 0, 2], 12.92*.0031308)
        self.assertAlmostEqual(result[0, 1, 0], 1.055*.5**(1/2.4)-.055)
        self.assertGreater(result[0, 1, 2], .99999)

    def test_ssim_constant_hand_computed_and_channel_mean(self):
        a = np.full((11, 11, 3), .2)
        b = np.full_like(a, .4)
        expected = (2*.2*.4+.01**2)/(.2**2+.4**2+.01**2)
        self.assertAlmostEqual(ssim(a, b), expected)
        self.assertAlmostEqual(ssim(a, a), 1)
        b[:, :, 0] = .2
        self.assertAlmostEqual(ssim(a, b), (1+2*expected)/3)

    def test_ssim_nonconstant_independent_scalar_window(self):
        a = np.arange(11*11*3, dtype=float).reshape(11, 11, 3)/(11*11*3)
        b = a[::-1].copy()
        weights = np.exp(-np.arange(-5, 6)**2/(2*1.5**2))
        weights /= weights.sum()
        scores = []
        for c in range(3):
            ma = sum(a[y, x, c]*weights[y]*weights[x] for y in range(11) for x in range(11))
            mb = sum(b[y, x, c]*weights[y]*weights[x] for y in range(11) for x in range(11))
            va = sum((a[y, x, c]-ma)**2*weights[y]*weights[x] for y in range(11) for x in range(11))
            vb = sum((b[y, x, c]-mb)**2*weights[y]*weights[x] for y in range(11) for x in range(11))
            cov = sum((a[y, x, c]-ma)*(b[y, x, c]-mb)*weights[y]*weights[x] for y in range(11) for x in range(11))
            scores.append(((2*ma*mb+.01**2)*(2*cov+.03**2))/((ma*ma+mb*mb+.01**2)*(va+vb+.03**2)))
        self.assertAlmostEqual(ssim(a, b), sum(scores)/3, places=12)

    def test_regional_hot_fixture_tie_order_and_edges(self):
        reference = np.ones((32, 32, 3))
        a = reference.copy()
        a[16:, :16] = 3
        result = regional_mse(a, reference)
        self.assertEqual((result['maximum']['x'], result['maximum']['y']), (0, 16))
        self.assertAlmostEqual(result['maximum']['relative_mse'], 4/(1+1e-12))
        self.assertEqual(len(result['regions']), 4)
        with self.assertRaises(ValueError):
            regional_mse(a[:-1], reference[:-1])

    def test_canonical_hash_shape_finite_dtype(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'image.npy'
            for data, valid in [(np.ones((16, 16, 3), dtype='<f8'), True),
                                (np.ones((16, 16, 3), dtype='<f4'), False),
                                (np.ones((16, 16)), False), (np.full((16, 16, 3), np.nan), False)]:
                np.save(p, data)
                digest = hashlib.sha256(p.read_bytes()).hexdigest()
                if valid:
                    self.assertEqual(load_image(p, digest).shape, (16, 16, 3))
                else:
                    with self.assertRaises(ValueError):
                        load_image(p, digest)
            with self.assertRaises(ValueError):
                load_image(p, '0'*64)


@unittest.skipUnless(os.environ.get('TC_R1_METRIC_MODELS'), 'explicit verified metric weights required')
class OfficialPerceptual(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metric = Perceptual(os.environ['TC_R1_METRIC_MODELS'])

    def test_identity_and_official_crosscheck(self):
        import torch
        import lpips
        import torchvision
        from unittest.mock import patch
        directory = Path(os.environ['TC_R1_METRIC_MODELS'])
        # Independent official pretrained path using local verified ImageNet
        # weights; prohibit network by replacing only torchvision loader.
        backbone = torchvision.models.alexnet(weights=None)
        backbone.load_state_dict(torch.load(directory/'alexnet-owt-7be5be79.pth', weights_only=True))
        with patch('lpips.pretrained_networks.tv.alexnet', return_value=backbone):
            official = lpips.LPIPS(net='alex', version='0.1', model_path=str(directory/'alex.pth'), verbose=False).eval()
        a = np.arange(64*64*3, dtype=float).reshape(64, 64, 3)/(64*64*3)
        b = a[::-1].copy()
        torch.set_num_threads(1)
        self.assertEqual(self.metric.score(a, a), 0)
        with torch.inference_mode():
            expected = float(official(torch.from_numpy(a.transpose(2, 0, 1).copy()).float()[None]*2-1,
                                      torch.from_numpy(b.transpose(2, 0, 1).copy()).float()[None]*2-1).item())
        self.assertGreater(expected, 0)
        self.assertAlmostEqual(self.metric.score(a, b), expected, places=7)

    def test_reference_producer_bindings_reconcile_with_f_contract(self):
        from reference_metrics import report
        with tempfile.TemporaryDirectory() as directory:
            a, b = Path(directory)/'a.npy', Path(directory)/'b.npy'
            np.save(a, np.ones((64, 64, 3), dtype='<f8'))
            np.save(b, np.ones((64, 64, 3), dtype='<f8'))
            a_sha, b_sha = (hashlib.sha256(p.read_bytes()).hexdigest() for p in (a, b))
            result = report(a, b, a_sha, b_sha, os.environ['TC_R1_METRIC_MODELS'])
            self.assertEqual(set(result['bindings']), {'a_sha256', 'b_sha256', 'implementation_sha256', 'model_sha256'})
            self.assertEqual(set(result['bindings']['model_sha256']), {'alexnet', 'lpips'})
            self.assertEqual(result['bindings']['a_sha256'], a_sha)
            self.assertEqual(result['bindings']['b_sha256'], b_sha)
            self.assertEqual(set(result['provenance']), {'core_metrics_sha256', 'packages'})
            self.assertEqual(result['metrics'], {'relative_mse_ab': 0., 'relative_mse_ba': 0., 'ssim': 1., 'lpips': 0.})


if __name__ == '__main__':
    unittest.main()
