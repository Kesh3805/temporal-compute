"""reference_set.build over fabricated convergence reports across escalation levels."""
import json
import tempfile
import unittest
from pathlib import Path

import reference_set

FRAMES = [(f'{family}-{v:02d}', f) for family in ('uniform', 'specular', 'diffuse', 'motion', 'adaptive')
          for v in (1, 2) for f in ('f0', 'f1', 'f2')]


def record(scene, frame, spp, decision):
    return dict(plan=dict(scene_id=scene, frame_id=frame, spp=spp), decision=decision,
                a=dict(sha256='a'*64), b=dict(sha256='b'*64), metrics={})


class ReferenceSetTests(unittest.TestCase):
    def write(self, root, spp, records):
        (Path(root)/f'convergence-{spp}.json').write_text(json.dumps(dict(spp=spp, records=records)))

    def test_escalation_and_halt(self):
        with tempfile.TemporaryDirectory() as root:
            first = [record(s, f, 8192, 'escalate' if s == 'specular-01' else 'converged') for s, f in FRAMES]
            self.write(root, 8192, first)
            self.write(root, 16384, [record('specular-01', f, 16384, 'converged' if f != 'f2' else 'escalate')
                                     for f in ('f0', 'f1', 'f2')])
            partial = reference_set.build(root)
            self.assertEqual((partial['complete'], partial['pending']), (False, ['specular-01/f2']))
            self.write(root, 32768, [record('specular-01', 'f2', 32768, 'halt')])
            done = reference_set.build(root)
            self.assertTrue(done['complete'])
            self.assertEqual(done['halted'], ['specular-01/f2'])
            self.assertEqual(done['converged']['specular-01/f0']['spp'], 16384)
            self.assertEqual(done['converged']['uniform-01/f0']['a'], 'uniform-01-f0-reference-a-8192.npy')

    def test_extended_levels_continue_a_registered_halt(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root, 8192, [record(s, f, 8192, 'converged' if s != 'specular-01' else 'escalate')
                                    for s, f in FRAMES])
            self.write(root, 16384, [record('specular-01', f, 16384, 'escalate') for f in ('f0', 'f1', 'f2')])
            self.write(root, 32768, [record('specular-01', f, 32768, 'halt') for f in ('f0', 'f1', 'f2')])
            self.assertEqual(reference_set.build(root)['halted'], ['specular-01/f0', 'specular-01/f1', 'specular-01/f2'])
            ext = [record('specular-01', f, 65536, 'converged' if f == 'f0' else 'escalate') for f in ('f0', 'f1', 'f2')]
            (Path(root)/'convergence-65536.json').write_text(json.dumps(dict(spp=65536, extended=True, records=ext)))
            value = reference_set.build(root)
            self.assertEqual((value['halted'], value['pending'], value['complete']),
                             ([], ['specular-01/f1', 'specular-01/f2'], False))
            self.assertEqual(value['converged']['specular-01/f0']['spp'], 65536)

    def test_work_after_terminal_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            self.write(root, 8192, [record('uniform-01', 'f0', 8192, 'converged')])
            self.write(root, 16384, [record('uniform-01', 'f0', 16384, 'converged')])
            with self.assertRaises(ValueError):
                reference_set.build(root)


if __name__ == '__main__':
    unittest.main()
