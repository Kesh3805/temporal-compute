"""Bounded stock PBRT synthetic throughput probe, not full qualification."""
import argparse
import json
import platform
import subprocess
import time
from pathlib import Path

PIN = 'b4ce9687e6c695f5582997c61b0c66cf064bdb4a'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pbrt', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    scene = args.output/'synthetic.pbrt'
    scene.write_text('''LookAt 0 0 -4 0 0 0 0 1 0
Camera "perspective" "float fov" [45]
Film "rgb" "integer xresolution" [64] "integer yresolution" [64]
Sampler "independent" "integer pixelsamples" [256]
Integrator "path" "integer maxdepth" [8]
PixelFilter "box"
WorldBegin
LightSource "infinite" "rgb L" [1 1 1]
Material "diffuse" "rgb reflectance" [.4 .6 .3]
Shape "sphere"
''', encoding='utf-8')
    runs = []
    for repeat in range(3):
        image = args.output/f'sphere-{repeat}.exr'
        command = [args.pbrt, '--stats', '--nthreads', '2', '--seed', '19',
                   '--outfile', str(image), str(scene)]
        start = time.perf_counter()
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        elapsed = time.perf_counter()-start
        (args.output/f'stats-{repeat}.txt').write_text(result.stdout+result.stderr, encoding='utf-8')
        runs.append({'wall_seconds': elapsed, 'scheduled_camera_samples': 1048576,
                     'scheduled_camera_samples_per_second': 1048576/elapsed,
                     'image_bytes': image.stat().st_size})
    report = {'scope': 'unrelated synthetic sphere; no controller comparison',
              'pbrt_source_commit': PIN, 'platform': platform.platform(), 'threads': 2,
              'runs': runs, 'renderer_selected': False, 'qualification_status': 'incomplete',
              'remaining': ['arbitrary sample-index batches', 'paired sample-level replay',
                            'audited complete ray counters', 'intermediate statistics adapter',
                            'representative production/reference/storage/analysis feasibility']}
    (args.output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
