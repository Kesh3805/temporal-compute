"""Synthetic CPU path qualification only; no registered assets or policies."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import time

BASE = '''LookAt 0 0 -4 0 0 0 0 1 0
Camera "perspective" "float fov" [45]
Film "rgb" "integer xresolution" [64] "integer yresolution" [64]
Sampler "independent" "integer pixelsamples" [256]
Integrator "path" "integer maxdepth" [8]
PixelFilter "box"
WorldBegin
'''
SCENES = {
 'empty-environment': 'LightSource "infinite" "rgb L" [1 1 1]\n',
 'diffuse-sphere': 'LightSource "infinite" "rgb L" [1 1 1]\nMaterial "diffuse" "rgb reflectance" [.4 .6 .3]\nShape "sphere"\n',
 'specular-sphere': 'LightSource "infinite" "rgb L" [1 1 1]\nMaterial "conductor"\nShape "sphere"\n',
 'pointlit-sphere': 'LightSource "infinite" "rgb L" [.005 .005 .005]\nLightSource "point" "point3 from" [0 2 -2] "rgb I" [60 60 60]\nMaterial "diffuse" "rgb reflectance" [.6 .6 .6]\nShape "sphere"\n',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fresh_log(path):
    path.unlink(missing_ok=True)


def load_records(path):
    records={}
    for row in csv.reader(path.read_text().splitlines()):
        key=tuple(map(int,row[:3]))
        value=tuple(map(float,row[3:6]))+tuple(map(int,row[6:]))
        if key in records or len(row)!=9 or not all(math.isfinite(v) for v in value):
            raise ValueError('invalid or duplicate sample record')
        records[key]=value
    return records


def state(records):
    pixels={}
    for (x,y,index),value in sorted(records.items()):
        pixels.setdefault((x,y),[]).append(value)
    output=[]
    for (x,y),values in sorted(pixels.items()):
        n=len(values)
        mean=[math.fsum(v[c] for v in values)/n for c in range(3)]
        variance=[math.fsum((v[c]-mean[c])**2 for v in values)/(n-1) if n>1 else None for c in range(3)]
        output.append(dict(pixel=[x,y],count=n,mean=mean,variance=variance,
            standard_error=[math.sqrt(v/n) if v is not None else None for v in variance],
            actual_trace_rays=sum(v[4]+v[5] for v in values)))
    return output


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pbrt',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--build-manifest',type=Path)
    args=parser.parse_args()
    binary=args.pbrt.resolve()
    binary_hash=hashlib.sha256(binary.read_bytes()).hexdigest()
    manifest=json.loads(args.build_manifest.read_text()) if args.build_manifest else None
    if manifest and manifest['binary_sha256']!=binary_hash:
        raise ValueError('binary does not match build manifest')
    args.output.mkdir(parents=True,exist_ok=True)
    report=dict(scope='Unrelated synthetic fixtures only; zero TC-R1 comparisons',
        binary_sha256=binary_hash,build_provenance=manifest,platform=platform.platform(),
        renderer_selected=False,fixtures={})

    def run(scene,name,begin=None,end=None,bounds=None,threads=1):
        prefix=args.output/name
        log=prefix.with_suffix('.csv')
        if begin is not None:
            fresh_log(log)
        env={k:v for k,v in os.environ.items() if not k.startswith('TC_R1E_')}
        if begin is not None:
            env.update(TC_R1E_SAMPLE_BEGIN=str(begin),TC_R1E_SAMPLE_END=str(end),TC_R1E_SAMPLE_LOG=str(log.resolve()))
        command=[str(binary),'--stats','--nthreads',str(threads),'--seed','19',
                 '--outfile',str(prefix.with_suffix('.exr').resolve())]
        if bounds:
            command += ['--pixelbounds',','.join(map(str,bounds))]
        command.append(str(scene.resolve()))
        start=time.perf_counter()
        result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=180,check=False)
        wall=time.perf_counter()-start
        prefix.with_suffix('.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:
            raise RuntimeError(f'PBRT failed; retained {prefix.with_suffix(".txt")}')
        if begin is not None and not log.is_file():
            raise ValueError('renderer did not produce a new sample log')
        return (load_records(log) if begin is not None else None),wall,result.stdout+result.stderr

    for name,geometry in SCENES.items():
        scene=args.output/f'{name}.pbrt'
        scene.write_text(BASE+geometry,encoding='utf-8')
        full,_,_=run(scene,name+'-full',0,8,[28,36,28,36])
        first,_,_=run(scene,name+'-first',0,4,[28,36,28,36])
        second,_,_=run(scene,name+'-second',4,8,[28,36,28,36])
        threaded,_,_=run(scene,name+'-threads',0,8,[28,36,28,36],2)
        expected={(x,y,i) for x in range(28,36) for y in range(28,36) for i in range(8)}
        require(set(full)==expected and set(first).isdisjoint(second), 'missing or overlapping sample records')
        require(full=={**first,**second}==threaded, 'paired streams changed with batching/threads')
        require(all(v[3]==1 and v[4]>=v[3] and v[5]>=0 for v in full.values()), 'invalid ray accounting')
        camera=sum(v[3] for v in full.values())
        regular=sum(v[4] for v in full.values())
        shadow=sum(v[5] for v in full.values())
        if name=='empty-environment':
            require(regular==camera and shadow==0, 'analytic one-ray fixture failed')
        before,after=state(first),state(full)
        improvement=[sum(b['standard_error'])-sum(a['standard_error']) for b,a in zip(before,after)]
        elapsed=[]
        native_stats=[]
        for repeat in range(3):
            _,wall,stats=run(scene,f'{name}-throughput-{repeat}',threads=2)
            elapsed.append(wall)
            counters={}
            for label in ('Camera rays traced','Regular ray intersection tests','Shadow ray intersection tests'):
                match=re.search(re.escape(label)+r'\s+(\d[\d,]*)',stats)
                # PBRT omits zero-valued STAT_COUNTER entries entirely.
                if 'Statistics:' not in stats:
                    raise ValueError('native statistics missing')
                counters[label]=int(match.group(1).replace(',','')) if match else 0
            native_stats.append(counters)
        cps=1048576/statistics.median(elapsed)
        total=native_stats[1]['Regular ray intersection tests']
        shadows=native_stats[1]['Shadow ray intersection tests']
        ratio=(total+shadows)/1048576 if total is not None and shadows is not None else None
        report['fixtures'][name]=dict(scene_sha256=hashlib.sha256(scene.read_bytes()).hexdigest(),
            bounded_records=len(full),sample_level_replay_exact=True,threads_tested=[1,2],
            camera_rays=camera,continuation_rays=regular-camera,visibility_rays=shadow,
            probe_rays=0,total_traced_rays=regular+shadow,shared_state=after,
            regional_count=sum(p['count'] for p in after),recent_standard_error_change=improvement,
            throughput_wall_seconds=elapsed,throughput_camera_samples=1048576,
            camera_samples_per_second=cps,native_counters=native_stats,
            measured_rays_per_camera_sample=ratio,
            measured_trace_rays_per_second=(total+shadows)/elapsed[1] if ratio is not None else None,
            projected_256x256_8192spp_seconds=536870912/cps,
            projected_60_reference_frames_hours=32212254720/cps/3600,
            projection_not_measurement=True)
    report['qualification_scope']='CPU path/pinhole/opaque diffuse or conductor, no media/subsurface/null interfaces;64x64,maxdepth8'
    report['remaining']='Representative execution hardware/feasibility and correctness of any additional features before execution freeze'
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='fixtures'},indent=2))


if __name__=='__main__':
    main()
