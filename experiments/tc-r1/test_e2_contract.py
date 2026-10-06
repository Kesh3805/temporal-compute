"""Numerical boundary tests do not render or access the registered corpus."""
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from e2_contract import EXTRA, SCENES, close, evaluate, require


class E2ContractTests(unittest.TestCase):
    def test_short_film_row_is_retained_and_evaluation_continues(self):
        def fake_render(command,env,**kwargs):
            begin,end=int(env['TC_R1E_SAMPLE_BEGIN']),int(env['TC_R1E_SAMPLE_END'])
            bounds=list(map(int,command[command.index('--pixelbounds')+1].split(',')))
            samples=[]
            events=[]
            for x in range(bounds[0],bounds[1]):
                for y in range(bounds[2],bounds[3]):
                    for i in range(begin,end):
                        samples.append(f'{x},{y},{i},1,1,1,1,1,0,1,1,0,0')
                        events.append(f'{x},{y},{i},camera')
            Path(env['TC_R1E_SAMPLE_LOG']).write_text('\n'.join(samples)+'\n')
            Path(env['TC_R1E2_EVENTS']).write_text('\n'.join(events)+'\n')
            Path(env['TC_R1E2_FILM']).write_text('28,28\n')
            return subprocess.CompletedProcess(command,0,'','')

        with tempfile.TemporaryDirectory() as folder, patch('e2_contract.subprocess.run',side_effect=fake_render) as renderer:
            report=evaluate(Path('unused-renderer'),Path(folder))
        expected=set(SCENES)|set(EXTRA)
        self.assertEqual(set(report['fixtures']),expected)
        self.assertEqual(set(report['failed_fixtures']),expected)
        self.assertEqual(renderer.call_count,len(expected))
        self.assertEqual(report['status'],'FAIL')
        for result in report['fixtures'].values():
            self.assertEqual(result,{'status':'FAIL','reason':'Film record shape'})

    def test_predeclared_channel_tolerance(self):
        self.assertTrue(close(0.,.0000009))
        self.assertFalse(close(0.,.000002))
        self.assertTrue(close(10.,10.00009))
        self.assertFalse(close(10.,10.001))

    def test_nonfinite_rejected(self):
        for value in (math.nan,math.inf,-math.inf):
            self.assertFalse(close(value,value))

    def test_failure_is_active_under_optimization(self):
        with self.assertRaises(ValueError):
            require(False,'contract failed')


if __name__=='__main__':
    unittest.main()
