"""Synthetic infrastructure probe. Never loads the registered TC-R1 corpus."""
import argparse
import hashlib
import json
import math
import platform
import time
from pathlib import Path

import mitsuba as mi


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    backends = {}
    for variant in ('scalar_rgb', 'llvm_ad_rgb', 'cuda_ad_rgb'):
        try:
            mi.set_variant(variant)
            backends[variant] = {'available': True}
        except ImportError as error:
            backends[variant] = {'available': False, 'error': str(error)}
    mi.set_variant('scalar_rgb')
    scene = mi.load_dict({
        'type': 'scene', 'integrator': {'type': 'path', 'max_depth': 8},
        'sensor': {'type': 'perspective', 'fov': 45,
                   'to_world': mi.ScalarTransform4f.look_at(
                       origin=[0, 0, -4], target=[0, 0, 0], up=[0, 1, 0]),
                   'film': {'type': 'hdrfilm', 'width': 16, 'height': 16,
                            'rfilter': {'type': 'box'}},
                   'sampler': {'type': 'independent', 'sample_count': 64}},
        'environment': {'type': 'constant', 'radiance': {'type': 'rgb', 'value': 1}},
        'sphere': {'type': 'sphere', 'bsdf': {'type': 'diffuse',
                   'reflectance': {'type': 'rgb', 'value': [0.4, 0.6, 0.3]}}},
    })
    sensor, integrator = scene.sensors()[0], scene.integrator()
    sampler = mi.load_dict({'type': 'independent', 'sample_count': 64})

    def sample(x, y, index):
        # A qualification-only stable seed map. This is not the frozen sampler.
        key = f'non-tc-r1-sphere-v1:{x}:{y}:{index}'.encode()
        sampler.seed(int.from_bytes(hashlib.sha256(key).digest()[:4], 'little'))
        jitter = sampler.next_2d()
        ray, weight = sensor.sample_ray(0, sampler.next_1d(),
            mi.Point2f((x+jitter.x)/16, (y+jitter.y)/16), sampler.next_2d())
        value, valid, _ = integrator.sample(scene, sampler, mi.RayDifferential3f(ray))
        return [float(v) for v in value*weight]

    keys = [(x, y, i) for y in range(4, 8) for x in range(3, 9) for i in range(8)]
    start = time.perf_counter()
    full = {key: sample(*key) for key in keys}
    elapsed = time.perf_counter()-start
    regrouped = {key: sample(*key) for i in range(8) for key in reversed(keys) if key[2] == i}
    assert full == regrouped, 'sample stream changed with batch order'
    assert all(math.isfinite(v) for rgb in full.values() for v in rgb)
    # Intermediate statistics are sample statistics, without reference access.
    values = [full[(3, 4, i)] for i in range(8)]
    mean = [sum(rgb[c] for rgb in values)/8 for c in range(3)]
    variance = [sum((rgb[c]-mean[c])**2 for rgb in values)/7 for c in range(3)]
    native_start = time.perf_counter()
    image = mi.render(scene, seed=19, spp=64)
    native_seconds = time.perf_counter()-native_start
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image_path = args.output.with_suffix('.exr')
    mi.Bitmap(image).write(str(image_path))
    throughput = 16*16*64/native_seconds
    report = {
        'scope': 'unrelated synthetic sphere only; no TC or baseline comparison',
        'mitsuba_version': mi.__version__, 'python': platform.python_version(),
        'platform': platform.platform(), 'backend_probes': backends,
        'selected_probe_variant': 'scalar_rgb', 'renderer_selected': False,
        'bounded_region': [3, 9, 4, 8], 'samples_per_pixel': 8,
        'sample_records': len(keys), 'regrouped_replay_exact': full == regrouped,
        'seed_map': 'SHA256 scene:x:y:index, first 32 bits little-endian; qualification only',
        'sample_hash': hashlib.sha256(json.dumps(sorted(full.items())).encode()).hexdigest(),
        'intermediate_pixel': {'count': 8, 'mean': mean, 'variance': variance,
                               'standard_error': [math.sqrt(v/8) for v in variance]},
        'manual_sample_seconds': elapsed, 'native_render_seconds': native_seconds,
        'native_camera_samples': 16384, 'native_camera_samples_per_second': throughput,
        'initial_reference_camera_samples': 32212254720,
        'synthetic_throughput_reference_projection_hours': 32212254720/throughput/3600,
        'projection_limitation': 'single tiny synthetic scene, cold wall time; not corpus feasibility',
        'image_bytes': image_path.stat().st_size,
        'complete_actual_ray_accounting': False,
        'accounting_limitation': 'native integrator does not expose every traced ray to this Python wrapper',
        'qualification_status': 'incomplete',
    }
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
