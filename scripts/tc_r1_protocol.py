"""Register/verify TC-R1's protocol and preserve Generation I; never render."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TAG = 'tc-r1-protocol-preregistered'
LOCK = ROOT/'research/tc-r1/protocol-freeze.json'
BASE = '4e96ddb476b0b887ebc2bdbe397fc1fe91445536'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def digest(data):
    # Git text line endings normalize to LF; binary research artifacts stay exact.
    normalized = data if b'\0' in data else data.replace(b'\r\n', b'\n')
    return hashlib.sha256(normalized).hexdigest()


def historical_paths():
    prefixes = ('crates/', 'scenarios/', 'results/tc0/', 'results/tc-s1/', 'docs/tc-s1/', 'research/tc-s1/', 'scripts/')
    return [p for p in git('ls-tree', '-r', '--name-only', BASE).splitlines() if p.startswith(prefixes)]


def original_hashes():
    expected = {}
    for path in historical_paths():
        original = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
        expected[path] = digest(original)
        if digest((ROOT/path).read_bytes()) != expected[path]:
            raise ValueError(f'Generation I changed: {path}')
    return expected


def write():
    if LOCK.exists() or subprocess.run(['git', 'rev-parse', '--verify', TAG], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        raise ValueError('registration exists; preserve it and make a versioned amendment')
    paths = [*ROOT.glob('docs/tc-r1/*.md'), ROOT/'docs/generation-ii.md', ROOT/'docs/adr/0006-generation-ii-research-gate.md', ROOT/'research/tc-r1/protocol.json', Path(__file__).resolve()]
    value = dict(schema_version=1, tag=TAG, generation_i_base=BASE, status='protocol-only; execution freeze required',
                 inputs={p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sorted(paths)},
                 preserved_generation_i=original_hashes())
    LOCK.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('Protocol hashes prepared. Commit/tag before outcomes; no rendering performed.')


def verify():
    sha = git('rev-parse', f'{TAG}^{{commit}}')
    recorded = subprocess.check_output(['git', 'show', f'{sha}:research/tc-r1/protocol-freeze.json'], cwd=ROOT)
    if digest(LOCK.read_bytes()) != digest(recorded):
        raise ValueError('protocol lock differs from registration tag')
    value = json.loads(recorded)
    for path, expected in {**value['inputs'], **value['preserved_generation_i']}.items():
        if digest((ROOT/path).read_bytes()) != expected:
            raise ValueError(f'protected content changed: {path}')
    subprocess.run(['git', 'merge-base', '--is-ancestor', sha, 'HEAD'], cwd=ROOT, check=True)
    if git('status', '--porcelain', '--untracked-files=normal'):
        raise ValueError('dirty checkout; commit reviewable changes first')
    print(f'Protocol registration verified: {sha}; Generation I preserved; no rendering performed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    write() if args.write else verify()
