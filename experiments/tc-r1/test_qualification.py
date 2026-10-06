"""Renderer-independent qualification record checks; no renderer/API execution."""
from pathlib import Path
import tempfile
import unittest

from qualify_pbrt import fresh_log, load_records, require, state


class QualificationRecords(unittest.TestCase):
    def test_stale_sample_log_removed(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'samples.csv'
            path.write_text('old data')
            fresh_log(path)
            self.assertFalse(path.exists())
            fresh_log(path)

    def test_runtime_validation_cannot_be_disabled(self):
        with self.assertRaises(ValueError):
            require(False,'invalid qualification')

    def test_sample_moments_and_actual_ray_cost(self):
        rows={(2,3,0):(1.,2.,3.,1,2,1),(2,3,1):(3.,4.,5.,1,3,2)}
        value=state(rows)[0]
        self.assertEqual(value['count'],2)
        self.assertEqual(value['mean'],[2.,3.,4.])
        self.assertEqual(value['variance'],[2.,2.,2.])
        self.assertEqual(value['standard_error'],[1.,1.,1.])
        self.assertEqual(value['actual_trace_rays'],8)

    def test_duplicate_and_nonfinite_records_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'samples.csv'
            for text in ('0,0,0,1,1,1,1,1,0\n'*2,'0,0,0,nan,1,1,1,1,0\n'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    load_records(path)

    def test_single_sample_variance_is_unknown(self):
        self.assertEqual(state({(0,0,0):(1.,1.,1.,1,1,0)})[0]['variance'],[None]*3)


if __name__=='__main__':
    unittest.main()
