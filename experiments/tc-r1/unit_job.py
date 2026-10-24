"""One execution job: one unit (scene, frame, replicate) x one timing repeat, six policies.

Amendments 0003-0006. Policies run sequentially in the registered timing-order
permutation for the repeat, each with two persistent workers. Per-dispatch logs
are hashed into compact records and deleted after validation except a seeded
1-in-1024 audit subset (0005 retention). After each run its production
snapshots are scored offline against the frame's scoring reference; the four
checkpoint snapshots are kept. Initialization charge parity across the six
policies is checked (0003).
"""
import argparse
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from checkpoint_amendment import InitializationMismatch, require_identical_initialization  # noqa: E402
from execution_runner import INCREMENTS, POLICIES, SNAPSHOT_RAYS, PolicyRun  # noqa: E402
from persistent_backend import PersistentPbrtBackend  # noqa: E402
from reference_pipeline import corpus_plans, image_evidence, scoring_reference, timing_orders  # noqa: E402

AUDIT_MODULUS = 1024
RECORD_LOCK = threading.Lock()   # both streams' backends append to one record file concurrently
JOINT = dict(mse=0.01, ssim=0.95, lpips=0.10)
CHECKPOINT_SNAPSHOTS = tuple(i//SNAPSHOT_RAYS for i in INCREMENTS)   # 1, 4, 16, 64


def audited(unit, policy, stream, dispatch):
    key = f'{unit}|{policy}|{stream}|{dispatch}'.encode('utf-8')
    return int.from_bytes(hashlib.sha256(key).digest()[:8], 'big') % AUDIT_MODULUS == 0


class RetainingBackend(PersistentPbrtBackend):
    """Hash each validated dispatch's logs into a compact record, then delete them unless audited."""
    def __init__(self, *args, unit, policy, stream, records, audit_directory, **kwargs):
        super().__init__(*args, **kwargs)
        self.unit, self.policy, self.stream = unit, policy, stream
        self.records, self.audit_directory = records, audit_directory

    def render(self, region, begin, end):
        index = self._calls
        samples = super().render(region, begin, end)
        prefix = self.output/f'batch-{index:08d}'
        metadata = json.loads(prefix.with_suffix('.json').read_text())
        logs = {suffix: prefix.with_suffix(suffix) for suffix in ('.samples.csv', '.events.csv', '.film.csv')}
        metadata['log_sha256'] = {suffix: hashlib.sha256(p.read_bytes()).hexdigest() for suffix, p in logs.items()}
        keep = audited(self.unit, self.policy, self.stream, index)
        metadata.update(dispatch=index, stream=self.stream, audit_retained=keep)
        metadata.pop('command', None)
        with RECORD_LOCK:
            self.records.write(json.dumps(metadata, separators=(',', ':'))+'\n')
        for suffix, path in logs.items():
            if keep:
                shutil.move(str(path), self.audit_directory/f'{self.policy}-{self.stream}-{index:08d}{suffix}')
            else:
                path.unlink()
        prefix.with_suffix('.json').unlink()
        return samples


def frame_entry(scene_id, frame_id):
    manifest = json.loads((ROOT/'research/tc-r1/corpus/manifest.json').read_text(encoding='utf-8'))
    for scene in manifest['scenes']:
        for frame in scene['frames']:
            if (scene['scene_id'], frame['frame_id']) == (scene_id, frame_id):
                return ROOT/frame['path'], frame['sha256']
    raise ValueError('unregistered scene/frame')


def load_reference(references, scene_id, frame_id):
    """Scoring reference from the converged level recorded for this frame."""
    summary = json.loads(Path(references).read_text(encoding='utf-8'))
    key = f'{scene_id}/{frame_id}'
    if key not in summary['converged']:
        raise ValueError(f'no converged reference for {key}')
    entry = summary['converged'][key]
    base = Path(references).parent/summary['directory']
    a, a_evidence = image_evidence(base/entry['a'])
    b, b_evidence = image_evidence(base/entry['b'])
    if (a_evidence['sha256'], b_evidence['sha256']) != (entry['a_sha256'], entry['b_sha256']):
        raise ValueError('reference image hash mismatch')
    return scoring_reference(a, b), entry


def attainment(scores, cap):
    within = [s for s in scores if s['seconds'] <= cap]
    hits = [s['joint'] for s in within]
    first = next((s['seconds'] for s in within if s['joint']), None)
    sustained = None
    for i, s in enumerate(within):
        if all(hits[i:]):
            sustained = s['seconds']
            break
    return dict(first_seconds=first, sustained_seconds=sustained, follow_up_seconds=max((s['seconds'] for s in within),
                                                                                       default=0.0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('binary', 'manifest', 'scene-id', 'frame-id', 'references', 'weights', 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--replicate', type=int, required=True)
    parser.add_argument('--repeat', type=int, choices=(0, 1, 2), required=True)
    parser.add_argument('--cap-seconds', type=float, required=True)
    parser.add_argument('--policies', default=','.join(POLICIES), help='synthetic smoke tests only')
    args = parser.parse_args()
    import metrics
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    plans = corpus_plans(ROOT, ROOT/'research/tc-r1/corpus/manifest.json')
    admitted = {p['asset_sha256'] for p in plans['pairs']}
    scene, digest = frame_entry(args.scene_id, args.frame_id)
    reference, reference_entry = load_reference(args.references, args.scene_id, args.frame_id)
    perceptual = metrics.Perceptual(args.weights)
    display_reference = metrics.display(reference)
    unit = f'{args.scene_id}|{args.frame_id}|{args.replicate}'
    selected = args.policies.split(',')
    order = [p for p in timing_orders(args.scene_id, args.frame_id, args.replicate, list(POLICIES))[args.repeat]
             if p in selected]
    (out/'audit').mkdir()
    results = {}
    for policy in order:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            snapshots = {}
            records = gzip.open(out/f'{policy}-dispatches.jsonl.gz', 'wt', encoding='utf-8')

            def backends(stream):
                return RetainingBackend(args.binary, args.manifest, scene, digest,
                                        (args.scene_id, args.frame_id, args.replicate, stream), tmp/stream,
                                        threads=1, admitted_scenes=admitted, unit=unit, policy=policy,
                                        stream=stream, records=records, audit_directory=out/'audit')

            def sink(name, index, image):
                array = np.ascontiguousarray(np.asarray(image, dtype='<f8'))
                path = tmp/f'snapshot-{index:05d}.npy'
                np.save(path, array, allow_pickle=False)
                snapshots[index] = path
                return hashlib.sha256(path.read_bytes()).hexdigest()
            try:
                record = PolicyRun(256, 256, backends, args.cap_seconds, sink, out/f'{policy}-trace.jsonl').run(policy)
            finally:
                records.close()
            scores = []
            for snap in record['snapshots']:
                image = np.load(snapshots[snap['index']], allow_pickle=False)
                display_image = metrics.display(image)
                regions = metrics.regional_mse(image, reference)
                value = dict(index=snap['index'], seconds=snap['seconds'], actual=snap['actual'], sha256=snap['sink'],
                             mse=metrics.relative_mse(image, reference), ssim=metrics.ssim(display_image, display_reference),
                             lpips=perceptual.score(display_image, display_reference),
                             worst_region=regions['maximum']['relative_mse'])
                value['joint'] = value['mse'] <= JOINT['mse'] and value['ssim'] >= JOINT['ssim'] and value['lpips'] <= JOINT['lpips']
                scores.append(value)
                if snap['index'] in CHECKPOINT_SNAPSHOTS:
                    shutil.copy(snapshots[snap['index']], out/f"{policy}-checkpoint-{snap['index']:02d}.npy")
            results[policy] = dict(record=record, scores=scores, attainment=attainment(scores, args.cap_seconds))
            (out/f'{policy}-result.json').write_text(json.dumps(results[policy], indent=1)+'\n', encoding='utf-8')
    parity = None
    if set(order) == set(POLICIES):
        try:
            parity = dict(initialization=require_identical_initialization(
                {p: results[p]['record']['initialization'] for p in POLICIES}), status='identical')
        except InitializationMismatch as error:
            parity = dict(status='mismatch', error=str(error),
                          charges={p: results[p]['record']['initialization'] for p in POLICIES})
    summary = dict(schema='tc-r1-unit-job-v1', unit=dict(scene_id=args.scene_id, frame_id=args.frame_id,
                   replicate=args.replicate), repeat=args.repeat, order=order, cap_seconds=args.cap_seconds,
                   binary_sha256=hashlib.sha256(Path(args.binary).read_bytes()).hexdigest(),
                   scene_sha256=digest, reference=reference_entry, initialization_parity=parity,
                   cpu=subprocess.run(['lscpu'], capture_output=True, text=True).stdout,
                   policies={p: dict(status=r['record']['status'], requests=r['record']['requests'],
                                     seconds=r['record']['seconds'], initialization=r['record']['initialization'],
                                     attainment=r['attainment'],
                                     checkpoint_mse=[s['mse'] for s in r['scores'] if s['index'] in CHECKPOINT_SNAPSHOTS])
                             for p, r in results.items()})
    (out/'summary.json').write_text(json.dumps(summary, indent=1)+'\n', encoding='utf-8')
    print(json.dumps({p: v['seconds'] for p, v in summary['policies'].items()}))


if __name__ == '__main__':
    main()
