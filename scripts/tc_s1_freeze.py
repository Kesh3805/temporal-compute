"""Bind the preregistration and frozen implementation to an explicit Git tag."""
import hashlib
import json
import subprocess
from tc_s1_generate import ROOT, config, corpus, write_json

TAG = 'tc-s1-preregistered'


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT).decode().strip()


def source_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()


def write_lock():
    cfg = config()
    if subprocess.run(['git','rev-parse','--verify',TAG],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
        raise ValueError('tag already exists; do not replace the frozen specification')
    paths = [*ROOT.glob('docs/tc-s1/*.md'), *ROOT.glob('research/tc-s1/*.json'),
             *ROOT.glob('crates/**/*.rs'), *ROOT.glob('crates/*/Cargo.toml')]
    paths += [ROOT/p for p in ['Cargo.toml','Cargo.lock','rust-toolchain.toml','rustfmt.toml','clippy.toml','.cargo/config.toml',
                              'scripts/tc_s1_generate.py','scripts/tc_s1_analysis.py','scripts/tc_s1_freeze.py','scripts/test_tc_s1.py']]
    paths = sorted(set(p for p in paths if p.name!='freeze.json'))
    baseline = {}
    for path in git('ls-tree','-r','--name-only',cfg['baseline_commit'],'crates').splitlines():
        if '/src/' in path and path.endswith('.rs'):
            original = subprocess.check_output(['git','show',f"{cfg['baseline_commit']}:{path}"],cwd=ROOT)
            actual = (ROOT/path).read_bytes().replace(b'\r\n',b'\n')
            if original != actual:
                raise ValueError(f'TC-0 runtime/policy source changed: {path}')
            baseline[path] = hashlib.sha256(original).hexdigest()
    value = dict(schema_version=1,tag=TAG,baseline_commit=cfg['baseline_commit'],baseline_sources=baseline,
                 inputs={p.relative_to(ROOT).as_posix():source_hash(p) for p in paths})
    write_json(ROOT/'research/tc-s1/freeze.json',value)


def verify_lock(require_clean=True):
    sha = git('rev-parse',f'{TAG}^{{commit}}')
    recorded = subprocess.check_output(['git','show',f'{sha}:research/tc-s1/freeze.json'],cwd=ROOT)
    current = (ROOT/'research/tc-s1/freeze.json').read_bytes().replace(b'\r\n',b'\n')
    if current != recorded:
        raise ValueError('freeze lock differs from preregistered Git commit')
    lock = json.loads(recorded)
    for path, expected in lock['inputs'].items():
        if source_hash(ROOT/path) != expected:
            raise ValueError(f'frozen input changed: {path}; document errata instead of silently retuning')
    if subprocess.run(['git','merge-base','--is-ancestor',sha,'HEAD'],cwd=ROOT).returncode:
        raise ValueError('current revision does not descend from preregistration')
    if require_clean and git('status','--porcelain','--untracked-files=normal'):
        raise ValueError('commit experiment tooling before execution; dirty source provenance is prohibited')
    return sha


def descriptors():
    rows = [(m,s) for m,s in corpus() if m['profile']=='primary']
    counts = {n:0 for n in config()['class_order']}
    groups = {}
    for m,s in rows:
        key = m['mission_mix']+'/'+m['load_regime']
        g = groups.setdefault(key,dict(instances=0,tasks=0,horizon_us=[],offered_load=[],deadline_ties=0))
        g['instances'] += 1
        g['tasks'] += len(s['tasks'])
        g['horizon_us'].append(m['acquisition_horizon_us'])
        g['offered_load'].append(m['offered_load'])
        deadlines = [t['deadline_us'] for t in s['tasks']]
        g['deadline_ties'] += len(deadlines)-len(set(deadlines))
        for t in s['tasks']:
            counts[t['id'].split('-',1)[1]] += 1
    return dict(primary_scenarios=len(rows),primary_tasks=sum(counts.values()),class_counts=counts,cells=groups,
                note='Static workload descriptors only; no policy utility/order/results.')


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    args = parser.parse_args()
    if args.write:
        write_json(ROOT/'research/tc-s1/static-descriptors.json',descriptors())
        write_lock()
        print('Prepared freeze hashes; create the explicit commit and tag before evaluation.')
    else:
        print('Verified preregistration:',verify_lock())
