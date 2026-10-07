"""Only the two preregistered E3 fixtures; inherits preserved E2 evaluation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace

import e2_contract
from e3_instrument import PREREGISTRATION

FIXTURES={
    'dielectric': e2_contract.EXTRA['dielectric'],
    'trianglemesh': '''LightSource "infinite" "rgb L" [1 1 1]
LightSource "point" "point3 from" [0 2 -2] "rgb I" [60 60 60]
Material "diffuse" "rgb reflectance" [.6 .6 .6]
Shape "trianglemesh" "point3 P" [-2 -2 0  2 2 0  2 -2 0  -2 2 0]
"integer indices" [0 1 2  0 3 1]
''',
}


def require(condition,message):
    if not condition:
        raise ValueError(message)


def transmission_records(path,samples):
    seen=set()
    for row in csv.reader(path.read_text().splitlines()):
        require(len(row)==4,'transmission record shape')
        key=tuple(map(int,row[:3]))
        ordinal=int(row[3])
        require(key in samples and 1<=ordinal<=samples[key][8], 'transmission lacks charged continuation')
        event=key+(ordinal,)
        require(event not in seen,'duplicate transmission observation')
        seen.add(event)
    return seen


def sample_records(path):
    records={}
    for row in csv.reader(path.read_text().splitlines()):
        require(len(row)==13,'sample record shape')
        key=tuple(map(int,row[:3]))
        require(key not in records,'duplicate sample')
        records[key]=tuple(map(float,row[3:6]))+tuple(map(int,row[6:]))
    return records


def evaluate(binary,output):
    # Preserve the E2 evaluator code and restore its module bindings afterwards.
    previous=(e2_contract.SCENES,e2_contract.EXTRA,e2_contract.subprocess)
    original_run=subprocess.run
    classification_files=[]

    def observe_run(command,env,**kwargs):
        path=Path(command[command.index('--outfile')+1]).with_suffix('.transmission.csv')
        path.unlink(missing_ok=True)
        classification_files.append(path)
        return original_run(command,env={**env,'TC_R1E3_TRANSMISSION':str(path.resolve())},**kwargs)

    try:
        e2_contract.SCENES=FIXTURES
        e2_contract.EXTRA={}
        e2_contract.subprocess=SimpleNamespace(run=observe_run,SubprocessError=subprocess.SubprocessError)
        inherited=e2_contract.evaluate(binary,output)
    finally:
        e2_contract.SCENES,e2_contract.EXTRA,e2_contract.subprocess=previous
    coverage={}
    errors=[]
    for kind in FIXTURES:
        try:
            require(inherited['fixtures'][kind]['status']=='PASS','inherited E2 invariant failed')
            counts=[]
            identities=[]
            for path in classification_files:
                if not path.name.startswith(kind+'-'):
                    continue
                samples=sample_records(path.with_name(path.name.replace('.transmission.csv','.samples.csv')))
                if kind=='dielectric':
                    require(path.is_file(),'no native transmission observations')
                    events=transmission_records(path,samples)
                    require(bool(events),'no native transmission events')
                    counts.append(len(events))
                else:
                    require(any(v[8]>0 and v[4]>v[3] for v in samples.values()),'triangle surface continuation not exercised')
                    require(any(v[9]>0 for v in samples.values()),'triangle visibility not exercised')
                identities.append(dict(camera=sum(v[7] for v in samples.values()),
                    continuation=sum(v[8] for v in samples.values()),visibility=sum(v[9] for v in samples.values()),
                    total=sum(v[6] for v in samples.values())))
            require(bool(identities),'no retained fixture evaluations')
            scene=output/(kind+'.pbrt')
            coverage[kind]=dict(status='PASS',evaluations=len(identities),
                transmission_events_by_evaluation=counts,charges=identities,
                scene_sha256=hashlib.sha256(scene.read_bytes()).hexdigest())
        except (ValueError,OSError) as error:
            coverage[kind]=dict(status='FAIL',reason=str(error))
            errors.append(kind)
    return dict(gate='TC-R1E3',status='FAIL' if errors else 'PASS',coverage=coverage,
        inherited_estimator_accounting=inherited,preregistration=PREREGISTRATION,
        kernel_decision='PATH-TRACING QUALIFICATION STOPPED' if errors else 'PBRT SELECTED',
        comparative_outcomes='None generated',e2_changed=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--pbrt',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    binary=args.pbrt.resolve()
    manifest=json.loads(args.manifest.read_text())
    require(manifest['binary_sha256']==hashlib.sha256(binary.read_bytes()).hexdigest(),'binary provenance mismatch')
    require(manifest['e3_preregistration']==PREREGISTRATION,'preregistration mismatch')
    report=evaluate(binary,args.output)
    report['binary_sha256']=manifest['binary_sha256']
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='coverage'},indent=2))
    if report['status']!='PASS':
        raise SystemExit(1)
