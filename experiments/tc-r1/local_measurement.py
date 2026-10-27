"""Bounded local measurement (amendment 0005 next step; contract local-measurement-v1).

Runs inside the Linux container against the qualified e3-instrumented binary.
Non-primary fixtures only: no primary scene, reference, or policy comparison.
Measures native throughput and peak RSS, retained log bytes per sample, the
per-region spread of charged rays per sample, and where bridge dispatch time
goes. The unchanged backend and kernel are timed by wrapping the stdlib calls
they make; neither module is edited.
"""
import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import re
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import pbrt_batch_backend as backend_module  # noqa: E402
from pbrt_batch_backend import PbrtBatchBackend  # noqa: E402
from progressive_kernel import ProgressiveKernel, WorkRequest  # noqa: E402

CONTRACT = ROOT/'research/tc-r1/local-measurement/contract.json'
FIXTURE = ROOT/'research/tc-r1/local-measurement/fixtures/throughput-256.pbrt'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def timed_run(command, env=None):
    """Wall time and peak RSS of one native process via GNU time."""
    wrapped = ['/usr/bin/time', '-v'] + command
    start = time.perf_counter()
    proc = subprocess.run(wrapped, env=env, capture_output=True, text=True, timeout=1800)
    wall = time.perf_counter() - start
    if proc.returncode != 0:
        raise RuntimeError(f'native run failed: {proc.stderr[-2000:]}')
    rss_kib = int(re.search(r'Maximum resident set size \(kbytes\): (\d+)', proc.stderr).group(1))
    return wall, rss_kib


def stock_throughput(binary, repeats, threads_list, spp):
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for threads in threads_list:
            for repeat in range(repeats):
                out = Path(tmp)/f'stock-{threads}-{repeat}.exr'
                env = {k: v for k, v in os.environ.items() if not k.startswith('TC_R1E')}
                wall, rss = timed_run([binary, '--nthreads', str(threads), '--seed', '7', '--spp', str(spp),
                                       '--outfile', str(out), str(FIXTURE)], env)
                rows.append(dict(threads=threads, repeat=repeat, wall_s=wall, peak_rss_kib=rss,
                                 camera_samples=256*256*spp, camera_samples_per_s=256*256*spp/wall))
    return rows


def logged_render(binary, repeats, spp):
    rows, region_rays = [], None
    for repeat in range(repeats):
        with tempfile.TemporaryDirectory() as tmp:
            logs = {k: Path(tmp)/name for k, name in (('TC_R1E_SAMPLE_LOG', 's.csv'), ('TC_R1E2_EVENTS', 'e.csv'),
                                                     ('TC_R1E2_FILM', 'f.csv'))}
            env = {k: v for k, v in os.environ.items() if not k.startswith('TC_R1E')}
            env.update({k: str(v) for k, v in logs.items()})
            wall, rss = timed_run([binary, '--nthreads', '1', '--seed', '7', '--spp', str(spp),
                                   '--outfile', str(Path(tmp)/'l.exr'), str(FIXTURE)], env)
            sizes = {k: v.stat().st_size for k, v in logs.items()}
            samples, rays = 0, 0
            per_region = {}
            with open(logs['TC_R1E_SAMPLE_LOG'], newline='') as handle:
                for row in csv.reader(handle):
                    x, y, total = int(row[0]), int(row[1]), int(row[9])
                    samples += 1
                    rays += total
                    key = (x//16, y//16)
                    count, charge = per_region.get(key, (0, 0))
                    per_region[key] = (count+1, charge+total)
            raw = b''.join(v.read_bytes() for v in logs.values())
            compressed = len(gzip.compress(raw, 6))
            rows.append(dict(repeat=repeat, wall_s=wall, peak_rss_kib=rss, camera_samples=samples,
                             charged_rays=rays, rays_per_sample=rays/samples,
                             bytes_per_sample={k: v/samples for k, v in sizes.items()},
                             total_bytes_per_sample=sum(sizes.values())/samples, gzip_ratio=len(raw)/compressed))
            if region_rays is None:
                region_rays = sorted(charge/count for count, charge in per_region.values())
    q = statistics.quantiles(region_rays, n=20)
    logs_ = [math.log(v) for v in region_rays]
    spread = dict(regions=len(region_rays), min=region_rays[0], p5=q[0], median=statistics.median(region_rays),
                  p95=q[-1], max=region_rays[-1], log_sd=statistics.pstdev(logs_))
    return rows, spread


class Clock:
    """Accumulates wall time of wrapped calls by label."""
    def __init__(self):
        self.totals = {}

    def wrap(self, label, function):
        def wrapped(*args, **kwargs):
            start = time.perf_counter()
            try:
                return function(*args, **kwargs)
            finally:
                self.totals[label] = self.totals.get(label, 0.0) + time.perf_counter() - start
        return wrapped


def bridge_latency(binary, manifest, repeats, requests):
    rows = []
    fixture_hash = sha(FIXTURE)
    original = dict(sha256=backend_module.hashlib.sha256, run=backend_module.subprocess.run,
                    load=backend_module.load_batch, observe=ProgressiveKernel.observe)
    try:
        for repeat in range(repeats):
            clock = Clock()
            backend_module.hashlib.sha256 = clock.wrap('provenance_hash', original['sha256'])
            backend_module.subprocess.run = clock.wrap('native_process', original['run'])
            backend_module.load_batch = clock.wrap('log_validation', original['load'])
            ProgressiveKernel.observe = clock.wrap('kernel_observe', original['observe'])
            with tempfile.TemporaryDirectory() as tmp:
                backend = PbrtBatchBackend(binary, manifest, FIXTURE, fixture_hash,
                                           ('local-measurement', 'f0', repeat, 'allocation'), Path(tmp)/'out',
                                           threads=1, admitted_scenes={fixture_hash})
                kernel = ProgressiveKernel(256, 256, backend)
                start = time.perf_counter()
                for region in kernel.regions[:requests]:
                    kernel.sample_region(WorkRequest(region, 4))
                total = time.perf_counter() - start
            per = {k: v/requests for k, v in clock.totals.items()}
            per['other'] = total/requests - sum(per.values())
            rows.append(dict(repeat=repeat, requests=requests, samples_per_request=16*16*4,
                             seconds_per_request=total/requests, breakdown_s=per))
    finally:
        backend_module.hashlib.sha256 = original['sha256']
        backend_module.subprocess.run = original['run']
        backend_module.load_batch = original['load']
        ProgressiveKernel.observe = original['observe']
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pbrt', required=True)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    if contract['schema'] != 'tc-r1-local-measurement-v1' or contract['fixture_sha256'] != sha(FIXTURE):
        raise ValueError('wrong measurement contract or fixture')
    # Exclusive reservation before any work; a failed attempt keeps its marker.
    with open(args.output, 'x', encoding='utf-8') as reserve:
        reserve.write('{"status": "started"}\n')
    plan = contract['plan']
    started = time.perf_counter()
    stock = stock_throughput(args.pbrt, plan['repeats'], plan['stock_threads'], plan['stock_spp'])
    logged, spread = logged_render(args.pbrt, plan['repeats'], plan['logged_spp'])
    bridge = bridge_latency(args.pbrt, args.manifest, plan['repeats'], plan['bridge_requests'])
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    children = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    report = dict(schema='tc-r1-local-measurement-report-v1', contract_sha256=sha(CONTRACT),
                  fixture_sha256=sha(FIXTURE), binary_sha256=sha(args.pbrt),
                  source_sha256={n: sha(HERE/n) for n in ('local_measurement.py', 'pbrt_batch_backend.py',
                                                          'progressive_kernel.py')},
                  host=dict(platform=sys.platform, cpus=os.cpu_count(),
                            meminfo=Path('/proc/meminfo').read_text().splitlines()[:3],
                            cpu_model=next((l.split(':', 1)[1].strip() for l in
                                            Path('/proc/cpuinfo').read_text().splitlines()
                                            if l.startswith('model name')), None)),
                  measured_seconds=time.perf_counter()-started, python_peak_rss_kib=usage,
                  children_peak_rss_kib=children, stock_throughput=stock, logged_render=logged,
                  region_rays_per_sample=spread, bridge_latency=bridge,
                  primary_scenes_used=False, references_produced=False, policy_comparison=False)
    Path(args.output).write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(dict(measured_seconds=report['measured_seconds'],
                          seconds_per_request=[r['seconds_per_request'] for r in bridge])))


if __name__ == '__main__':
    main()
