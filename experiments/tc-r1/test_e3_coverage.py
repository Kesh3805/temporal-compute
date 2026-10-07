"""E3 record validation only; no renderer execution."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest

from e3_coverage import transmission_records


class E3CoverageTests(unittest.TestCase):
    def test_workflow_rejects_reruns_before_marker_lookup(self):
        workflow=Path(__file__).resolve().parents[2]/'.github/workflows/tc-r1e3-coverage.yml'
        source=workflow.read_text()
        guard=textwrap.dedent(source.split('      - name: Check first execution marker introduction\n        run: |\n',1)[1].split('      - name:',1)[0])
        bash=shutil.which('bash') if os.name!='nt' else str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Git/bin/bash.exe')
        # Stub only the parent-marker lookup; execute the actual workflow guard.
        stub='git() { echo MARKER_LOOKUP; return "$MARKER_PRESENT"; };\n'
        for attempt,marker,expected,lookup in (('1','1',0,True),('1','0',1,True),('2','1',1,False),('3','1',1,False),('','1',1,False)):
            with self.subTest(attempt=attempt,marker_present=marker=='0'):
                result=subprocess.run([bash,'-c',stub+guard],env={**os.environ,'GITHUB_RUN_ATTEMPT':attempt,'MARKER_PRESENT':marker},capture_output=True,text=True)
                self.assertEqual(result.returncode,expected,result.stderr)
                self.assertEqual('MARKER_LOOKUP' in result.stdout,lookup)

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
