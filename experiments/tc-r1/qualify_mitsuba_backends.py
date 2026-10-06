"""Backend-specific synthetic throughput only; no policy comparison."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import statistics
import time

import drjit as dr
import mitsuba as mi

SOURCE = '478e193a183c21723f4a8251afc3ad29a8da4c5e'  # dereferenced upstream v3.9.1
REFERENCE_CAMERA_SAMPLES = 10 * 3 * 2 * 256 * 256 * 8192


def scene(kind):
    value={'type':'scene','integrator':{'type':'path','max_depth':8},
        'sensor':{'type':'perspective','fov':45,
          'to_world':mi.ScalarTransform4f.look_at(origin=[0,0,-4],target=[0,0,0],up=[0,1,0]),
          'film':{'type':'hdrfilm','width':64,'height':64,'rfilter':{'type':'box'}},
          'sampler':{'type':'independent','sample_count':4096}},
        'environment':{'type':'constant','radiance':{'type':'rgb','value':1 if kind!='pointlit' else .005}}}
    if kind!='empty':
        value['object']={'type':'sphere','bsdf':{'type':'conductor','material':'Al'} if kind=='specular'
            else {'type':'diffuse','reflectance':{'type':'rgb','value':[.4,.6,.3]}}}
    if kind=='pointlit':
        value['point']={'type':'point','position':[0,2,-2],'intensity':{'type':'rgb','value':60}}
    return mi.load_dict(value)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant',required=True,choices=['scalar_rgb','llvm_ad_rgb','cuda_ad_rgb'])
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=dict(renderer='Mitsuba',package_version=mi.__version__,upstream_release_commit=SOURCE,
        binary_provenance='pip release wheel; upstream release mapping, not independently rebuilt source',
        variant=args.variant,platform=platform.platform(),drjit_version=importlib.metadata.version('drjit'),
        license='BSD-3-Clause',fixtures={},complete_ray_accounting=False,
        accounting_limitation='native path integrator has no exposed complete per-action ray counter',
        scope='unrelated 64x64 synthetic infrastructure; no registered assets or policies')
    init=time.perf_counter()
    try:
        mi.set_variant(args.variant)
    except ImportError as error:
        report.update(status='UNAVAILABLE',reason=str(error))
    else:
        report.update(status='PASS WITH LIMITATION',initialization_seconds=time.perf_counter()-init)
        for kind in ('empty','diffuse','specular','pointlit'):
            start=time.perf_counter()
            s=scene(kind)
            load=time.perf_counter()-start
            timings=[]
            for repeat in range(4):
                if args.variant!='scalar_rgb':
                    dr.sync_thread()
                start=time.perf_counter()
                output=mi.render(s,seed=19,spp=4096)
                dr.eval(output)
                if args.variant!='scalar_rgb':
                    dr.sync_thread()
                timings.append(time.perf_counter()-start)
            cps=16777216/statistics.median(timings[1:])
            report['fixtures'][kind]=dict(load_seconds=load,cold_wall_seconds=timings[0],
                warm_wall_seconds=timings[1:],camera_samples_per_render=16777216,
                camera_samples_per_second=cps,measured_rays_per_second=None,
                projected_256x256_8192spp_seconds=536870912/cps,
                projected_60_reference_frames_hours=REFERENCE_CAMERA_SAMPLES/cps/3600,
                reference_projection_definition='10 scenes x 3 frames x 2 independent streams x 256^2 pixels x 8192 spp',
                projection_not_corpus_measurement=True,
                timing='dr.eval plus dr.sync_thread before start/after stop for JIT; native scalar is synchronous')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
