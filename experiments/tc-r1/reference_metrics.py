"""Hash-bound reference-only metrics. Never runs a policy or a renderer."""
import argparse
import hashlib
import json
from pathlib import Path

from metrics import PACKAGES, WEIGHTS, Perceptual, display, load_image, relative_mse, ssim


def report(a_path, b_path, a_sha256, b_sha256, weights_directory):
    a, b = load_image(a_path, a_sha256), load_image(b_path, b_sha256)
    perceptual = Perceptual(weights_directory)
    da, db = display(a), display(b)
    return {
        'schema': 'tc-r1-reference-metrics-v1',
        'bindings': {'a_sha256': a_sha256, 'b_sha256': b_sha256,
                     'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                     'model_sha256': {'alexnet': WEIGHTS['alexnet-owt-7be5be79.pth'], 'lpips': WEIGHTS['alex.pth']}},
        'provenance': {'core_metrics_sha256': hashlib.sha256(Path(__file__).with_name('metrics.py').read_bytes()).hexdigest(),
                       'packages': PACKAGES},
        'metrics': {'relative_mse_ab': relative_mse(a, b), 'relative_mse_ba': relative_mse(b, a),
                    'ssim': ssim(da, db), 'lpips': perceptual.score(da, db)},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('a', 'b', 'a_sha256', 'b_sha256', 'weights_directory', 'output'):
        parser.add_argument('--'+name.replace('_', '-'), required=True)
    args = parser.parse_args()
    result = report(args.a, args.b, args.a_sha256, args.b_sha256, args.weights_directory)
    Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8')
