"""E3 record validation only; no renderer execution."""
from pathlib import Path
import tempfile
import unittest

from e3_coverage import transmission_records


class E3CoverageTests(unittest.TestCase):
    def test_native_transmission_binds_existing_charge(self):
        samples={(1,2,3):(1.,1.,1.,1,3,0,3,1,2,0)}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'observations.csv'
            path.write_text('1,2,3,2\n')
            self.assertEqual(transmission_records(path,samples),{(1,2,3,2)})
            for text in ('1,2,3,3\n','1,2,4,1\n','1,2,3,2\n'*2,'1,2\n'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    transmission_records(path,samples)


if __name__=='__main__':
    unittest.main()
