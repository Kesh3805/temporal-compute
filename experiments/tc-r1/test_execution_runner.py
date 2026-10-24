"""Execution runner rules on a deterministic numeric backend (no PBRT, no policy comparison)."""
import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from execution_runner import AUDIT_PERIOD, POLICIES, PolicyRun
from progressive_kernel import NativeSample


def unit(*key):
    return struct.unpack('>Q', hashlib.sha256(repr(key).encode()).digest()[:8])[0]/2**64


class StreamBackend:
    """Distinct deterministic values per stream; per-sample rays 1..8; optional failure on a call."""
    def __init__(self, stream, fail_on=None):
        self.stream, self.calls, self.fail_on = stream, 0, fail_on

    def render(self, region, begin, end):
        self.calls += 1
        if self.fail_on == self.calls:
            raise RuntimeError('injected failure')
        out = []
        for x, y in region.pixels():
            bright = 3.0 if (x//16 + y//16) % 2 else 0.3
            for i in range(begin, end):
                v = bright*(0.2 + unit(self.stream, x, y, i))
                rays = 1 + int(unit('rays', x, y, i)*(8 if x < 16 else 2))
                out.append(NativeSample(x, y, i, (v, 0.8*v, 0.6*v), 1, rays, 0, 1, rays-1, 0))
        return out


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_policy(self, name, tag, cap=0.05, fail_on=None):
        sunk = []

        def sink(policy, index, image):
            sunk.append((index, hashlib.sha256(repr(image).encode()).hexdigest()))
            return sunk[-1][1]
        runner = PolicyRun(32, 32, lambda stream: StreamBackend(stream, fail_on if stream == 'production' else None),
                           cap, sink, self.root/f'{tag}-{name}.jsonl', increments=(8192, 32768), snapshot_rays=8192)
        return runner.run(name), sunk

    def test_registered_rules_for_every_policy(self):
        inits = set()
        for name in POLICIES:
            record, sunk = self.run_policy(name, 'a')
            self.assertEqual(record['status'], 'complete')
            inits.add(record['initialization'])
            a = record['initialization']
            self.assertEqual([c['nominal'] for c in record['checkpoints']], [a+8192, a+32768])
            self.assertTrue(all(0 <= c['overshoot'] < 2*1024*8 for c in record['checkpoints']))
            self.assertEqual([s['index'] for s in record['snapshots']], list(range(1, len(record['snapshots'])+1)))
            self.assertGreaterEqual(len(record['snapshots']), 4)
            self.assertGreaterEqual(record['seconds'], 0.05)
            lines = (self.root/f'a-{name}.jsonl').read_text().splitlines()
            self.assertEqual(len(lines), record['requests'])
            self.assertIn('candidates', json.loads(lines[0]))
            self.assertTrue(all(('candidates' in json.loads(l)) == (i % AUDIT_PERIOD == 0) for i, l in enumerate(lines)))
        self.assertEqual(len(inits), 1, 'initialization charge must be policy independent')

    def test_repeat_runs_are_deterministic_in_rays(self):
        for name in ('variance-guided', 'tc-full'):
            first, sunk1 = self.run_policy(name, 'r1', cap=0.01)
            second, sunk2 = self.run_policy(name, 'r2', cap=0.01)
            self.assertEqual([c['actual'] for c in first['checkpoints']], [c['actual'] for c in second['checkpoints']])
            n = min(len(sunk1), len(sunk2))
            self.assertEqual(sunk1[:n], sunk2[:n])

    def test_cost_aware_controller_uses_ray_cost(self):
        _, _ = self.run_policy('tc-full', 'c', cap=0.01)
        lines = [json.loads(l) for l in (self.root/'c-tc-full.jsonl').read_text().splitlines()]
        self.assertTrue(any(l['reason'] == 'marginal-score' for l in lines))

    def test_backend_failure_propagates(self):
        with self.assertRaises(RuntimeError):
            self.run_policy('uniform', 'f', fail_on=5)


if __name__ == '__main__':
    unittest.main()
