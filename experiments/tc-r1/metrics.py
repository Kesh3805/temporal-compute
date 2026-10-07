"""Registered numeric metrics. No rendering, policy selection or implicit downloads."""
import hashlib
import importlib.metadata
from pathlib import Path

import numpy as np

PACKAGES = {'numpy': '2.4.6', 'torch': '2.8.0', 'torchvision': '0.23.0', 'lpips': '0.1.4'}
WEIGHTS = {
    'alexnet-owt-7be5be79.pth': '7be5be791159472b1fbf3c69796f7cb30dca7ad8466c2df70058c37116cdee02',
    'alex.pth': 'df73285e35b22355a2df87cdb6b70b343713b667eddbda73e1977e0c860835c0',
}


def image(value):
    a = np.asarray(value, dtype=np.float64)
    if a.ndim != 3 or a.shape[2] != 3 or min(a.shape[:2]) == 0 or not np.isfinite(a).all():
        raise ValueError('nonempty finite H,W,RGB image required')
    return a


def pair(a, b):
    a, b = image(a), image(b)
    if a.shape != b.shape:
        raise ValueError('image/reference dimensions differ')
    return a, b


def load_image(path, expected_sha256):
    path = Path(path)
    verify_hash(path, expected_sha256)
    a = np.load(path, allow_pickle=False)
    if a.dtype != np.dtype('<f8') or not a.flags.c_contiguous:
        raise ValueError('canonical little-endian float64 C-order image required')
    return image(a)


def verify_hash(path, expected):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != expected:
        raise ValueError(f'content hash mismatch: {Path(path).name}')


def relative_mse(a, reference):
    a, reference = pair(a, reference)
    with np.errstate(over='raise', invalid='raise'):
        result = float(np.sum((a-reference)**2) / (np.sum(reference**2)+reference.size*1e-12))
    if not np.isfinite(result):
        raise ValueError('nonfinite MSE')
    return result


def display(a):
    a = np.maximum(image(a), 0)
    mapped = a / (1+a)
    return np.where(mapped <= 0.0031308, 12.92*mapped, 1.055*mapped**(1/2.4)-0.055)


def ssim(a, b):
    """Display RGB, population covariance, valid 11x11 Gaussian windows."""
    a, b = pair(a, b)
    if min(a.shape[:2]) < 11:
        raise ValueError('SSIM requires at least 11x11')
    if np.any(a < 0) or np.any(a > 1) or np.any(b < 0) or np.any(b > 1):
        raise ValueError('SSIM expects display data in [0,1]')
    g = np.exp(-np.arange(-5, 6, dtype=np.float64)**2/(2*1.5**2))
    g /= g.sum()
    kernel = np.outer(g, g)

    def average(x):
        windows = np.lib.stride_tricks.sliding_window_view(x, (11, 11), axis=(0, 1))
        return np.einsum('hwcij,ij->hwc', windows, kernel, optimize=True)

    ma, mb = average(a), average(b)
    va, vb = average(a*a)-ma*ma, average(b*b)-mb*mb
    covariance = average(a*b)-ma*mb
    value = ((2*ma*mb+0.01**2)*(2*covariance+0.03**2))/((ma*ma+mb*mb+0.01**2)*(va+vb+0.03**2))
    return float(value.mean())


def regional_mse(a, reference):
    a, reference = pair(a, reference)
    h, w, _ = a.shape
    if h % 16 or w % 16:
        raise ValueError('regional metric requires dimensions divisible by 16')
    records = [{'x': x, 'y': y, 'relative_mse': relative_mse(a[y:y+16, x:x+16], reference[y:y+16, x:x+16])}
               for y in range(0, h, 16) for x in range(0, w, 16)]
    return {'maximum': max(records, key=lambda r: r['relative_mse']), 'regions': records}


class Perceptual:
    """Official LPIPS0.1 AlexNet, verified local weights only, CPU inference."""
    def __init__(self, weights_directory):
        import torch
        import torchvision
        import lpips
        for package, expected in PACKAGES.items():
            actual = importlib.metadata.version(package).split('+')[0]
            if actual != expected:
                raise ValueError(f'package revision mismatch: {package} {actual}')
        directory = Path(weights_directory)
        for name, digest in WEIGHTS.items():
            verify_hash(directory/name, digest)
        # pnet_rand avoids torchvision's implicit pretrained download. Replace
        # every feature tensor with the verified official ImageNet state below.
        self.model = lpips.LPIPS(net='alex', version='0.1', pnet_rand=True,
                                 model_path=str(directory/'alex.pth'), verbose=False)
        backbone = torchvision.models.alexnet(weights=None)
        backbone.load_state_dict(torch.load(directory/'alexnet-owt-7be5be79.pth', map_location='cpu', weights_only=True))
        features = list(backbone.features.children())
        offsets = (0, 2, 5, 8, 10, 12)
        for i in range(5):
            target = getattr(self.model.net, f'slice{i+1}')
            for j in range(offsets[i], offsets[i+1]):
                target._modules[str(j)].load_state_dict(features[j].state_dict())
        self.model.eval()
        self.model.requires_grad_(False)
        self.torch = torch

    def score(self, a, b):
        a, b = pair(a, b)
        if min(a.shape[:2]) < 64:
            raise ValueError('LPIPS fixtures/images require at least 64x64')
        if np.any(a < 0) or np.any(a > 1) or np.any(b < 0) or np.any(b > 1):
            raise ValueError('LPIPS expects display data in [0,1]')
        def tensor(x):
            return self.torch.from_numpy(np.ascontiguousarray(x.transpose(2, 0, 1), dtype=np.float32))[None]*2-1
        with self.torch.inference_mode():
            result = float(self.model(tensor(a), tensor(b)).item())
        if not np.isfinite(result) or result < 0:
            raise ValueError('invalid LPIPS output')
        return result


def reference_convergence(a, b, perceptual):
    a, b = pair(a, b)
    da, db = display(a), display(b)
    values = {'relative_mse': max(relative_mse(a, b), relative_mse(b, a)),
              'ssim': ssim(da, db), 'lpips': perceptual.score(da, db)}
    return {**values, 'valid': values['relative_mse'] <= 0.0001 and values['ssim'] >= 0.995 and values['lpips'] <= 0.01}


def score(a, reference_a, reference_b, perceptual):
    reference_a, reference_b = pair(reference_a, reference_b)
    convergence = reference_convergence(reference_a, reference_b, perceptual)
    if not convergence['valid']:
        raise ValueError('reference convergence failed')
    reference = reference_a/2+reference_b/2
    da, dr = display(a), display(reference)
    regions = regional_mse(a, reference)
    return {'mse': relative_mse(a, reference), 'ssim': ssim(da, dr),
            'lpips': perceptual.score(da, dr), 'worst_region': regions['maximum']['relative_mse'],
            'regional_distribution': regions['regions'], 'reference_convergence': convergence}
