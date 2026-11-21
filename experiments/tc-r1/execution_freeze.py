"""TC-R1 execution freeze: bind every execution input by hash; verify before any comparative work.

build: write research/tc-r1/execution-freeze.json from committed files plus
external evidence (validated binary, references, cap calibration).
verify: recompute every bound hash, require a clean checkout and the freeze
file at HEAD, and refuse any difference. Execution jobs call verify first.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
FREEZE = ROOT/'research/tc-r1/execution-freeze.json'

SOURCES = (
    'progressive_kernel.py', 'cached_kernel.py', 'pbrt_batch_backend.py', 'persistent_backend.py',
    'instrument_pbrt.py', 'e2_instrument.py', 'e3_instrument.py', 'worker_instrument.py',
    'baselines.py', 'amended_policies.py', 'tc_controller.py', 'ray_cost.py', 'execution_runner.py', 'unit_job.py',
    'metrics.py', 'prepare_metric_models.py', 'requirements-metrics.txt', 'reference_pipeline.py',
    'reference_producer.py', 'reference_metrics.py', 'reference_convergence.py', 'reference_set.py',
    'analysis.py', 'analysis_adapter.py', 'checkpoint_amendment.py', 'integration_budget.py', 'execution_freeze.py',
    'reference_job.py', 'reference_validation.py', 'reference_shards.py', 'reference_convergence_extended.py',
    'check_shard_prefix.py', 'cap_calibration.py', 'worker_validation.py')
DOCUMENTS = (
    'docs/tc-r1/preregistration.md', 'docs/tc-r1/amendments/0001-comparator-selection.md',
    'docs/tc-r1/amendments/0002-initialization-aware-checkpoints.md',
    'docs/tc-r1/amendments/0003-actual-initialization-checkpoints.md',
    'docs/tc-r1/amendments/0004-comparator-competence.md', 'docs/tc-r1/amendments/0005-execution-design.md',
    'docs/tc-r1/amendments/0006-free-host-execution.md', 'docs/tc-r1/amendments/0007-extended-references.md',
    'research/tc-r1/reference-amendment-0007.json', 'research/tc-r1/cap-calibration/cap-calibration.json',
    'research/tc-r1/worker-validation/contract-v2.json', 'research/tc-r1/protocol.json',
    'research/tc-r1/integration/checkpoint-amendment-0003.json', 'research/tc-r1/comparator-amendment-0004.json',
    'research/tc-r1/execution-design-amendment-0005.json', 'research/tc-r1/execution-host-amendment-0006.json',
    'research/tc-r1/worker-validation/contract.json', 'research/tc-r1/corpus/manifest.json',
    '.github/workflows/tc-r1-execution.yml')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bound_files():
    files = {f'experiments/tc-r1/{name}': sha(HERE/name) for name in SOURCES}
    files.update({path: sha(ROOT/path) for path in DOCUMENTS})
    from reference_pipeline import corpus_plans
    plans = corpus_plans(ROOT, ROOT/'research/tc-r1/corpus/manifest.json')
    manifest = json.loads((ROOT/'research/tc-r1/corpus/manifest.json').read_text(encoding='utf-8'))
    for scene in manifest['scenes']:
        for frame in scene['frames']:
            files[frame['path']] = frame['sha256']
    return files, plans['corpus_sha256']


def build(evidence_path):
    evidence = json.loads(Path(evidence_path).read_text(encoding='utf-8'))
    files, corpus = bound_files()
    reference_set = json.loads((ROOT/evidence['reference_set']).read_text(encoding='utf-8'))
    if not reference_set['complete']:
        raise ValueError('reference set incomplete; no freeze')
    from metrics import WEIGHTS
    from execution_runner import INCREMENTS, POLICIES, SNAPSHOT_RAYS
    value = dict(
        schema='tc-r1-execution-freeze-v1', tag='tc-r1-execution-preregistered',
        protocol=dict(commit='99ad341775ed3e60bd262134783eeb2244700e76', tag='tc-r1-protocol-preregistered'),
        files=files, corpus_sha256=corpus,
        reference_set=dict(path=evidence['reference_set'], sha256=sha(ROOT/evidence['reference_set']),
                           artifact_run=evidence['reference_run'], converged=len(reference_set['converged']),
                           halted=reference_set['halted']),
        binary=dict(sha256=evidence['binary_sha256'], artifact_run=evidence['binary_run'],
                    artifact='tc-r1-validated-binary', worker_validation=evidence['worker_validation_verdict'],
                    reference_producer_validation=evidence['reference_validation_verdict']),
        cap_seconds=evidence['cap_seconds'], cap_calibration_sha256=evidence['cap_calibration_sha256'],
        models=WEIGHTS, policies=list(POLICIES), increments=list(INCREMENTS), snapshot_rays=SNAPSHOT_RAYS,
        analysis=dict(bootstrap_seed=734922, replicates=10000, conventional=['uniform', 'adaptive', 'variance']),
        job_layout=dict(jobs=720, matrix='10 scenes x 3 frames x 8 replicates, one workflow run per repeat 0..2'),
        comparative_outcomes_observed=False)
    FREEZE.write_text(json.dumps(value, indent=1)+'\n', encoding='utf-8', newline='\n')
    return value


def verify():
    if subprocess.run(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT, capture_output=True,
                      text=True).stdout.strip():
        raise ValueError('dirty checkout: frozen inputs may have changed')
    committed = subprocess.run(['git', 'show', 'HEAD:research/tc-r1/execution-freeze.json'], cwd=ROOT,
                               capture_output=True)
    if committed.returncode != 0 or committed.stdout != FREEZE.read_bytes():
        raise ValueError('freeze manifest is not the committed HEAD version')
    value = json.loads(FREEZE.read_text(encoding='utf-8'))
    files, corpus = bound_files()
    changed = sorted(p for p in set(files) | set(value['files']) if files.get(p) != value['files'].get(p))
    if changed or corpus != value['corpus_sha256']:
        raise ValueError(f'frozen inputs changed: {changed[:10]}')
    if sha(ROOT/value['reference_set']['path']) != value['reference_set']['sha256']:
        raise ValueError('reference set changed')
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('build', 'verify'))
    parser.add_argument('--evidence')
    parser.add_argument('--binary', help='verify: downloaded binary whose hash must match the freeze')
    args = parser.parse_args()
    if args.mode == 'build':
        value = build(args.evidence)
    else:
        value = verify()
        if args.binary and sha(args.binary) != value['binary']['sha256']:
            raise ValueError('execution binary differs from the frozen binary')
    print(json.dumps(dict(mode=args.mode, files=len(value['files']), cap_seconds=value['cap_seconds'],
                          binary=value['binary']['sha256'][:12])))


if __name__ == '__main__':
    main()
