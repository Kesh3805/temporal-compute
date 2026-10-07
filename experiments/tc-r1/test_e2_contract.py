"""Numerical boundary tests do not render or access the registered corpus."""
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from e2_contract import EXTRA, SCENES, close, evaluate, require


class E2ContractTests(unittest.TestCase):
    def evaluate_film_rows(self,film_rows):
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
            Path(env['TC_R1E2_FILM']).write_text(film_rows(bounds,end-1))
            return subprocess.CompletedProcess(command,0,'','')

        with tempfile.TemporaryDirectory() as folder, patch('e2_contract.subprocess.run',side_effect=fake_render) as renderer, patch('e2_contract.close',return_value=True) as compare:
            report=evaluate(Path('unused-renderer'),Path(folder))
        return report,renderer.call_count,compare.call_count

    def test_malformed_film_rows_are_retained_before_comparison(self):
        expected=set(SCENES)|set(EXTRA)
        for row in ('28,28\n','28,28,15\n','28,28,15,1,1,1,extra\n'):
            with self.subTest(row=row):
                report,renders,comparisons=self.evaluate_film_rows(lambda bounds,index:row)
                self.assertEqual(set(report['fixtures']),expected)
                self.assertEqual(set(report['failed_fixtures']),expected)
                self.assertEqual(renders,len(expected))
                self.assertEqual(comparisons,0)
                self.assertEqual(report['status'],'FAIL')
                for result in report['fixtures'].values():
                    self.assertEqual(result,{'status':'FAIL','reason':'Film record shape'})

    def test_complete_final_film_rows_reach_estimator_comparison(self):
        def film_rows(bounds,index):
            return ''.join(f'{x},{y},{index},1,1,1\n'
                for x in range(bounds[0],bounds[1]) for y in range(bounds[2],bounds[3]))
        report,renders,comparisons=self.evaluate_film_rows(film_rows)
        self.assertGreater(comparisons,0)
        self.assertEqual(report['fixtures']['empty-environment']['status'],'PASS')
        self.assertTrue(all(v.get('reason')!='Film record shape' for v in report['fixtures'].values()))

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
