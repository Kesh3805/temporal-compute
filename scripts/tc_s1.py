#!/usr/bin/env python3
"""Execute the tagged TC-S1 preregistration; never revise frozen inputs."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time
import tc_s1_generate as gen
import tc_s1_analysis as analysis
from tc_s1_freeze import git, verify_lock


def gzip_write(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('wb') as file:
        with gzip.GzipFile(filename='',fileobj=file,mode='wb',mtime=0) as writer:
            writer.write(data)


def build():
    subprocess.run(['cargo','build','--locked','--release','-p','tc-cli','--example','tc_s1_batch'],cwd=gen.ROOT,check=True)
    target = Path(os.environ.get('CARGO_TARGET_DIR','target'))
    if not target.is_absolute():
        target = gen.ROOT/target
    return target/'release/examples'/('tc_s1_batch.exe' if os.name=='nt' else 'tc_s1_batch')


def execute(out, binary, cfg):
    metadata = gen.verify()
    entries = metadata['entries']
    lookup = {(m['id'],m['profile']):m for m in entries}
    ordered = list(lookup.values())
    requests = out/'requests.jsonl'
    with requests.open('wb') as file:
        for meta,scenario in gen.corpus(cfg,sensitivities=True):
            file.write(gen.canonical(dict(scenario=scenario,seed=meta['seed'],schedulers=cfg['schedulers'])))
    rows = []
    oracle_cases = {}
    samples = {'eo-0001','eo-0011','eo-0021','eo-0031','eo-0041','eo-0071','eo-0141','eo-0200'}
    with requests.open('rb') as source, (out/'raw-reports.jsonl.gz').open('wb') as archive:
        with gzip.GzipFile(filename='',fileobj=archive,mode='wb',mtime=0,compresslevel=1) as raw:
            process = subprocess.Popen([str(binary),'evaluate'],stdin=source,stdout=subprocess.PIPE,cwd=gen.ROOT)
            try:
                for index,line in enumerate(process.stdout):
                    case = ordered[index//len(cfg['schedulers'])]
                    expected_policy = cfg['schedulers'][index%len(cfg['schedulers'])]
                    run = json.loads(line)
                    if run['scheduler']!=expected_policy or run['scenario']['name']!=case['id'] or run['seed']!=case['seed']:
                        raise ValueError('batch order/identity mismatch')
                    if gen.digest(run['scenario'])!=case['sha256']:
                        raise ValueError('executed scenario differs from frozen hash')
                    event_hash = gen.digest(run['events'])
                    row = dict(case,scheduler=run['scheduler'],metrics=run['metrics'],classes=analysis.run_projection(run,cfg),
                               event_sha256=event_hash,event_count=len(run['events']),replay_verified=True)
                    rows.append(row)
                    raw.write(line)
                    if case['profile']=='oracle':
                        oracle_cases.setdefault(case['id'],run['scenario'])
                    if case['profile']=='primary' and case['id'] in samples:
                        gzip_write(out/'corpus/traces'/f"{case['id']}-{run['scheduler']}.json.gz",gen.canonical(run))
                    if (index+1)%1200==0:
                        print(f'{index+1} replay-verified policy runs processed',flush=True)
                code = process.wait()
                if code:
                    raise RuntimeError(f'batch evaluation failed with status {code}')
            except BaseException:
                process.kill()
                process.wait()
                raise
    if len(rows)!=len(entries)*len(cfg['schedulers']):
        raise ValueError('missing or extra policy runs')
    gzip_write(out/'corpus/metrics.jsonl.gz',b''.join(gen.canonical(r) for r in rows))
    gen.write_json(out/'corpus/stream-hashes.json',{f"{r['profile']}/{r['id']}/{r['scheduler']}":r['event_sha256'] for r in rows})
    return rows,oracle_cases


def check_oracles(rows,cases,cfg):
    result = {}
    total = 0
    for id,scenario in cases.items():
        exact = analysis.oracle(scenario)
        task_lookup = {t['id']:t for t in scenario['tasks']}
        now = value = 0
        seen = set()
        for selected in exact['schedule']:
            if selected in seen:
                raise ValueError('oracle certificate repeats a task')
            seen.add(selected)
            t = task_lookup[selected]
            now = max(now,t['arrival_time_us'])+t['execution_cost_us']
            value += analysis.utility_at(t,now)
        if value!=exact['utility'] or now!=exact['completion_us']:
            raise ValueError('oracle schedule certificate failed')
        policies = {}
        for row in (r for r in rows if r['id']==id and r['profile']=='oracle'):
            actual = row['metrics']['total_utility']
            if actual>exact['utility']:
                raise ValueError('policy exceeds supposedly exact oracle')
            policies[row['scheduler']] = dict(utility=actual,regret=exact['utility']-actual,
                                               normalized_regret=analysis.ratio(exact['utility']-actual,exact['utility']),capture=analysis.ratio(actual,exact['utility']))
        result[id] = dict(exact,policies=policies)
        total += exact['utility']
    summary = {}
    for policy in cfg['schedulers']:
        values = [v['policies'][policy] for v in result.values()]
        summary[policy] = dict(total_utility=sum(v['utility'] for v in values),oracle_utility=total,
                               corpus_capture=analysis.ratio(sum(v['utility'] for v in values),total),
                               total_regret=sum(v['regret'] for v in values),worst_regret=max(v['regret'] for v in values),
                               capture_distribution=analysis.distribution([v['capture'] for v in values if v['capture'] is not None]))
    return dict(cases=result,summary=summary,note='Exact for 40 derived nine-job problems; not an oracle for the full primary corpus.')


def publish_analysis(out,rows,oracles,cfg):
    primary = [r for r in rows if r['profile']=='primary']
    aggregates = analysis.aggregate(primary,cfg)
    comparisons = analysis.paired(primary,cfg)
    sensitivities = {}
    for profile in cfg['sensitivity']:
        selected = [r for r in rows if r['profile']==profile]
        aggregate = analysis.aggregate(selected,cfg)
        best,gain = analysis.gain(aggregate,cfg)
        sensitivities[profile] = dict(strongest_baseline=best,relative_gain=gain,aggregates=aggregate,
                                      critical=analysis.critical_gate(selected,cfg),paired=analysis.paired(selected,cfg,bootstrap=False))
    outcome = analysis.verdict(primary,aggregates,comparisons,sensitivities,cfg)
    controls = {}
    for id in cfg['controls']:
        selected = [r for r in rows if r['profile']=='control' and r['id']==id]
        controls[id] = {r['scheduler']:dict(metrics=r['metrics'],classes=r['classes']) for r in selected}
        if id in ['constant-value','underload-equivalence'] and len({r['metrics']['total_utility'] for r in selected})!=1:
            raise ValueError('negative-control utility disagreement invalidates the experiment')
    groups = {field:{name:analysis.aggregate([r for r in primary if r[field]==name],cfg) for name in names}
              for field,names in [('load_regime',cfg['load_regimes']),('mission_mix',cfg['mission_mixes'])]}
    worst = {b:max(-d for d in comparisons[b]['paired_deltas']) for b in cfg['baselines']}
    gen.write_json(out/'aggregate.json',dict(policies=aggregates,gate=outcome,groups=groups,worst_paired_loss=worst))
    gen.write_json(out/'paired-comparisons.json',comparisons)
    gen.write_json(out/'class-breakdown.json',{p:a['classes'] for p,a in aggregates.items()})
    gen.write_json(out/'sensitivity.json',sensitivities)
    gen.write_json(out/'controls.json',controls)
    gen.write_json(out/'oracle.json',oracles)
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=gen.ROOT/'results/local/tc-s1')
    args = parser.parse_args()
    start = time.perf_counter()
    frozen = verify_lock()
    cfg = gen.config()
    gen.verify()
    out = args.output.resolve()
    out.mkdir(parents=True,exist_ok=True)
    binary = build()
    rows,cases = execute(out,binary,cfg)
    oracles = check_oracles(rows,cases,cfg)
    outcome = publish_analysis(out,rows,oracles,cfg)
    provenance = dict(schema_version=1,preregistration_sha=frozen,source_sha=git('rev-parse','HEAD'),dirty=False,
                      corpus_sha256=gen.digest(gen.verify()),specification_sha256=gen.digest(cfg),
                      simulation_version='tc0-1',generator_version=cfg['generator_version'],primary_scenarios=cfg['scenario_count'],
                      policy_runs=len(rows),replayed_simulations=2*len(rows),python=platform.python_version(),
                      rustc=subprocess.check_output(['rustc','--version']).decode().strip(),
                      replay='Every run compared events, metrics and decisions in Rust; per-run canonical event hashes retained.',
                      command='python scripts/tc_s1.py',raw_reports='raw-reports.jsonl.gz (local; regenerate rather than commit large full streams)')
    gen.write_json(out/'provenance.json',provenance)
    gen.write_json(out/'performance.json',dict(elapsed_seconds=time.perf_counter()-start,policy_runs=len(rows),note='Host-dependent runtime, excluded from byte-reproducible scientific artifacts.'))
    files = ['aggregate.json','paired-comparisons.json','class-breakdown.json','sensitivity.json','controls.json','oracle.json','provenance.json','corpus/metrics.jsonl.gz','corpus/stream-hashes.json']
    gen.write_json(out/'artifact-manifest.json',{f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in files})
    print(json.dumps(dict(verdict=outcome['verdict'],gates=outcome['gates'],relative_gain=outcome['relative_gain'],strongest_baseline=outcome['strongest_baseline'],policy_runs=len(rows)),indent=2))
    print('Artifacts:',out)


if __name__=='__main__':
    main()
