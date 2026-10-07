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
    def workflow_guard(self, folder, attempt='1'):
        workflow=Path(__file__).resolve().parents[2]/'.github/workflows/tc-r1e3-coverage.yml'
        source=workflow.read_text()
        guard=textwrap.dedent(source.split('      - name: Check first execution marker introduction\n        run: |\n',1)[1].split('      - name:',1)[0])
        bash=shutil.which('bash') if os.name!='nt' else str(Path(os.environ.get('ProgramFiles','C:/Program Files'))/'Git/bin/bash.exe')
        env=dict(os.environ)
        if attempt is None:
            env.pop('GITHUB_RUN_ATTEMPT',None)
        else:
            env['GITHUB_RUN_ATTEMPT']=attempt
        return subprocess.run([bash,'-e','-o','pipefail','-c',guard],cwd=folder,env=env,capture_output=True,text=True)

    def git(self, folder, *args):
        return subprocess.run(['git','-c','user.name=E3 guard test','-c','user.email=e3@example.invalid','-c','commit.gpgsign=false',*args],cwd=folder,check=True,capture_output=True,text=True).stdout.strip()

    def assert_guard(self, folder, expected, attempt='1'):
        result=self.workflow_guard(folder,attempt)
        self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        return result

    def marker(self, folder, present):
        path=Path(folder)/'research/tc-r1/e3/execute-once.json'
        if present:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('{}\n')
        else:
            path.unlink()
        self.git(folder,'add','--all')
        self.git(folder,'commit','-m','Add marker' if present else 'Delete marker')

    def test_workflow_rejects_reruns_before_marker_lookup(self):
        with tempfile.TemporaryDirectory() as folder:
            self.git(folder,'init','-b','main')
            self.git(folder,'commit','--allow-empty','-m','Base')
            self.marker(folder,True)
            self.assert_guard(folder,0)
            for attempt in ('2','3','',None):
                with self.subTest(attempt=attempt):
                    result=self.assert_guard(folder,1,attempt)
                    self.assertIn('Only the first workflow attempt',result.stdout)
            self.git(folder,'commit','--allow-empty','-m','Marker already present')
            self.assert_guard(folder,1)
            self.marker(folder,False)
            self.assert_guard(folder,1)
            self.marker(folder,True)
            self.assert_guard(folder,1)

    def test_workflow_checks_merged_prior_marker_history(self):
        with tempfile.TemporaryDirectory() as folder:
            self.git(folder,'init','-b','main')
            self.git(folder,'commit','--allow-empty','-m','Base')
            self.git(folder,'checkout','-b','old-marker')
            self.marker(folder,True)
            self.marker(folder,False)
            self.git(folder,'checkout','main')
            self.git(folder,'merge','--no-ff','old-marker','-m','Merge deleted marker history')
            # HEAD's first parent has no marker history; its second parent does.
            self.assert_guard(folder,1)
            self.marker(folder,True)
            self.assert_guard(folder,1)

    def test_workflow_rejects_unreadable_history(self):
        with tempfile.TemporaryDirectory() as folder:
            result=self.assert_guard(folder,1)
            self.assertIn('Cannot verify prior marker history',result.stdout)

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
