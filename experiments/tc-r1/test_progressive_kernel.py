"""Synthetic numeric and retained native-artifact tests; never render."""
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import math
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from progressive_kernel import (Moments, NativeSample, ProgressiveKernel, Region,
                                WorkRequest, pbrt_seed_map, stream_seed)
from pbrt_batch_backend import PbrtBatchBackend, load_batch


class SyntheticBackend:
    def __init__(self):
        self.calls=[]

    def render(self, region, begin, end):
        self.calls.append((region,begin,end))
        return [NativeSample(x,y,i,(float(i+x),float(i+y),2.),1,2,1,1,2,1)
                for x,y in region.pixels() for i in range(begin,end)]


def kernel(width=2,height=2,regions=None,backend=None):
    ticks=iter(range(0,100000000000,1000000))
    return ProgressiveKernel(width,height,backend or SyntheticBackend(),regions,lambda:next(ticks))


class ProgressiveKernelTests(unittest.TestCase):
    def test_moments_known_answers(self):
        m=Moments()
        for v in (1.,2.,3.,4.):
            m.add((v,2*v,0.))
        self.assertEqual(m.count,4)
        self.assertEqual(m.mean,(2.5,5.,0.))
        self.assertEqual(m.m2,(5.,20.,0.))

    def test_state_units_and_no_observation_work(self):
        backend=SyntheticBackend()
        k=kernel(backend=backend)
        self.assertIsNone(k.observe()[0].mean)
        self.assertIsNone(k.observe()[0].standard_error)
        self.assertEqual(backend.calls,[])
        state=k.sample_region(WorkRequest(k.regions[0],1))
        self.assertIsNone(state.variance)
        state=k.sample_region(WorkRequest(k.regions[0],3))
        self.assertEqual(state.sample_count,16)
        self.assertEqual(state.mean,(2.,2.,2.))
        self.assertAlmostEqual(state.variance[0],5/3)
        self.assertAlmostEqual(state.standard_error[0],math.sqrt(5/12)/2)
        self.assertEqual(state.charged_rays,64)
        self.assertGreater(state.estimated_sample_cost,0)
        with self.assertRaises(FrozenInstanceError):
            state.charged_rays=0
        k.sample_region(WorkRequest(k.regions[0],4))
        self.assertIsNotNone(k.observe()[0].recent_improvement)

    def test_batches_and_tile_order_preserve_image(self):
        whole=kernel()
        whole.sample_region(WorkRequest(whole.regions[0],16))
        tiled=kernel(regions=(Region(0,1,0,2),Region(1,2,0,2)))
        for _ in range(4):
            for region in reversed(tiled.regions):
                tiled.sample_region(WorkRequest(region,4))
        self.assertEqual(whole.image(),tiled.image())
        self.assertEqual(sum(s.charged_rays for s in whole.observe()),sum(s.charged_rays for s in tiled.observe()))

    def test_invalid_partition_and_requests_do_no_work(self):
        for regions in ((),(Region(0,1,0,2),),(Region(0,2,0,2),Region(0,1,0,1)),(Region(-1,2,0,2),)):
            with self.assertRaises(ValueError):
                kernel(regions=regions)
        backend=SyntheticBackend()
        k=kernel(backend=backend)
        for request in (WorkRequest(k.regions[0],0),WorkRequest(k.regions[0],17),WorkRequest(k.regions[0],True),WorkRequest(Region(0,1,0,1),1)):
            with self.assertRaises(ValueError):
                k.sample_region(request)
        self.assertEqual(backend.calls,[])

    def test_bad_sample_retains_failure_and_blocks_retry(self):
        for change in ('duplicate','missing','negative','nan','queries'):
            backend=SyntheticBackend()
            native=backend.render(Region(0,2,0,2),0,2)
            if change=='duplicate': native.append(native[0])
            if change=='missing': native.pop()
            if change=='negative': native[0]=replace(native[0],continuation=-1)
            if change=='nan': native[0]=replace(native[0],rgb=(float('nan'),0.,0.))
            if change=='queries': native[0]=replace(native[0],regular_queries=100)
            with self.subTest(change=change),patch.object(backend,'render',return_value=native):
                k=kernel(backend=backend)
                with self.assertRaises(ValueError): k.sample_region(WorkRequest(k.regions[0],2))
                self.assertEqual(k.observe()[0].sample_count,0)
                self.assertFalse(k.work_known)
                self.assertEqual(k.trace[-1]['status'],'failed')
                with self.assertRaises(ValueError): k.sample_region(WorkRequest(k.regions[0],2))
                with self.assertRaises(ValueError): k.image()

    def test_stop_has_no_work_and_final_image_coverage(self):
        backend=SyntheticBackend()
        k=kernel(backend=backend)
        with self.assertRaises(ValueError): k.image()
        k.sample_region(WorkRequest(k.regions[0],2))
        calls=len(backend.calls)
        a=k.observe()
        self.assertEqual(k.stop('common budget'),a)
        self.assertEqual(len(backend.calls),calls)
        with self.assertRaises(ValueError): k.sample_region(WorkRequest(k.regions[0],1))

    def test_failed_measurement_never_exposes_partial_commit(self):
        k=kernel()
        k._clock=lambda:0
        with self.assertRaises(ValueError): k.sample_region(WorkRequest(k.regions[0],2))
        self.assertEqual(k.observe()[0].sample_count,0)
        self.assertEqual(k.observe()[0].version,0)
        self.assertFalse(k.work_known)

    def test_interruption_rolls_back_and_invalidates_work(self):
        for stage in ('render','clock','final_observation'):
            with self.subTest(stage=stage):
                backend=SyntheticBackend()
                k=kernel(backend=backend)
                k.sample_region(WorkRequest(k.regions[0],2))
                before=k.observe()
                if stage=='render':
                    guard=patch.object(backend,'render',side_effect=KeyboardInterrupt)
                elif stage=='clock':
                    guard=patch.object(k,'_clock',side_effect=[0,KeyboardInterrupt()])
                else:
                    observe=k.observe
                    calls=0
                    def interrupt_after_trace():
                        nonlocal calls
                        calls+=1
                        if calls==3:
                            raise KeyboardInterrupt
                        return observe()
                    guard=patch.object(k,'observe',side_effect=interrupt_after_trace)
                with guard,self.assertRaises(KeyboardInterrupt):
                    k.sample_region(WorkRequest(k.regions[0],2))
                self.assertEqual(k.observe(),before)
                self.assertFalse(k.work_known)
                self.assertEqual([r['status'] for r in k.trace],['committed','failed'])
                self.assertEqual(k.trace[-1]['error_type'],'KeyboardInterrupt')
                calls=len(backend.calls)
                with self.assertRaises(ValueError): k.sample_region(WorkRequest(k.regions[0],1))
                with self.assertRaises(ValueError): k.image()
                self.assertEqual(len(backend.calls),calls)

    def test_native_interruption_retains_failure_and_blocks_reuse(self):
        qualified=Path(__file__).resolve().parents[2]/'research/tc-r1/e3/build-manifest.json'
        manifest=json.loads(qualified.read_text())
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            binary=root/'mock-binary'
            scene=root/'mock-scene'
            binary.write_bytes(b'synthetic executable identity; never executed')
            scene.write_bytes(b'synthetic admitted fixture identity')
            manifest['binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
            build=root/'build.json'
            build.write_text(json.dumps(manifest))
            scene_hash=hashlib.sha256(scene.read_bytes()).hexdigest()
            backend=PbrtBatchBackend(binary,build,scene,scene_hash,
                                     ('diffuse-01','f0',0,'production'),root/'evidence',
                                     admitted_scenes={scene_hash})
            with patch('pbrt_batch_backend.subprocess.run',side_effect=KeyboardInterrupt) as dispatch:
                with self.assertRaises(KeyboardInterrupt): backend.render(Region(0,1,0,1),0,1)
                record=json.loads((root/'evidence/batch-00000000.json').read_text())
                self.assertEqual(record['status'],'failed')
                self.assertFalse(record['work_known'])
                self.assertEqual(record['error_type'],'KeyboardInterrupt')
                with self.assertRaises(ValueError): backend.render(Region(0,1,0,1),0,1)
                self.assertEqual(dispatch.call_count,1)

    def test_stream_derivation_and_collision_fail_closed(self):
        identity=('diffuse-01','f0',0,'production')
        expected=int.from_bytes(hashlib.sha256(b'tc-r1-v1|20261007|diffuse-01|f0|0|production').digest()[:8],'big')
        self.assertEqual(stream_seed(*identity),expected)
        self.assertNotEqual(stream_seed(*identity),stream_seed(*identity[:3],'allocation'))
        with self.assertRaises(ValueError): pbrt_seed_map([identity,identity])
        with patch('progressive_kernel.stream_seed',side_effect=[1,1+(1<<31)]):
            with self.assertRaises(ValueError): pbrt_seed_map([identity,identity[:3]+('allocation',)])

    def test_full_planned_identity_pool_has_unique_native_seeds(self):
        identities=[(f'{family}-{variant:02d}',f'f{frame}',replicate,stream)
                    for family in ('uniform','specular','diffuse','motion','adaptive')
                    for variant in (1,2) for frame in range(3) for replicate in range(8)
                    for stream in ('allocation','production','reference-a','reference-b','timing-order')]
        seeds=pbrt_seed_map(identities)
        self.assertEqual(len(seeds),1200)
        self.assertEqual(len({value[1] for value in seeds.values()}),1200)

    def test_retained_native_batches_validate_without_render(self):
        root=Path(__file__).resolve().parents[2]/'research/tc-r1/e3'
        hashes=json.loads((root/'artifact-hashes.json').read_text())['files']
        with tempfile.TemporaryDirectory() as folder,tarfile.open(root/'raw-artifacts.tar.gz') as archive:
            out=Path(folder)
            for kind in ('dielectric','trianglemesh'):
                prefix=out/(kind+'-one')
                for suffix in ('.samples.csv','.film.csv','.events.csv'):
                    name=prefix.name+suffix
                    data=archive.extractfile(name).read()
                    self.assertEqual(hashlib.sha256(data).hexdigest(),hashes[name])
                    prefix.with_suffix(suffix).write_bytes(data)
                samples=load_batch(prefix,Region(28,36,28,36),0,16)
                self.assertEqual(len(samples),1024)
                ledger=prefix.with_suffix('.events.csv')
                ledger.write_text(ledger.read_text()+'28,28,0,camera\n')
                with self.assertRaises(ValueError): load_batch(prefix,Region(28,36,28,36),0,16)

    def test_native_log_shapes_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            prefix=Path(folder)/'batch'
            prefix.with_suffix('.samples.csv').write_text('0,0,0,1,1,1,1,1,0,1,1,0,0\n')
            prefix.with_suffix('.events.csv').write_text('0,0,0,camera\n')
            prefix.with_suffix('.film.csv').write_text('0,0,0,1,1,1\n')
            self.assertEqual(len(load_batch(prefix,Region(0,1,0,1),0,1)),1)
            for suffix in ('.samples.csv','.events.csv','.film.csv'):
                path=prefix.with_suffix(suffix)
                original=path.read_text()
                path.write_text('0,0\n')
                with self.assertRaises(ValueError): load_batch(prefix,Region(0,1,0,1),0,1)
                path.write_text(original)


if __name__=='__main__':
    unittest.main()
