"""Persistent worker protocol and containment against a scripted fake worker (no PBRT)."""
import hashlib
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from persistent_backend import WORKER_SOURCE_SHA256, PersistentPbrtBackend
from progressive_kernel import ProgressiveKernel, Region, WorkRequest

ROOT = Path(__file__).resolve().parents[2]

FAKE = textwrap.dedent('''
    import os, sys
    mode = os.environ.get('FAKE_MODE', 'normal')
    if mode.startswith('startfail'):
        marker = os.environ['FAKE_MARKER']
        launches = int(open(marker).read()) if os.path.exists(marker) else 0
        open(marker, 'w').write(str(launches + 1))
        if launches < int(mode[-1]):
            sys.stderr.write('simulated startup crash\\n')
            sys.exit(7)
    print('TCR1W READY', flush=True)
    count = 0
    for line in sys.stdin:
        count += 1
        if line.startswith('DUMP '):
            _, x0, x1, y0, y1, begin, end, path = line.split()
            x0, x1, y0, y1, begin, end = map(int, (x0, x1, y0, y1, begin, end))
            with open(path, 'w') as d:
                for y in range(y0, y1):
                    for x in range(x0, x1):
                        m = sum(((x*7 + y*13 + i*3) % 11)/10.0 for i in range(begin, end))/(end - begin)
                        d.write(f'{x},{y},{m:.9g},{m:.9g},{m:.9g}\\n')
            print(f'TCR1W DUMPED {x0} {x1} {y0} {y1} {begin} {end}', flush=True)
            continue
        x0, x1, y0, y1, begin, end, sp, ep, fp = line.split()
        x0, x1, y0, y1, begin, end = map(int, (x0, x1, y0, y1, begin, end))
        if mode == 'crash' and count == 2:
            sys.exit(3)
        if mode == 'hang' and count == 2:
            import time; time.sleep(30)
        with open(sp, 'w') as s, open(ep, 'w') as e, open(fp, 'w') as f:
            for y in range(y0, y1):
                for x in range(x0, x1):
                    total = 0.0
                    for i in range(begin, end):
                        v = ((x*7 + y*13 + i*3) % 11)/10.0
                        total += v
                        s.write(f'{x},{y},{i},{v!r},{v!r},{v!r},1,2,1,3,1,1,1\\n')
                        e.write(f'{x},{y},{i},camera\\n{x},{y},{i},continuation\\n{x},{y},{i},visibility\\n')
                        m = total/(i - begin + 1)
                        f.write(f'{x},{y},{i},{m!r},{m!r},{m!r}\\n')
        ack = 'TCR1W DONE 0 0 0 0 0 0' if mode == 'badack' and count == 2 else f'TCR1W DONE {x0} {x1} {y0} {y1} {begin} {end}'
        print('renderer chatter', flush=True)
        print(ack, flush=True)
''')


class FakeBackend(PersistentPbrtBackend):
    fake = None

    def _command(self):
        return [sys.executable, str(self.fake)]


class PersistentBackendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.fake = root/'fake_worker.py'
        self.fake.write_text(FAKE)
        FakeBackend.fake = self.fake
        self.scene = root/'scene.pbrt'
        self.scene.write_text('# synthetic\n')
        qualified = json.loads((ROOT/'research/tc-r1/e3/build-manifest.json').read_text())
        self.manifest = root/'manifest.json'
        self.manifest.write_text(json.dumps(dict(
            upstream_commit='b4ce9687e6c695f5582997c61b0c66cf064bdb4a',
            e3_source_sha256=qualified['e3_source_sha256'],
            binary_sha256=hashlib.sha256(self.fake.read_bytes()).hexdigest(),
            worker_source_sha256=WORKER_SOURCE_SHA256)))
        self.scene_hash = hashlib.sha256(self.scene.read_bytes()).hexdigest()
        self.root = root

    def tearDown(self):
        self.tmp.cleanup()

    def backend(self, name='out', timeout=20):
        return FakeBackend(self.fake, self.manifest, self.scene, self.scene_hash,
                           ('worker-test', 'f0', 0, 'allocation'), self.root/name,
                           admitted_scenes={self.scene_hash}, timeout=timeout)

    def test_requests_validate_through_qualified_load_batch_and_close_cleanly(self):
        backend = self.backend()
        kernel = ProgressiveKernel(8, 8, backend, (Region(0, 4, 0, 8), Region(4, 8, 0, 8)))
        for region in kernel.regions + kernel.regions:
            state = kernel.sample_region(WorkRequest(region, 4))
            self.assertEqual(state.charged_rays, state.sample_count*3)
        records = sorted((self.root/'out').glob('batch-*.json'))
        self.assertEqual(len(records), 4)
        self.assertTrue(all(json.loads(r.read_text())['status'] == 'validated' for r in records))
        backend.close()

    def test_worker_crash_is_unknown_work_and_not_retried(self):
        import os
        os.environ['FAKE_MODE'] = 'crash'
        try:
            backend = self.backend()
            backend.render(Region(0, 2, 0, 2), 0, 4)
            with self.assertRaises(RuntimeError):
                backend.render(Region(0, 2, 0, 2), 4, 8)
            record = json.loads((self.root/'out'/'batch-00000001.json').read_text())
            self.assertEqual((record['status'], record['work_known']), ('failed', False))
            with self.assertRaisesRegex(ValueError, 'cannot be retried'):
                backend.render(Region(0, 2, 0, 2), 4, 8)
        finally:
            del os.environ['FAKE_MODE']

    def test_wrong_acknowledgement_fails(self):
        import os
        os.environ['FAKE_MODE'] = 'badack'
        try:
            backend = self.backend()
            backend.render(Region(0, 2, 0, 2), 0, 4)
            with self.assertRaises(ValueError):
                backend.render(Region(0, 2, 0, 2), 4, 8)
            self.assertTrue(backend._failed)
        finally:
            del os.environ['FAKE_MODE']

    def test_timeout_fails_and_kills_worker(self):
        import os
        os.environ['FAKE_MODE'] = 'hang'
        try:
            backend = self.backend(timeout=2)
            backend.render(Region(0, 2, 0, 2), 0, 4)
            with self.assertRaisesRegex(RuntimeError, 'timed out'):
                backend.render(Region(0, 2, 0, 2), 4, 8)
            self.assertIsNotNone(backend._proc.poll())
        finally:
            del os.environ['FAKE_MODE']

    def test_unqualified_worker_manifest_rejected(self):
        value = json.loads(self.manifest.read_text())
        value['worker_source_sha256'] = '0'*64
        self.manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'unqualified worker'):
            self.backend()

    def test_startup_failures_are_recorded_and_bounded(self):
        import os
        os.environ['FAKE_MARKER'] = str(self.root/'launches')
        try:
            os.environ['FAKE_MODE'] = 'startfail2'
            backend = self.backend()
            self.assertEqual(len(backend.startup_failures), 2)
            self.assertIn('status 7', backend.startup_failures[0]['error'])
            self.assertIn('simulated startup crash', backend.startup_failures[0]['error'])
            backend.render(Region(0, 2, 0, 2), 0, 4)
            backend.close()
            (self.root/'launches').unlink()
            os.environ['FAKE_MODE'] = 'startfail3'
            with self.assertRaisesRegex(RuntimeError, 'status 7'):
                self.backend('out2')
        finally:
            del os.environ['FAKE_MODE'], os.environ['FAKE_MARKER']

    def test_dump_returns_exact_float32_region_film(self):
        import numpy as np
        backend = self.backend()
        image, digest = backend.dump(Region(1, 4, 2, 4), 0, 8)
        self.assertEqual(image.shape, (2, 3, 3))
        expected = sum(((3*7 + 3*13 + i*3) % 11)/10.0 for i in range(8))/8
        self.assertEqual(image[1, 2, 0], float(np.float32(float(f'{expected:.9g}'))))
        self.assertEqual(len(digest), 64)
        backend.render(Region(0, 2, 0, 2), 0, 4)   # logged requests still work after a dump
        backend.close()

    def test_scene_change_detected_at_close(self):
        backend = self.backend()
        backend.render(Region(0, 2, 0, 2), 0, 4)
        self.scene.write_text('# changed\n')
        with self.assertRaisesRegex(ValueError, 'scene changed'):
            backend.close()


if __name__ == '__main__':
    unittest.main()
