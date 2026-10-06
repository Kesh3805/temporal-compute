"""Audit retained TC-S1 artifacts against frozen inputs and recomputed analysis."""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
import tc_s1_generate as gen
import tc_s1_analysis as analysis
import tc_s1 as runner


def verify(root):
    cfg = gen.config()
    manifest = gen.verify()
    for name, expected in json.loads((root/'artifact-manifest.json').read_text()).items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != expected:
            raise ValueError(f'artifact checksum mismatch: {name}')
    with gzip.open(root/'corpus/metrics.jsonl.gz', 'rt') as file:
        rows = [json.loads(line) for line in file]
    expected = {(m['profile'], m['id'], p): m for m in manifest['entries'] for p in cfg['schedulers']}
    observed = Counter((r['profile'], r['id'], r['scheduler']) for r in rows)
    if set(observed) != set(expected) or any(v != 1 for v in observed.values()):
        raise ValueError('missing, duplicate or unexpected policy run')
    hashes = json.loads((root/'corpus/stream-hashes.json').read_text())
    if len(hashes) != len(rows):
        raise ValueError('stream hash count mismatch')
    lookup = {}
    for row in rows:
        key = (row['profile'], row['id'], row['scheduler'])
        for field, value in expected[key].items():
            if row[field] != value:
                raise ValueError(f'frozen metadata mismatch: {key}/{field}')
        if not row['replay_verified']:
            raise ValueError('unverified replay')
        if hashes['/'.join(key)] != row['event_sha256']:
            raise ValueError('stream hash mismatch')
        if sum(c['utility'] for c in row['classes'].values()) != row['metrics']['total_utility']:
            raise ValueError('class utility does not reconcile')
        if sum(c['tasks'] for c in row['classes'].values()) != sum(c['completed']+c['expired_unstarted'] for c in row['classes'].values()):
            raise ValueError('task outcome counts do not reconcile')
        lookup[key] = row
    traces = list((root/'corpus/traces').glob('*.json.gz'))
    if len(traces) != 48:
        raise ValueError('missing representative traces')
    for path in traces:
        with gzip.open(path, 'rt') as file:
            run = json.load(file)
        row = lookup[('primary', run['scenario']['name'], run['scheduler'])]
        if gen.digest(run['events']) != row['event_sha256'] or gen.digest(run['scenario']) != row['sha256']:
            raise ValueError(f'trace hash mismatch: {path.name}')
        if run['metrics'] != row['metrics'] or analysis.run_projection(run, cfg) != row['classes']:
            raise ValueError('trace metrics mismatch')
    cases = {meta['id']: scenario for meta, scenario in gen.corpus(cfg, sensitivities=True) if meta['profile']=='oracle'}
    oracles = runner.check_oracles(rows, cases, cfg)
    if oracles != json.loads((root/'oracle.json').read_text()):
        raise ValueError('oracle/certificate recomputation mismatch')
    with tempfile.TemporaryDirectory(prefix='tc-s1-audit-') as temporary:
        out = Path(temporary)
        verdict = runner.publish_analysis(out, rows, oracles, cfg)
        for name in ['aggregate.json', 'paired-comparisons.json', 'class-breakdown.json', 'sensitivity.json', 'controls.json', 'oracle.json']:
            if json.loads((out/name).read_text()) != json.loads((root/name).read_text()):
                raise ValueError(f'frozen analysis recomputation mismatch: {name}')
    print(f"Audit passed: {len(rows)} runs, {len(traces)} traces, 40 exact oracles, all statistics; verdict {verdict['verdict']}.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path, nargs='?', default=gen.ROOT/'results/tc-s1')
    verify(parser.parse_args().results)
