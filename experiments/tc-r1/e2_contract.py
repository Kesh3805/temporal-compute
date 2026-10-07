"""One bounded E2 synthetic evaluation. Failed contracts are retained, never tuned."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

from qualify_pbrt import BASE, SCENES

EXTRA={
 'dielectric': 'LightSource "infinite" "rgb L" [1 1 1]\nMaterial "dielectric" "float eta" [1.5]\nShape "sphere"\n',
 'area': '''AttributeBegin
Translate 0 2 -2
AreaLightSource "diffuse" "rgb L" [30 30 30] "bool twosided" [true]
Shape "sphere" "float radius" [.25]
AttributeEnd
Material "diffuse" "rgb reflectance" [.6 .6 .6]
Shape "sphere"
''',
 'roulette': 'LightSource "point" "point3 from" [0 0 -3] "rgb I" [1 1 1]\nMaterial "diffuse" "rgb reflectance" [.1 .1 .1]\nShape "sphere" "float radius" [10]\n',
}


def close(a,b):
    return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=1e-6+1e-5*max(abs(a),abs(b))


def require(condition,message):
    if not condition:
        raise ValueError(message)


def evaluate(binary,output):
    results={}
    failures=[]
    for scene_id,geometry in {**SCENES,**EXTRA}.items():
        scene=output/(scene_id+'.pbrt')
        scene.write_text(BASE.replace('[256]','[16]')+geometry)

        def run(label,begin,end,region,threads):
            prefix=output/(scene_id+'-'+label)
            env={k:v for k,v in os.environ.items() if not k.startswith('TC_R1E')}
            sample=prefix.with_suffix('.samples.csv')
            film=prefix.with_suffix('.film.csv')
            events=prefix.with_suffix('.events.csv')
            for p in (sample,film,events):
                p.unlink(missing_ok=True)
            env.update(TC_R1E_SAMPLE_BEGIN=str(begin),TC_R1E_SAMPLE_END=str(end),
                TC_R1E_SAMPLE_LOG=str(sample.resolve()),TC_R1E2_FILM=str(film.resolve()),
                TC_R1E2_EVENTS=str(events.resolve()))
            command=[str(binary),'--nthreads',str(threads),'--seed','19','--pixelbounds',
                ','.join(map(str,region)),'--outfile',str(prefix.with_suffix('.exr').resolve()),str(scene.resolve())]
            proc=subprocess.run(command,env=env,capture_output=True,text=True,timeout=120)
            prefix.with_suffix('.log').write_text(proc.stdout+proc.stderr)
            require(proc.returncode==0,'renderer failed: '+label)
            for p in (sample,film,events):
                require(p.is_file(),'missing fresh log: '+str(p))
            records={}
            for row in csv.reader(sample.read_text().splitlines()):
                require(len(row)==13,'sample record shape')
                key=tuple(map(int,row[:3]))
                require(key not in records,'duplicate sample')
                records[key]=tuple(map(float,row[3:6]))+tuple(map(int,row[6:]))
            expected={(x,y,i) for x in range(region[0],region[1]) for y in range(region[2],region[3]) for i in range(begin,end)}
            require(set(records)==expected,'sample identity domain')
            ledger=Counter(tuple(map(int,row[:3]))+(row[3],) for row in csv.reader(events.read_text().splitlines()))
            for key,v in records.items():
                camera,regular,shadow,total,charged_camera,continuation,visibility=v[3:]
                require(total==charged_camera+continuation+visibility,'common charged identity')
                require(camera==charged_camera==1 and shadow==visibility and regular-camera<=continuation,'trace generation coverage')
                for kind,count in [('camera',charged_camera),('continuation',continuation),('visibility',visibility)]:
                    require(ledger[key+(kind,)]==count,'event ledger mismatch')
            require(sum(ledger.values())==sum(v[6] for v in records.values()),'ledger extra events')
            final={}
            for row in csv.reader(film.read_text().splitlines()):
                require(len(row)==6,'Film record shape')
                if int(row[2])==end-1:
                    final[tuple(map(int,row[:2]))]=tuple(map(float,row[3:]))
            require(set(final)=={k[:2] for k in expected},'Film pixel domain')
            for pixel,rgb in final.items():
                mean=[math.fsum(records[pixel+(i,)][c] for i in range(begin,end))/(end-begin) for c in range(3)]
                require(all(close(a,b) for a,b in zip(mean,rgb)),'sample mean / native Film mismatch')
            return records,final

        try:
            reference,one=run('one',0,16,[28,36,28,36],1)
            variants=[('threads',[(0,16)],[[28,36,28,36]],2),
              ('forward',[(0,4),(4,8),(8,12),(12,16)],[[28,36,28,36]],1),
              ('reverse',[(12,16),(8,12),(4,8),(0,4)],[[28,36,28,36]],2),
              ('tiles',[(12,16),(8,12),(4,8),(0,4)],[[28,32,28,32],[32,36,28,32],[28,32,32,36],[32,36,32,36]],2)]
            for label,batches,regions,threads in variants:
                all_records={}
                sums={pixel:[0.,0.,0.] for pixel in one}
                counts=Counter()
                for begin,end in batches:
                    for tile,region in enumerate(regions):
                        values,film=run(f'{label}-{begin}-{tile}',begin,end,region,threads)
                        require(not set(all_records).intersection(values),'batch overlap')
                        all_records.update(values)
                        for pixel,rgb in film.items():
                            counts[pixel]+=end-begin
                            for c in range(3):
                                sums[pixel][c]+=(end-begin)*rgb[c]
                require(reference==all_records,'sample values/accounting changed under batching')
                require(all(counts[p]==16 and all(close(sums[p][c]/16,one[p][c]) for c in range(3)) for p in one),'progressive estimator mismatch')
            if scene_id=='empty-environment':
                require(all(v[3:]==(1,1,0,1,1,0,0) for v in reference.values()),'analytic one-camera case')
            if scene_id in ('diffuse-sphere','specular-sphere','dielectric'):
                require(any(v[8]>0 for v in reference.values()),'continuation not exercised')
            if scene_id in ('area','pointlit-sphere'):
                require(any(v[9]>0 for v in reference.values()),'visibility not exercised')
            if scene_id=='roulette':
                require(any(v[8]>v[4]-v[3] for v in reference.values()),'discarded roulette continuation not exercised')
            results[scene_id]={'status':'PASS','samples':len(reference)}
        except (ValueError,OSError,subprocess.SubprocessError) as error:
            results[scene_id]={'status':'FAIL','reason':str(error)}
            failures.append(scene_id)
    return dict(status='FAIL' if failures else 'PASS',fixtures=results,failed_fixtures=failures,
                comparative_outcomes='None generated',preregistration='7f610be4eb137aae85c3fe97721a2a3ae5366ca3',
                source_audit_required=True,selection='not selected until independent source audit and both contracts complete')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--pbrt',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    report=evaluate(args.pbrt.resolve(),args.output)
    report['binary_sha256']=hashlib.sha256(args.pbrt.read_bytes()).hexdigest()
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if report['status']!='PASS':
        raise SystemExit(1)
