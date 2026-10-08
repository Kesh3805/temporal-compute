"""Pre-outcome reference planning, immutable evidence retention and host inspection.

No renderer invocation and no policy performance evaluation occur here. Metric
reports are supplied by Track E and bound to actual files; retained reports do
not establish their producer's correctness by themselves.
"""
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import platform
import random
import shutil
import time


LEVELS = (8192, 16384, 32768)
STREAMS = ('reference-a', 'reference-b')
MASTER_SEED = 20261007
SCENE_IDS = {f'{family}-{variant:02d}' for family in
             ('uniform', 'specular', 'diffuse', 'motion', 'adaptive') for variant in (1, 2)}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def stream_seed(scene_id, frame_id, replicate, stream):
    require(type(replicate) is int and 0 <= replicate <= 7, 'replicate must be 0..7')
    for value in (scene_id, frame_id, stream):
        require(isinstance(value, str) and value and '|' not in value, 'invalid stream identity')
    require(stream in (*STREAMS, 'allocation', 'production', 'timing-order'), 'unregistered stream')
    text = f'tc-r1-v1|{MASTER_SEED}|{scene_id}|{frame_id}|{replicate}|{stream}'
    return int.from_bytes(hashlib.sha256(text.encode('utf-8')).digest()[:8], 'big')


def reference_plan(scene_id, frame_id, asset_sha256, corpus_sha256, spp):
    require(scene_id in SCENE_IDS and frame_id in ('f0', 'f1', 'f2'), 'unregistered scene/frame')
    require(type(spp) is int and spp in LEVELS, 'unregistered reference level')
    for digest in (asset_sha256, corpus_sha256):
        require(isinstance(digest, str) and len(digest) == 64 and
                all(c in '0123456789abcdef' for c in digest), 'invalid SHA-256')
    seeds = {name: stream_seed(scene_id, frame_id, 0, name) for name in STREAMS}
    return dict(schema='tc-r1-reference-pair-v1', scene_id=scene_id, frame_id=frame_id,
                asset_sha256=asset_sha256, corpus_sha256=corpus_sha256, spp=spp,
                width=256, height=256, completed_sample_range=[0, spp], replicate=0,
                streams=seeds, pbrt_seeds={name: seed & 0x7fffffff for name, seed in seeds.items()})


def corpus_plans(repository_root, manifest_path):
    """Verify Track D bytes and join its exact 30 scene/frame pairs."""
    root = Path(repository_root).resolve()
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    require(manifest['schema_version'] == 1 and manifest['resolution'] == [256, 256],
            'corpus schema/resolution')
    require({s['scene_id'] for s in manifest['scenes']} == SCENE_IDS and
            len(manifest['scenes']) == 10, 'corpus scene identity/count')
    def verified_file(path, digest):
        require(isinstance(path, str) and '\\' not in path and ':' not in path,
                'corpus paths must be repository-relative POSIX')
        candidate = (root / path).resolve()
        require(not Path(path).is_absolute() and candidate.is_relative_to(root), 'corpus path escape')
        require(sha256(candidate) == digest, 'corpus artifact hash mismatch')
    for path, digest in manifest['inputs'].items():
        verified_file(path, digest)
    corpus_hash = sha256(manifest_path)
    plans = []
    for scene in manifest['scenes']:
        require(len(scene['frames']) == 3 and
                {f['frame_id'] for f in scene['frames']} == {'f0', 'f1', 'f2'},
                'corpus frame identity/count')
        for frame in scene['frames']:
            verified_file(frame['path'], frame['sha256'])
            plans.append(reference_plan(scene['scene_id'], frame['frame_id'],
                                        frame['sha256'], corpus_hash, LEVELS[0]))
    projected = [seed for plan in plans for seed in plan['pbrt_seeds'].values()]
    require(len(set(projected)) == len(projected), 'reference PBRT seed projection collision')
    return dict(schema='tc-r1-reference-plan-v1', final_generation_authorized=False,
                native_stream_conformance_verified=False, corpus_sha256=corpus_hash, pairs=plans,
                initial_camera_samples=30 * 2 * 256 * 256 * LEVELS[0])


def convergence_decision(spp, metrics):
    require(type(spp) is int and spp in LEVELS, 'unregistered reference level')
    names = ('relative_mse_ab', 'relative_mse_ba', 'ssim', 'lpips')
    require(set(metrics) == set(names), 'convergence metric shape')
    require(all(type(metrics[n]) in (int, float) and math.isfinite(metrics[n]) for n in names),
            'nonfinite or nonnumeric convergence metric')
    require(metrics['relative_mse_ab'] >= 0 and metrics['relative_mse_ba'] >= 0 and
            -1 <= metrics['ssim'] <= 1 and metrics['lpips'] >= 0, 'invalid convergence metric range')
    passes = (max(metrics['relative_mse_ab'], metrics['relative_mse_ba']) <= .0001 and
              metrics['ssim'] >= .995 and metrics['lpips'] <= .01)
    return 'converged' if passes else ('halt' if spp == LEVELS[-1] else 'escalate')


def validate_progression(records, next_plan):
    """Reject retries, identity drift, skipped escalation and post-terminal work."""
    expected = reference_plan(next_plan['scene_id'], next_plan['frame_id'],
                              next_plan['asset_sha256'], next_plan['corpus_sha256'], next_plan['spp'])
    require(next_plan == expected, 'reference plan differs from registered construction')
    require(len(records) < len(LEVELS), 'reference attempt limit')
    for index, record in enumerate(records):
        prior_plan = dict(expected, spp=LEVELS[index], completed_sample_range=[0, LEVELS[index]])
        require(record['plan'] == prior_plan, 'reference identity or level changed')
        require(record['decision'] == 'escalate', 'reference already terminal')
        require(convergence_decision(LEVELS[index], record['metrics']) == 'escalate',
                'invalid prior escalation')
    require(next_plan['spp'] == LEVELS[len(records)], 'reference level skipped or repeated')


def image_evidence(path, expected_shape=(256, 256, 3)):
    import numpy as np
    raw = Path(path).read_bytes()
    with io.BytesIO(raw) as source:
        image = np.load(source, allow_pickle=False)
        require(isinstance(image, np.ndarray), 'canonical image must be an NPY array')
        require(not source.read(1), 'trailing canonical image data')
    require(image.shape == expected_shape, 'canonical image dimensions')
    require(image.dtype.str == '<f8' and image.flags.c_contiguous, 'canonical image dtype/order')
    require(bool(np.isfinite(image).all()), 'nonfinite reference image')
    return image, dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                       dtype='<f8', shape=list(expected_shape))


def pair_record(plan, a_path, b_path, metrics_report_path, implementation_path, model_paths):
    """Bind externally computed perceptual metrics and independently verify MSE."""
    import numpy as np
    expected = reference_plan(plan['scene_id'], plan['frame_id'], plan['asset_sha256'],
                              plan['corpus_sha256'], plan['spp'])
    require(plan == expected, 'reference plan differs from registered construction')
    a, a_evidence = image_evidence(a_path)
    b, b_evidence = image_evidence(b_path)
    report = json.loads(Path(metrics_report_path).read_text(encoding='utf-8'))
    require(set(model_paths) == {'alexnet', 'lpips'}, 'both LPIPS and AlexNet weights required')
    bindings = dict(a_sha256=a_evidence['sha256'], b_sha256=b_evidence['sha256'],
                    implementation_sha256=sha256(implementation_path),
                    model_sha256={name: sha256(path) for name, path in model_paths.items()})
    require(report['bindings'] == bindings, 'metric report artifact bindings')
    metrics = report['metrics']
    with np.errstate(over='raise', invalid='raise'):
        numerator = float(np.sum((a - b) ** 2, dtype=np.float64))
        for name, denominator in (('relative_mse_ab', b), ('relative_mse_ba', a)):
            mse = numerator / (float(np.sum(denominator ** 2, dtype=np.float64)) + a.size * 1e-12)
            require(math.isclose(metrics[name], mse, rel_tol=1e-12, abs_tol=1e-15),
                    'metric report disagrees with reference linear MSE')
    return dict(plan=plan, decision=convergence_decision(plan['spp'], metrics), metrics=metrics,
                a=a_evidence, b=b_evidence, metric_report_sha256=sha256(metrics_report_path),
                metric_bindings=bindings)


def scoring_reference(a, b):
    """Arithmetic mean in canonical linear space; finite overflow is rejected."""
    import numpy as np
    require(a.shape == b.shape and a.ndim == 3 and a.shape[2] == 3, 'reference pair shape')
    require(np.isfinite(a).all() and np.isfinite(b).all(), 'nonfinite scoring inputs')
    # Halve first to avoid overflow in A+B for finite large radiance.
    with np.errstate(over='raise', invalid='raise'):
        result = a * .5 + b * .5
    require(np.isfinite(result).all(), 'nonfinite scoring reference')
    return np.ascontiguousarray(result, dtype='<f8')


def _publish_record(path, record, suffix='.pending'):
    """Fsync complete bytes, then atomically link without replacing any row.

    Pending evidence survives an interruption or unsupported hard-link operation.
    The final path is never visible with partial JSON contents. This requires a
    filesystem supporting same-directory hard links; unavailable support fails
    closed and must be addressed before production integration.
    """
    path = Path(path)
    payload = json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists(), 'immutable record already exists')
    pending = path.with_name(path.name + suffix)
    with pending.open('x', encoding='utf-8', newline='\n') as output:
        output.write(payload)
        output.flush()
        os.fsync(output.fileno())
    os.link(pending, path)
    pending.unlink()


def retain_record(path, record):
    """Never overwrite or automatically discard an interrupted attempt."""
    _publish_record(path, record)


def recover_interrupted_attempt(directory, plan, reason):
    """Explicitly terminalize incomplete evidence while preserving original bytes.

    A human reviews the pending artifact and supplies the registered plan/reason.
    This function does not retry a producer, delete evidence or permit escalation.
    """
    expected = reference_plan(plan['scene_id'], plan['frame_id'], plan['asset_sha256'],
                              plan['corpus_sha256'], plan['spp'])
    require(plan == expected, 'reference plan differs from registered construction')
    path = Path(directory) / f'{plan["scene_id"]}-{plan["frame_id"]}-{plan["spp"]}.json'
    pending = path.with_name(path.name + '.pending')
    reservation = path.with_name(path.name + '.attempt')
    reservation_pending = reservation.with_name(reservation.name + '.pending')
    evidence = [item for item in (pending, reservation, reservation_pending) if item.is_file()]
    require(evidence and not path.exists(), 'no unpublished interrupted attempt')
    record = failure_record(plan, 'interrupted-record', reason)
    record['interrupted_evidence'] = [dict(path=item.name, sha256=sha256(item), bytes=item.stat().st_size)
                                      for item in evidence]
    _publish_record(path, record, '.recovery-pending')
    return record


def failure_record(plan, phase, error):
    require(isinstance(phase, str) and phase and isinstance(error, str) and error,
            'failure requires phase and reason')
    return dict(plan=plan, decision='failed', phase=phase, error=error)


def retain_attempt(directory, plan, produce_record):
    """Single-writer ledger with durable failures and no automatic retry.

    The caller may prepare metrics from existing artifacts; this function never
    invokes PBRT. Concurrent producer locking is a separate integration concern.
    """
    directory = Path(directory)
    expected = reference_plan(plan['scene_id'], plan['frame_id'], plan['asset_sha256'],
                              plan['corpus_sha256'], plan['spp'])
    require(plan == expected, 'reference plan differs from registered construction')
    directory.mkdir(parents=True, exist_ok=True)
    prior = []
    for level in LEVELS:
        path = directory / f'{plan["scene_id"]}-{plan["frame_id"]}-{level}.json'
        require(not path.with_name(path.name + '.pending').exists() or path.exists(),
                'interrupted reference record requires explicit terminal recovery')
        require(not path.with_name(path.name + '.recovery-pending').exists(),
                'interrupted recovery requires human inspection')
        reservation = path.with_name(path.name + '.attempt')
        require(path.exists() or not (reservation.exists() or
                reservation.with_name(reservation.name + '.pending').exists()),
                'interrupted reference producer requires explicit terminal recovery')
        if path.exists():
            prior.append(json.loads(path.read_text(encoding='utf-8')))
    validate_progression(prior, plan)
    path = directory / f'{plan["scene_id"]}-{plan["frame_id"]}-{plan["spp"]}.json'
    reservation = path.with_name(path.name + '.attempt')
    # Reserve ownership before calling any producer. An interrupted reservation
    # or callback remains durable and cannot silently launch the work again.
    retain_record(reservation, dict(plan=plan, status='started'))
    interrupted = None
    try:
        record = produce_record()
        require(record['plan'] == plan, 'producer changed reference identity')
        require(record['decision'] == convergence_decision(plan['spp'], record['metrics']),
                'producer convergence decision mismatch')
    except BaseException as error:
        # Any producer defect blocks this pair and must survive in evidence.
        # Process interrupts remain interrupts after terminal evidence retention.
        record = failure_record(plan, 'artifact-validation', f'{type(error).__name__}: {error}')
        if not isinstance(error, Exception):
            interrupted = error
    retain_record(path, record)
    if interrupted is not None:
        raise interrupted
    return record


def timing_record(elapsed_ns, time_cap_seconds, charged_rays, attained, reason):
    require(type(elapsed_ns) is int and elapsed_ns >= 0 and
            type(charged_rays) is int and charged_rays >= 0, 'timing/count fields')
    require(type(time_cap_seconds) in (int, float) and math.isfinite(time_cap_seconds) and
            time_cap_seconds > 0, 'actual host time cap missing or invalid')
    require(type(attained) is bool, 'target event must be Boolean')
    seconds = elapsed_ns / 1e9
    require(reason in ('target', 'time-cap', 'ray-cap', 'failure'), 'timing reason')
    require(attained == (reason == 'target'), 'event/censor reason mismatch')
    if reason == 'time-cap':
        require(seconds >= time_cap_seconds, 'administrative censor must reach common cap')
    else:
        require(seconds <= time_cap_seconds, 'event/censor follow-up exceeds common cap')
    return dict(elapsed_ns=elapsed_ns, followup_seconds=min(seconds, time_cap_seconds),
                completion_overshoot_seconds=max(0., seconds - time_cap_seconds), charged_rays=charged_rays,
                event=attained, censor_reason=None if attained else reason,
                time_cap_seconds=time_cap_seconds,
                primary_time_eligible=reason in ('target', 'time-cap'))


def timing_orders(scene_id, frame_id, replicate, policies):
    """Explicit seeded permutation; its algorithm must be pinned with Python."""
    require(len(policies) >= 2 and len(set(policies)) == len(policies) and
            all(isinstance(p, str) and p for p in policies), 'policy identities')
    # Independently permute each repetition with the one registered paired stream.
    rng = random.Random(stream_seed(scene_id, frame_id, replicate, 'timing-order'))
    orders = []
    for _ in range(3):
        order = list(policies)
        rng.shuffle(order)
        orders.append(order)
    return orders


def time_completed_cpu_work(work, synchronize):
    """Caller supplies its real completion boundary; overhead remains charged."""
    start = time.perf_counter_ns()
    result = work()
    synchronize()
    elapsed = time.perf_counter_ns() - start
    return result, elapsed


def inspect_host(storage_path, binaries=()):
    """Read-only observations; not a declaration of execution-host selection."""
    memory = None
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        class MemoryStatus(ctypes.Structure):
            _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD),
                        *[(name, ctypes.c_ulonglong) for name in
                          ('physical', 'available', 'page', 'available_page', 'virtual',
                           'available_virtual', 'extended')]]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            memory = status.physical
    elif hasattr(os, 'sysconf'):
        try:
            memory = os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')
        except (ValueError, OSError):
            pass
    storage = shutil.disk_usage(storage_path)
    return dict(schema='tc-r1-host-observation-v1', selected_execution_host=False,
                os=platform.platform(), cpu_description=platform.processor(),
                logical_cpu_count=os.cpu_count(), physical_memory_bytes=memory,
                storage_total_bytes=storage.total, storage_free_bytes=storage.free,
                python_version=platform.python_version(),
                binaries={str(path): sha256(path) for path in binaries},
                missing_execution_fields=['physical_cores', 'compiler_build_flags', 'threads',
                                          'warmup', 'time_cap_seconds', 'storage_retention_location'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    host = commands.add_parser('inspect-host')
    host.add_argument('--storage', type=Path, required=True)
    host.add_argument('--binary', type=Path, action='append', default=[])
    host.add_argument('--output', type=Path, required=True)
    plan = commands.add_parser('plan-corpus')
    plan.add_argument('--repository-root', type=Path, required=True)
    plan.add_argument('--manifest', type=Path, required=True)
    plan.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'inspect-host':
        retain_record(args.output, inspect_host(args.storage, args.binary))
    elif args.command == 'plan-corpus':
        retain_record(args.output, corpus_plans(args.repository_root, args.manifest))


if __name__ == '__main__':
    main()
