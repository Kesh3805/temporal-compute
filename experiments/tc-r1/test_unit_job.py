"""Retention and attainment logic of the unit job against the scripted fake worker."""
import gzip
import io
import json
import threading
import unittest

import test_persistent_backend as fake
import unit_job
from progressive_kernel import Region


class RetainingBackendTests(fake.PersistentBackendTests):
    def retaining(self, records, policy='tc-full', stream='allocation'):
        class Fake(unit_job.RetainingBackend):
            def _command(inner):
                return [fake.sys.executable, str(self.fake)]
        audit = self.root/'audit'
        audit.mkdir(exist_ok=True)
        return Fake(self.fake, self.manifest, self.scene, self.scene_hash, ('worker-test', 'f0', 0, stream),
                    self.root/f'out-{policy}-{stream}', admitted_scenes={self.scene_hash}, timeout=20,
                    unit='u', policy=policy, stream=stream, records=records, audit_directory=audit)

    def test_logs_hashed_then_deleted_except_audit(self):
        buffer = io.BytesIO()
        records = gzip.open(buffer, 'wt', encoding='utf-8')
        backend = self.retaining(records)
        for i in range(40):
            backend.render(Region(0, 2, 0, 2), 4*i, 4*i+4)
        backend.close()
        records.close()
        lines = [json.loads(l) for l in gzip.decompress(buffer.getvalue()).decode().splitlines()]
        self.assertEqual([l['dispatch'] for l in lines], list(range(40)))
        self.assertTrue(all(set(l['log_sha256']) == {'.samples.csv', '.events.csv', '.film.csv'} for l in lines))
        self.assertEqual(list((self.root/'out-tc-full-allocation').iterdir()), [])
        expected = {i for i in range(40) if unit_job.audited('u', 'tc-full', 'allocation', i)}
        self.assertEqual({l['dispatch'] for l in lines if l['audit_retained']}, expected)
        self.assertEqual(len(list((self.root/'audit').iterdir())), 3*len(expected))

    def test_concurrent_streams_write_whole_lines(self):
        buffer = io.BytesIO()
        records = gzip.open(buffer, 'wt', encoding='utf-8')
        backends = [self.retaining(records, stream=s) for s in ('allocation', 'production')]

        def work(backend):
            for i in range(30):
                backend.render(Region(0, 2, 0, 2), 4*i, 4*i+4)
        threads = [threading.Thread(target=work, args=(b,)) for b in backends]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        for b in backends:
            b.close()
        records.close()
        lines = [json.loads(l) for l in gzip.decompress(buffer.getvalue()).decode().splitlines()]
        self.assertEqual(sorted((l['stream'], l['dispatch']) for l in lines),
                         sorted((s, i) for s in ('allocation', 'production') for i in range(30)))

    def test_audit_selection_is_about_one_in_1024(self):
        hits = sum(unit_job.audited('scene|f0|0', 'uniform', 'production', i) for i in range(200000))
        self.assertTrue(120 < hits < 280)


class AttainmentTests(unittest.TestCase):
    def test_first_and_sustained_within_cap(self):
        scores = [dict(seconds=s, joint=j) for s, j in ((10, False), (20, True), (30, False), (40, True), (50, True),
                                                       (70, False))]
        self.assertEqual(unit_job.attainment(scores, 60),
                         dict(first_seconds=20, sustained_seconds=40, follow_up_seconds=50))
        self.assertEqual(unit_job.attainment(scores[:1], 60)['first_seconds'], None)


del fake.PersistentBackendTests

if __name__ == '__main__':
    unittest.main()
