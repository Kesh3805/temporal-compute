"""Shard rendering and combination against the scripted fake worker (no PBRT)."""
import json
import unittest

import numpy as np

import reference_shards as rs
import test_persistent_backend as fake


class ShardTests(fake.PersistentBackendTests):
    def setUp(self):
        super().setUp()
        self.scene.write_text('Film "rgb" "integer xresolution" [6] "integer yresolution" [4]\n')
        import hashlib
        self.scene_hash = hashlib.sha256(self.scene.read_bytes()).hexdigest()
        self.patch = rs.PersistentPbrtBackend._command
        rs.PersistentPbrtBackend._command = lambda backend: [fake.sys.executable, str(self.fake)]

    def tearDown(self):
        rs.PersistentPbrtBackend._command = self.patch
        super().tearDown()

    def shard(self, begin, end, name):
        return rs.render_shard(self.fake, self.manifest, self.scene, self.scene_hash, ('s', 'f0', 0, 'reference-a'),
                               begin, end, 1, self.root/'shards'/name)

    def test_combined_shards_equal_one_shot(self):
        records = [self.shard(b, e, f'shard-{b}.npy') for b, e in rs.shard_ranges(64, 16)]
        combined = rs.combine(records, self.root/'shards', 64)
        whole = rs.combine([self.shard(0, 64, 'whole.npy')], self.root/'shards', 64)
        np.testing.assert_allclose(combined, whole, rtol=1e-6, atol=1e-7)
        self.assertEqual(combined.shape, (4, 6, 3))

    def test_gaps_mixed_identities_and_tampering_rejected(self):
        a, b, c = (self.shard(x, x+16, f'g-{x}.npy') for x in (0, 16, 32))
        with self.assertRaises(ValueError):
            rs.combine([a, c], self.root/'shards', 48)
        with self.assertRaises(ValueError):
            rs.combine([a, dict(b, identity=['s', 'f0', 0, 'reference-b'])], self.root/'shards', 32)
        (self.root/'shards'/'g-16.npy').write_bytes((self.root/'shards'/'g-0.npy').read_bytes())
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            rs.combine([a, b], self.root/'shards', 32)
        record = json.loads((self.root/'shards'/'g-0.json').read_text())
        self.assertEqual((record['begin'], record['end'], record['path']), (0, 16, 'g-0.npy'))

    def test_shard_ranges(self):
        self.assertEqual(rs.shard_ranges(65536), [(0, 32768), (32768, 65536)])
        with self.assertRaises(ValueError):
            rs.shard_ranges(40000)


del fake.PersistentBackendTests

if __name__ == '__main__':
    unittest.main()
