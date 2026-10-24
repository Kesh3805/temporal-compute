"""Worker equivalence validation (contract tc-r1-worker-validation-v1).

Compares the persistent worker against the qualified per-process e3 bridge,
request by request, as sorted multisets of sample, event and Film log lines.
Non-primary fixtures only. Writes one report; any mismatch is FAIL.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from amended_policies import AmendedConventionalPolicy  # noqa: E402
from cached_kernel import CachedProgressiveKernel  # noqa: E402
from pbrt_batch_backend import PbrtBatchBackend  # noqa: E402
from persistent_backend import PersistentPbrtBackend  # noqa: E402
from progressive_kernel import ProgressiveKernel, Region, WorkRequest  # noqa: E402

CONTRACT = ROOT/'research/tc-r1/worker-validation/contract.json'
LOGS = ('.samples.csv', '.events.csv', '.film.csv')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Bench:
    def __init__(self, contract, e3, e3_manifest, worker, worker_manifest, scratch):
        self.contract, self.scratch = contract, Path(scratch)
        self.e3, self.e3_manifest, self.worker, self.worker_manifest = e3, e3_manifest, worker, worker_manifest
        self.admitted = set(contract['fixtures'].values())
        self.counter = 0

    def scene(self, fixture):
        return ROOT/self.contract['fixture_paths'][fixture], self.contract['fixtures'][fixture]

    def out(self, label):
        self.counter += 1
        return self.scratch/f'{self.counter:03d}-{label}'

    def identity(self, fixture):
        return ('worker-validation', fixture.removesuffix('.pbrt'), 0, 'allocation')

    def per_process(self, binary, manifest, fixture, requests, label):
        scene, digest = self.scene(fixture)
        out = self.out(label)
        backend = PbrtBatchBackend(binary, manifest, scene, digest, self.identity(fixture), out,
                                   threads=1, admitted_scenes=self.admitted)
        return [self.lines(out, i, backend.render(Region(*r), b, e))
                for i, (r, b, e) in enumerate(requests)]

    def persistent(self, fixture, requests, threads, label):
        scene, digest = self.scene(fixture)
        out = self.out(label)
        backend = PersistentPbrtBackend(self.worker, self.worker_manifest, scene, digest, self.identity(fixture),
                                        out, threads=threads, admitted_scenes=self.admitted)
        rows = [self.lines(out, i, backend.render(Region(*r), b, e)) for i, (r, b, e) in enumerate(requests)]
        backend.close()
        return rows

    @staticmethod
    def lines(out, index, samples):
        prefix = out/f'batch-{index:08d}'
        return {suffix: sorted(prefix.with_suffix(suffix).read_text().splitlines()) for suffix in LOGS}


def compare(reference, candidate):
    mismatches = []
    for i, (a, b) in enumerate(zip(reference, candidate)):
        for suffix in LOGS:
            if a[suffix] != b[suffix]:
                diff = sorted(set(a[suffix]) ^ set(b[suffix]))[:3]
                mismatches.append(dict(request=i, log=suffix, lines=(len(a[suffix]), len(b[suffix])), example=diff))
    if len(reference) != len(candidate):
        mismatches.append(dict(request_count=(len(reference), len(candidate))))
    return mismatches


def equivalence(bench):
    rows = []
    for fixture in bench.contract['fixtures']:
        requests = bench.contract['requests']['big' if fixture == 'throughput-256.pbrt' else 'small']
        qualified = bench.per_process(bench.e3, bench.e3_manifest, fixture, requests, 'e3-'+fixture)
        for threads in (1, 2):
            worker = bench.persistent(fixture, requests, threads, f'worker-t{threads}-'+fixture)
            rows.append(dict(fixture=fixture, threads=threads, requests=len(requests),
                             sample_lines=sum(len(r['.samples.csv']) for r in qualified),
                             mismatches=compare(qualified, worker)))
        if fixture != 'throughput-256.pbrt':
            batch = bench.per_process(bench.worker, bench.worker_manifest, fixture, requests, 'wbatch-'+fixture)
            rows.append(dict(fixture=fixture, mode='worker-binary-batch-mode', requests=len(requests),
                             mismatches=compare(qualified, batch)))
    return rows


def state_without_cost(state):
    value = asdict(state)
    value.pop('estimated_sample_cost')
    return value


def kernel_run(bench):
    spec = bench.contract['kernel_run']
    scene, digest = bench.scene(spec['fixture'])
    regions = tuple(Region(x, x+8, y, y+8) for y in (0, 8) for x in (0, 8))
    qualified = ProgressiveKernel(16, 16, PbrtBatchBackend(bench.e3, bench.e3_manifest, scene, digest,
                                  bench.identity(spec['fixture']), bench.out('kernel-e3'), threads=1,
                                  admitted_scenes=bench.admitted), regions)
    worker_backend = PersistentPbrtBackend(bench.worker, bench.worker_manifest, scene, digest,
                                           bench.identity(spec['fixture']), bench.out('kernel-worker'), threads=1,
                                           admitted_scenes=bench.admitted)
    worker = CachedProgressiveKernel(16, 16, worker_backend, regions)
    policies = (AmendedConventionalPolicy('variance-guided'), AmendedConventionalPolicy('variance-guided'))
    problems = []
    for step in range(spec['decisions']):
        a, b = (p.choose(k.observe()) for p, k in zip(policies, (qualified, worker)))
        if a != b:
            problems.append(dict(step=step, issue='different request'))
            break
        qualified.sample_region(a)
        worker.sample_region(b)
        if [state_without_cost(s) for s in qualified.observe()] != [state_without_cost(s) for s in worker.observe()]:
            problems.append(dict(step=step, issue='observed state differs'))
            break
    strip = [{k: v for k, v in t.items() if k != 'elapsed_ns'} for t in qualified.trace]
    if strip != [{k: v for k, v in t.items() if k != 'elapsed_ns'} for t in worker.trace]:
        problems.append(dict(issue='trace differs'))
    if qualified.image() != worker.image():
        problems.append(dict(issue='final image differs'))
    worker_backend.close()
    return dict(decisions=spec['decisions'], problems=problems)


def failure(bench):
    scene, digest = bench.scene('diffuse.pbrt')
    backend = PersistentPbrtBackend(bench.worker, bench.worker_manifest, scene, digest, bench.identity('diffuse.pbrt'),
                                    bench.out('failure'), threads=1, admitted_scenes=bench.admitted)
    backend.render(Region(0, 8, 0, 8), 0, 4)
    backend._proc.kill()
    backend._proc.wait()
    outcomes = []
    for _ in range(2):
        try:
            backend.render(Region(0, 8, 0, 8), 4, 8)
            outcomes.append('accepted')
        except (RuntimeError, ValueError, OSError) as error:
            outcomes.append(type(error).__name__+': '+str(error)[:80])
    record = json.loads((backend.output/'batch-00000001.json').read_text())
    ok = (outcomes[0] != 'accepted' and 'cannot be retried' in outcomes[1] and
          record['status'] == 'failed' and record['work_known'] is False)
    return dict(outcomes=outcomes, passed=ok)


def timing(bench):
    spec = bench.contract['timing']
    scene, digest = bench.scene(spec['fixture'])
    result = {}
    for label in ('qualified', 'worker'):
        if label == 'qualified':
            backend = PbrtBatchBackend(bench.e3, bench.e3_manifest, scene, digest, bench.identity(spec['fixture']),
                                       bench.out('timing-e3'), threads=1, admitted_scenes=bench.admitted)
            kernel = ProgressiveKernel(256, 256, backend)
        else:
            backend = PersistentPbrtBackend(bench.worker, bench.worker_manifest, scene, digest,
                                            bench.identity(spec['fixture']), bench.out('timing-worker'), threads=1,
                                            admitted_scenes=bench.admitted)
            kernel = CachedProgressiveKernel(256, 256, backend)
        start = time.perf_counter()
        for region in kernel.regions[:spec['requests']]:
            kernel.sample_region(WorkRequest(region, 4))
        result[label] = (time.perf_counter() - start)/spec['requests']
        if label == 'worker':
            backend.close()
    result['speedup'] = result['qualified']/result['worker']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('e3', 'e3-manifest', 'worker', 'worker-manifest', 'output'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    contract = json.loads(CONTRACT.read_text(encoding='utf-8'))
    if contract['schema'] != 'tc-r1-worker-validation-v1':
        raise ValueError('wrong worker validation contract')
    worker_manifest = json.loads(Path(args.worker_manifest).read_text())
    if worker_manifest['worker_source_sha256'] != contract['worker_source_sha256']:
        raise ValueError('worker build does not match the contract')
    with open(args.output, 'x', encoding='utf-8') as reserve:
        reserve.write('{"status": "started"}\n')
    with tempfile.TemporaryDirectory() as scratch:
        bench = Bench(contract, args.e3, args.e3_manifest, args.worker, args.worker_manifest, scratch)
        checks = dict(equivalence=equivalence(bench), kernel_run=kernel_run(bench), failure=failure(bench))
        speed = timing(bench)
    passed = (all(not row['mismatches'] for row in checks['equivalence']) and
              not checks['kernel_run']['problems'] and checks['failure']['passed'])
    report = dict(schema='tc-r1-worker-validation-report-v1', verdict='PASS' if passed else 'FAIL',
                  contract_sha256=sha(CONTRACT), e3_binary_sha256=sha(args.e3), worker_binary_sha256=sha(args.worker),
                  source_sha256={n: sha(HERE/n) for n in ('worker_validation.py', 'worker_instrument.py',
                                                          'persistent_backend.py', 'cached_kernel.py',
                                                          'pbrt_batch_backend.py', 'progressive_kernel.py')},
                  checks=checks, timing=speed, primary_scenes_used=False, references_produced=False,
                  policy_comparison=False)
    Path(args.output).write_text(json.dumps(report, indent=1)+'\n', encoding='utf-8')
    print(json.dumps(dict(verdict=report['verdict'], timing=speed)))


if __name__ == '__main__':
    main()
