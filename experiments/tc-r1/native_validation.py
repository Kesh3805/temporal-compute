"""Bounded native correctness evidence; never a primary experiment runner."""
import argparse
from collections import Counter
import csv
from dataclasses import asdict, is_dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from unittest.mock import patch

import corpus
from baselines import ConventionalPolicy
from integration_budget import validate_sample_bound
from paired_policy_runner import PairedPolicyRunner
from pbrt_batch_backend import PbrtBatchBackend, close, load_batch
from progressive_kernel import ProgressiveKernel, Region, WorkRequest, pbrt_seed_map, require
from tc_controller import TcPolicy

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT/'research/tc-r1/native-validation'
CONTRACT_COMMIT = '0da7a7f33a52815773f32eb01710f3eae74eb366'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    def encode(item):
        if is_dataclass(item):
            return asdict(item)
        raise TypeError(type(item).__name__)
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False, default=encode)+'\n', encoding='utf-8')


def verify_contract():
    path = DIRECTORY/'contract.json'
    value = json.loads(path.read_text())
    frozen = subprocess.check_output(['git', 'show', CONTRACT_COMMIT+':research/tc-r1/native-validation/contract.json'], cwd=ROOT)
    require(path.read_bytes() == frozen, 'validation contract changed after freeze')
    for name, digest in value['inputs'].items():
        require(sha(ROOT/name) == digest, 'bound integration input changed: '+name)
    for name, digest in value['fixtures'].items():
        require(sha(DIRECTORY/'fixtures'/name) == digest, 'synthetic fixture changed: '+name)
    require(value['tolerance'] == dict(absolute=1e-6, relative=1e-5), 'comparison tolerance')
    require(all(value[k] is False for k in ('scientific_host_selected', 'amendment_adopted',
                'reference_generation_authorized', 'comparative_execution_authorized')), 'inactive gate required')
    return value


def execution_guard(repository, attempt):
    require(attempt == '1', 'only workflow attempt 1 is authorized')
    history = subprocess.check_output(['git','rev-list','--full-history','HEAD^@','--',
                    'research/tc-r1/native-validation/execute-validation.json'],cwd=repository,text=True)
    require(not history.strip(), 'validation marker already appeared in reachable prior history')


def full_film(prefix, samples, region, begin, end):
    """Independently check ALL cumulative Film rows, not just the last index."""
    records = {(s.x, s.y, s.index): s for s in samples}
    expected = {(x, y, i) for x, y in region.pixels() for i in range(begin, end)}
    require(set(records) == expected and len(samples) == len(expected), 'Film sample ownership')
    film = {}
    for row in csv.reader(prefix.with_suffix('.film.csv').read_text().splitlines()):
        require(len(row) == 6, 'complete Film shape')
        key = tuple(map(int, row[:3]))
        rgb = tuple(map(float, row[3:]))
        require(key in expected and key not in film, 'complete Film identity or duplicate')
        x, y, index = key
        mean = tuple(math.fsum(records[x, y, i].rgb[c] for i in range(begin, index+1))/(index-begin+1)
                     for c in range(3))
        require(all(close(a, b) for a, b in zip(mean, rgb)), 'intermediate Film estimator mismatch')
        film[key] = rgb
    require(set(film) == expected, 'incomplete Film domain')
    return {(x, y): film[x, y, end-1] for x, y in region.pixels()}


def compare_samples(expected, actual):
    def mapping(samples):
        result = {(s.x, s.y, s.index): s for s in samples}
        require(len(result) == len(samples), 'duplicate cross-batch sample')
        return result
    left, right = mapping(expected), mapping(actual)
    require(set(left) == set(right), 'cross-batch sample identity mismatch')
    for key, a in left.items():
        b = right[key]
        require((a.camera, a.continuation, a.visibility) == (b.camera, b.continuation, b.visibility),
                'sample class counts depend on ordering or threads')
        require(all(close(x, y) for x, y in zip(a.rgb, b.rgb)), 'sample stream mismatch')


def compare_pixels(expected, actual):
    require(set(expected) == set(actual), 'estimator pixel domain mismatch')
    require(all(close(a, b) for p in expected for a, b in zip(expected[p], actual[p])), 'final estimator mismatch')


def complete_prefix(samples):
    indices = {}
    for sample in samples:
        key = sample.x, sample.y
        require(sample.index not in indices.setdefault(key, set()), 'reused paired sample')
        indices[key].add(sample.index)
    require(all(v == set(range(len(v))) for v in indices.values()), 'paired stream skipped an index')
    return {k: len(v) for k, v in indices.items()}


class CheckedBackend(PbrtBatchBackend):
    def __init__(self, owner, name, fixture, stream='production', threads=1):
        self.owner = owner
        self.audit = []
        self.samples = []
        scene = DIRECTORY/'fixtures'/fixture
        super().__init__(owner.binary, owner.manifest, scene, owner.contract['fixtures'][fixture],
                         ('native-'+fixture.removesuffix('.pbrt'), 'f0', 0, stream), owner.output/name,
                         threads, admitted_scenes=set(owner.contract['fixtures'].values()))

    def render(self, region, begin, end):
        require(not self._failed, 'failed checked backend cannot retry')
        self.owner.reserve()
        try:
            samples = super().render(region, begin, end)
            prefix = self.output/f'batch-{self._calls-1:08d}'
            film = full_film(prefix, samples, region, begin, end)
            actual = sum(validate_sample_bound(s.camera, s.continuation, s.visibility) for s in samples)
            require(actual == sum(s.charged_rays for s in samples), 'charged class identity')
            value = dict(begin=begin, end=end, region=asdict(region), film=film, samples=samples, charged=actual)
            self.audit.append(value)
            self.samples.extend(samples)
            write(prefix.with_suffix('.validation.json'), dict(status='PASS',
                  complete_film_rows=len(samples), charged_rays=actual, per_sample_bound=17))
            return samples
        except BaseException:
            self._failed = True
            raise


class Validation:
    def __init__(self, binary, manifest, output):
        self.contract = verify_contract()
        self.binary, self.manifest, self.output = Path(binary).resolve(), Path(manifest).resolve(), Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        require(not (self.output/'report.json').exists(), 'validation report exists; no silent rerun')
        build = json.loads(self.manifest.read_text())
        require(build['upstream_commit'] == self.contract['pbrt_commit'] and
                build['e3_source_sha256'] == self.contract['qualified_source_sha256'] and
                build['binary_sha256'] == sha(self.binary), 'native build provenance')
        require(build['cpu_float_build_verified'] is True, 'CPU-float build not verified')
        self.commands = 0
        self.report = dict(gate='TC-R1 native integration validation', status='RUNNING',
            contract_commit=CONTRACT_COMMIT, contract_sha256=sha(DIRECTORY/'contract.json'),
            implementation_sha256=sha(Path(__file__)), binary_sha256=sha(self.binary),
            build_manifest_sha256=sha(self.manifest), fixtures=self.contract['fixtures'],
            host='validation only; scientific host unselected', amendment_0002='inactive',
            comparative_outcomes=0, references_produced=0, checks={})

    def reserve(self):
        require(self.commands < self.contract['maximum_native_commands'], 'bounded native command effort exhausted')
        self.commands += 1

    def backend(self, name, fixture, stream='production', threads=1):
        return CheckedBackend(self, name, fixture, stream, threads)

    def parser(self):
        corpus.verify()
        manifest = json.loads((ROOT/'research/tc-r1/corpus/manifest.json').read_text())
        identities = [(s['scene_id'], f['frame_id'], r, stream) for s in manifest['scenes']
                      for f in s['frames'] for r in range(8) for stream in manifest['streams']['names']]
        seeds = pbrt_seed_map(identities)
        write(self.output/'registered-streams.json', [dict(identity=k, full_seed=v[0], native_seed=v[1])
                                                   for k, v in seeds.items()])
        records = []
        folder = self.output/'parser'
        folder.mkdir()
        for scene in manifest['scenes']:
            for frame in scene['frames']:
                self.reserve()
                asset = ROOT/frame['path']
                require(sha(asset) == frame['sha256'], 'primary asset changed before parse')
                command = [str(self.binary), '--format', str(asset)]
                name = scene['scene_id']+'-'+frame['frame_id']
                record = dict(asset=frame['path'], scene_sha256=frame['sha256'], command=command, status='FAIL')
                write(folder/(name+'.json'),record)
                env = {k: v for k, v in os.environ.items() if not k.startswith('TC_R1E')}
                try:
                    result = subprocess.run(command, env=env, capture_output=True, timeout=600)
                    (folder/(name+'.stdout')).write_bytes(result.stdout)
                    (folder/(name+'.stderr')).write_bytes(result.stderr)
                    record.update(returncode=result.returncode, status='PASS' if result.returncode == 0 else 'FAIL')
                except subprocess.TimeoutExpired as error:
                    (folder/(name+'.stdout')).write_bytes(error.stdout or b'')
                    (folder/(name+'.stderr')).write_bytes(error.stderr or b'')
                    record.update(error_type=type(error).__name__, error=str(error))
                except OSError as error:
                    record.update(error_type=type(error).__name__,error=str(error))
                records.append(record)
                write(folder/(name+'.json'), record)
        write(self.output/'parser-report.json', records)
        corpus.verify()
        require(len(records) == 30 and all(r['status'] == 'PASS' for r in records), 'corpus parser failed; diagnostics retained')
        self.report['checks']['corpus_parser'] = dict(status='PASS', assets=30, rendering=False, stream_identities=len(seeds))

    def estimators(self):
        summaries = {}
        for fixture in ('environment.pbrt', 'diffuse.pbrt', 'surface-paths.pbrt'):
            stem = fixture.removesuffix('.pbrt')
            whole = Region(0, 16, 0, 16)
            one = self.backend(stem+'/one', fixture)
            kernel = ProgressiveKernel(16, 16, one)
            kernel.sample_region(WorkRequest(whole, 16))
            expected = one.samples
            native_image = one.audit[0]['film']
            compare_pixels(native_image, {(x,y): kernel.image()[y][x] for x,y in whole.pixels()})
            for variant in self.contract['matrix'][1:]:
                backend = self.backend(stem+'/'+variant, fixture, threads=2 if variant in ('two-threads', 'reversed-quadrants') else 1)
                if variant == 'reversed-batches':
                    for begin in (12, 8, 4, 0):
                        backend.render(whole, begin, begin+4)
                else:
                    regions = tuple(Region(x,x+8,y,y+8) for y in (0,8) for x in (0,8)) if variant == 'reversed-quadrants' else (whole,)
                    k = ProgressiveKernel(16, 16, backend, regions)
                    for _ in range(1 if variant == 'two-threads' else 4):
                        for region in reversed(regions):
                            k.sample_region(WorkRequest(region, 16 if variant == 'two-threads' else 4))
                    compare_pixels(native_image, {(x,y): k.image()[y][x] for x,y in whole.pixels()})
                compare_samples(expected, backend.samples)
                # Independently accumulate native Film estimates with explicit batch weights.
                image = {}
                for pixel in whole.pixels():
                    batches = [a for a in backend.audit if pixel in a['film']]
                    weight = sum(a['end']-a['begin'] for a in batches)
                    require(weight == 16, 'complete estimator sample weight')
                    image[pixel] = tuple(math.fsum(a['film'][pixel][c]*(a['end']-a['begin']) for a in batches)/weight for c in range(3))
                compare_pixels(native_image, image)
            summaries[stem] = dict(status='PASS', variants=self.contract['matrix'], camera_samples_per_variant=4096)
        self.report['checks']['progressive_bridge'] = summaries

    def paired(self):
        summaries = {}
        regions = (Region(0,8,0,16), Region(8,16,0,16))
        for method in self.contract['paired_policies']:
            allocation = self.backend('paired/'+method+'/allocation', 'diffuse.pbrt', 'allocation')
            production = self.backend('paired/'+method+'/production', 'diffuse.pbrt')
            policy = TcPolicy(method.removeprefix('tc-')) if method.startswith('tc-') else ConventionalPolicy(method)
            runner = PairedPolicyRunner(16,16,allocation,production,regions)
            result = runner.run(policy, self.contract['paired_decisions'])
            write(allocation.output.parent/'paired-trace.json', result.trace)
            a, p = complete_prefix(allocation.samples), complete_prefix(production.samples)
            require(a == p and len(a) == 256 and min(a.values()) >= 16, 'paired ownership or minimum coverage')
            require(allocation.seed != production.seed, 'independent native seeds')
            lookup = {(s.x,s.y,s.index):s for s in production.samples}
            require(any(any(not close(v,w) for v,w in zip(s.rgb,lookup[s.x,s.y,s.index].rgb)) for s in allocation.samples),
                    'native fixture does not demonstrate distinct stream output')
            require(result.allocation_charged_rays == sum(s.charged_rays for s in allocation.samples) and
                    result.production_charged_rays == sum(s.charged_rays for s in production.samples), 'uncharged paired sampling')
            for entry in result.trace:
                require(entry['status'] == 'committed' and entry['request'].additional_samples == 4, 'partial paired request')
                if entry['step'] < 8:
                    require(min(s.samples_per_pixel for s in entry['allocation_before']) < 16, 'initialization order')
                elif method in ('adaptive-mc-ucb-region', 'variance-guided'):
                    for candidate in entry['candidates']:
                        state = next(s for s in entry['allocation_before'] if s.region == candidate.region)
                        n, variance = state.samples_per_pixel, math.fsum(state.variance)/3
                        index = ((math.sqrt(variance)+2/math.sqrt(n))/n if method == 'adaptive-mc-ucb-region'
                                 else variance/(n*(n+4)))
                        require(close(index,candidate.index), 'independent conventional candidate equation')
            # Reconcile the same complete per-stream prefixes against independent one-shot Film runs.
            for stream, backend in (('allocation',allocation),('production',production)):
                direct = self.backend('paired/'+method+'/'+stream+'-direct', 'diffuse.pbrt', stream)
                for region in regions:
                    direct.render(region,0,a[next(region.pixels())])
                compare_samples(backend.samples,direct.samples)
                if stream == 'production':
                    film = {pixel:rgb for batch in direct.audit for pixel,rgb in batch['film'].items()}
                    compare_pixels(film,{(x,y):result.production_image[y][x] for x,y in a})
            summaries[method] = dict(status='PASS', decisions=len(result.trace), initialization_decisions=8,
                                     independent_seeds=[allocation.seed,production.seed])
        self.report['checks']['paired_streams_and_policy_boundary'] = summaries

    def checkpoints(self):
        allocation = self.backend('checkpoints/allocation','checkpoints.pbrt','allocation')
        production = self.backend('checkpoints/production','checkpoints.pbrt')
        # Unequal legal synthetic rectangles exercise nonzero actual overshoot.
        regions = (Region(0,3,0,8),Region(3,8,0,8))
        kernels = [ProgressiveKernel(8,8,b,regions) for b in (allocation,production)]
        actual, trace, checkpoints = 0, [], []
        initialization = None
        for step in range(220):
            observed = kernels[0].observe()
            if min(s.samples_per_pixel for s in observed) < 16:
                selected = min(observed,key=lambda s:(s.samples_per_pixel,s.region.y0,s.region.x0)).region
            else:
                # Fixed action sequence, no policy quality or timing selection.
                selected = regions[1]
            request = WorkRequest(selected,4)
            before = actual
            states = [k.sample_region(request) for k in kernels]
            require(states[0].samples_per_pixel == states[1].samples_per_pixel, 'checkpoint pair identity')
            charge = sum(k.trace[-1]['charged_rays'] for k in kernels)
            require(charge <= 8704, 'synthetic complete-request bound')
            actual += charge
            require(actual == sum(s.charged_rays for b in (allocation,production) for s in b.samples), 'checkpoint cumulative actual ledger')
            trace.append(dict(step=step,before=before,pair_charge=charge,actual=actual,
                              region=asdict(selected),spp=states[0].samples_per_pixel))
            if initialization is None and min(s.samples_per_pixel for s in kernels[0].observe()) == 16:
                require(all(s.samples_per_pixel == 16 for k in kernels for s in k.observe()) and
                        actual <= 34816, 'mandatory paired initialization bound')
                initialization = actual
            target = self.contract['synthetic_thresholds'][len(checkpoints)]
            if actual >= target:
                require(initialization is not None and before < target and actual-target <= 8703, 'checkpoint crossing or overshoot')
                checkpoints.append(dict(threshold=target,actual_charged_rays=actual,overshoot=actual-target,
                                        allocation_rays=sum(s.charged_rays for s in kernels[0].observe()),
                                        production_rays=sum(s.charged_rays for s in kernels[1].observe())))
                if len(checkpoints) == 2:
                    break
        require(len(checkpoints) == 2, 'bounded synthetic checkpoint effort exhausted')
        complete_prefix(allocation.samples)
        require(complete_prefix(allocation.samples) == complete_prefix(production.samples), 'checkpoint sample prefixes')
        write(self.output/'checkpoint-trace.json', trace)
        self.report['checks']['checkpoint_mechanics'] = dict(status='PASS', synthetic_only=True,
            actual_initialization_rays=initialization, initialization_upper_bound=34816,
            paired_request_upper_bound=8704, checkpoints=checkpoints)

    def failures(self):
        original_run = subprocess.run
        def interrupt(command, **kwargs):
            process = subprocess.Popen(command, env=kwargs['env'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.terminate()
            out, err = process.communicate(timeout=30)
            prefix = Path(command[command.index('--outfile')+1]).with_suffix('')
            prefix.with_suffix('.interrupted.stdout').write_bytes(out)
            prefix.with_suffix('.interrupted.stderr').write_bytes(err)
            raise InterruptedError('deliberate native validation process termination')
        def truncate(command, **kwargs):
            result = original_run(command, **kwargs)
            require(result.returncode == 0, 'native execution failed before deliberate truncation')
            path = Path(kwargs['env']['TC_R1E_SAMPLE_LOG'])
            region = Region(*map(int,command[command.index('--pixelbounds')+1].split(',')))
            begin,end = (int(kwargs['env'][k]) for k in ('TC_R1E_SAMPLE_BEGIN','TC_R1E_SAMPLE_END'))
            prefix = Path(command[command.index('--outfile')+1]).with_suffix('')
            samples = load_batch(prefix,region,begin,end)
            full_film(prefix,samples,region,begin,end)
            for sample in samples:
                validate_sample_bound(sample.camera,sample.continuation,sample.visibility)
            data = path.read_bytes()
            path.with_suffix('.original-complete.csv').write_bytes(data)
            path.write_bytes(b'\n'.join(data.splitlines()[:-1])+b'\n')
            return result
        for label, fault in (('interrupted',interrupt),('partial-records',truncate)):
            backend = self.backend('failures/'+label,'diffuse.pbrt')
            k = ProgressiveKernel(16,16,backend)
            request = WorkRequest(k.regions[0],4)
            with patch('pbrt_batch_backend.subprocess.run', side_effect=fault):
                try:
                    k.sample_region(request)
                except (ValueError,InterruptedError) as error:
                    expected = ('deliberate native validation process termination' if label == 'interrupted'
                                else 'native sample identity domain')
                    require(str(error) == expected, 'unexpected failure in deliberate fault test: '+str(error))
                else:
                    raise ValueError('native fault accepted')
            require(not k.work_known and all(s.sample_count == 0 for s in k.observe()), 'fault estimator rollback')
            for action in (lambda:k.image(),lambda:k.sample_region(request),lambda:backend.render(request.region,0,4)):
                try:
                    action()
                except ValueError:
                    pass
                else:
                    raise ValueError('fault allowed scoring or retry')
            require(backend._calls == 1, 'native fault silently retried')
            write(backend.output/'kernel-failure.json', k.trace)
        allocation = self.backend('failures/pair/allocation','diffuse.pbrt','allocation')
        production = self.backend('failures/pair/production','diffuse.pbrt')
        runner = PairedPolicyRunner(16,16,allocation,production)
        def second_stream(command, **kwargs):
            return interrupt(command, **kwargs) if 'production' in kwargs['env']['TC_R1E_SAMPLE_LOG'] else original_run(command, **kwargs)
        with patch('pbrt_batch_backend.subprocess.run', side_effect=second_stream):
            try:
                runner.run(ConventionalPolicy('uniform'),4)
            except InterruptedError:
                pass
            else:
                raise ValueError('partial pair supplied scored result')
        require(runner.trace[-1]['work_known'] is False, 'partial pair work was declared known')
        try:
            runner.run(ConventionalPolicy('uniform'),4)
        except ValueError:
            pass
        else:
            raise ValueError('partial pair silently retried')
        require(allocation._calls == production._calls == 1, 'pair replay after interruption')
        write(self.output/'failures/pair/trace.json',runner.trace)
        self.report['checks']['failure_containment'] = dict(status='PASS', faults=['terminated-process','truncated-log','second-stream-interruption'])

    def run(self):
        try:
            for check in (self.parser,self.estimators,self.paired,self.checkpoints,self.failures):
                check()
                write(self.output/'progress.json',self.report)
            self.report['status'] = 'PASS'
        except BaseException as error:
            self.report.update(status='BLOCKED',error_type=type(error).__name__,error=str(error),
                               decision='STOP native integration; maintainer decision required; no assumption rewrite')
            raise
        finally:
            self.report['native_commands'] = self.commands
            write(self.output/'report.json',self.report)
            hashes = {p.relative_to(self.output).as_posix():sha(p) for p in sorted(self.output.rglob('*'))
                      if p.is_file() and p.name != 'artifact-hashes.json'}
            write(self.output/'artifact-hashes.json',hashes)
        return self.report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--guard-only',action='store_true')
    parser.add_argument('--pbrt',type=Path)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--output',type=Path)
    args = parser.parse_args()
    if args.guard_only:
        execution_guard(ROOT,os.environ.get('GITHUB_RUN_ATTEMPT'))
        verify_contract()
        marker = json.loads((DIRECTORY/'execute-validation.json').read_text())
        require(marker['contract_commit'] == CONTRACT_COMMIT and
                marker['contract_sha256'] == sha(DIRECTORY/'contract.json'), 'validation marker contract binding')
        print('First bounded validation attempt; frozen contract verified. No rendering.')
    else:
        require(all((args.pbrt,args.manifest,args.output)), 'binary, manifest and output required')
        print(json.dumps(Validation(args.pbrt,args.manifest,args.output).run(),indent=2))
