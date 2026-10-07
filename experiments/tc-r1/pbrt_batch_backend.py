"""Qualified native CPU batch bridge. No policy, references or renderer changes."""
from collections import Counter
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

from progressive_kernel import NativeSample, require, stream_seed

PIN='b4ce9687e6c695f5582997c61b0c66cf064bdb4a'


def close(a,b):
    return math.isfinite(a) and math.isfinite(b) and abs(a-b)<=1e-6+1e-5*max(abs(a),abs(b))


def load_batch(prefix, region, begin, end):
    records={}
    for row in csv.reader(prefix.with_suffix('.samples.csv').read_text().splitlines()):
        require(len(row)==13,'native sample record shape')
        x,y,index=map(int,row[:3])
        counts=tuple(map(int,row[6:]))
        sample=NativeSample(x,y,index,tuple(map(float,row[3:6])),
                            counts[0],counts[1],counts[2],counts[4],counts[5],counts[6])
        sample.validate()
        require(counts[3]==sample.charged_rays,'native total identity')
        key=(x,y,index)
        require(key not in records,'duplicate native sample')
        records[key]=sample
    expected={(x,y,i) for x,y in region.pixels() for i in range(begin,end)}
    require(set(records)==expected,'native sample identity domain')
    ledger=Counter()
    for row in csv.reader(prefix.with_suffix('.events.csv').read_text().splitlines()):
        require(len(row)==4,'native event record shape')
        key=tuple(map(int,row[:3]))
        require(key in records and row[3] in ('camera','continuation','visibility'),'unknown native event')
        ledger[key+(row[3],)]+=1
    for key,sample in records.items():
        require(all(ledger[key+(kind,)]==count for kind,count in
                    (('camera',sample.camera),('continuation',sample.continuation),('visibility',sample.visibility))),
                'native class ledger mismatch')
    film={}
    for row in csv.reader(prefix.with_suffix('.film.csv').read_text().splitlines()):
        require(len(row)==6,'native Film record shape')
        x,y,index=map(int,row[:3])
        rgb=tuple(map(float,row[3:]))
        require((x,y,index) in records and all(math.isfinite(v) for v in rgb),'invalid native Film identity/value')
        if index==end-1:
            require((x,y) not in film,'duplicate final Film pixel')
            film[(x,y)]=rgb
    require(set(film)==set(region.pixels()),'native Film pixel domain')
    for pixel,rgb in film.items():
        mean=tuple(math.fsum(records[pixel+(i,)].rgb[c] for i in range(begin,end))/(end-begin) for c in range(3))
        require(all(close(a,b) for a,b in zip(mean,rgb)),'native Film estimator mismatch')
    return tuple(records.values())


class PbrtBatchBackend:
    def __init__(self, binary, build_manifest, scene, scene_sha256, identity, output, threads=1,
                 admitted_scenes=None):
        self.binary=Path(binary).resolve()
        self.scene=Path(scene).resolve()
        self.output=Path(output).resolve()
        manifest=json.loads(Path(build_manifest).read_text())
        qualified=json.loads((Path(__file__).resolve().parents[2]/'research/tc-r1/e3/build-manifest.json').read_text())
        require(manifest['upstream_commit']==PIN,'wrong PBRT upstream')
        require(manifest['e3_source_sha256']==qualified['e3_source_sha256'],'unqualified instrumentation source')
        require(manifest['binary_sha256']==hashlib.sha256(self.binary.read_bytes()).hexdigest(),'binary provenance mismatch')
        require(hashlib.sha256(self.scene.read_bytes()).hexdigest()==scene_sha256,'scene provenance mismatch')
        # Integration supplies hashes from the strict Track D corpus verifier or
        # separately reviewed synthetic fixtures; an arbitrary file hash is insufficient.
        require(admitted_scenes is not None and scene_sha256 in admitted_scenes,
                'scene has no validated feature-envelope admission')
        require(type(threads) is int and threads>0,'invalid thread count')
        self.identity=tuple(identity)
        self.full_seed=stream_seed(*self.identity)
        self.seed=self.full_seed & 0x7fffffff
        self.threads=threads
        self._scene_sha256=scene_sha256
        self._binary_sha256=manifest['binary_sha256']
        self._calls=0
        self.output.mkdir(parents=True,exist_ok=True)

    def render(self, region, begin, end):
        # Detect changed inputs before every dispatch; never silently bind new bytes.
        require(hashlib.sha256(self.binary.read_bytes()).hexdigest()==self._binary_sha256,'binary changed')
        require(hashlib.sha256(self.scene.read_bytes()).hexdigest()==self._scene_sha256,'scene changed')
        prefix=self.output/f'batch-{self._calls:08d}'
        self._calls+=1
        paths={key:prefix.with_suffix(suffix) for key,suffix in
               (('TC_R1E_SAMPLE_LOG','.samples.csv'),('TC_R1E2_EVENTS','.events.csv'),('TC_R1E2_FILM','.film.csv'))}
        require(not any(prefix.with_suffix(s).exists() for s in ('.samples.csv','.events.csv','.film.csv','.exr','.log','.json')),
                'batch evidence already exists')
        env={k:v for k,v in os.environ.items() if not k.startswith('TC_R1E')}
        env.update({k:str(v) for k,v in paths.items()})
        env.update(TC_R1E_SAMPLE_BEGIN=str(begin),TC_R1E_SAMPLE_END=str(end))
        command=[str(self.binary),'--nthreads',str(self.threads),'--seed',str(self.seed),'--spp',str(end),
                 '--pixelbounds',f'{region.x0},{region.x1},{region.y0},{region.y1}',
                 '--outfile',str(prefix.with_suffix('.exr')),str(self.scene)]
        metadata=dict(identity=self.identity,full_seed=self.full_seed,pbrt_seed=self.seed,
                      begin=begin,end=end,binary_sha256=self._binary_sha256,scene_sha256=self._scene_sha256,
                      command=command,status='started')
        record=prefix.with_suffix('.json')
        record.write_text(json.dumps(metadata,indent=2)+'\n')
        try:
            proc=subprocess.run(command,env=env,capture_output=True,text=True,timeout=600)
            prefix.with_suffix('.log').write_text(proc.stdout+proc.stderr)
            require(proc.returncode==0,'native batch failed; retained diagnostics')
            samples=load_batch(prefix,region,begin,end)
            metadata.update(status='validated',camera_samples=len(samples),charged_rays=sum(s.charged_rays for s in samples))
            record.write_text(json.dumps(metadata,indent=2)+'\n')
            return samples
        except Exception as error:
            metadata.update(status='failed',work_known=False,error=str(error))
            record.write_text(json.dumps(metadata,indent=2)+'\n')
            raise
