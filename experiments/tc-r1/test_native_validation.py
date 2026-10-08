"""Independent offline regressions; never fetch/build/render PBRT."""
from dataclasses import replace
from pathlib import Path
import subprocess
import tempfile
import unittest

from native_validation import (compare_samples, complete_prefix, execution_guard,
                               full_film, verify_contract)
from progressive_kernel import NativeSample, Region


class NativeValidationTests(unittest.TestCase):
    def test_frozen_non_primary_contract_bindings(self):
        value=verify_contract()
        self.assertEqual(len(value['fixtures']),4)
        self.assertFalse(value['amendment_adopted'])
        self.assertFalse(value['comparative_execution_authorized'])

    def test_all_film_rows_not_only_terminal_estimator(self):
        samples=[NativeSample(0,0,i,(v,v,v),1,1,0,1,0,0) for i,v in enumerate((2.,4.,6.))]
        with tempfile.TemporaryDirectory() as folder:
            prefix=Path(folder)/'fixture'
            film=prefix.with_suffix('.film.csv')
            original='0,0,0,2,2,2\n0,0,1,3,3,3\n0,0,2,4,4,4\n'
            film.write_text(original)
            self.assertEqual(full_film(prefix,samples,Region(0,1,0,1),0,3),{(0,0):(4.,4.,4.)})
            for data in (original.replace('1,3,3,3','1,9,9,9'),original.split('\n',1)[1],
                         original+'0,0,0,2,2,2\n','0,0\n'+original):
                film.write_text(data)
                with self.assertRaises(ValueError): full_film(prefix,samples,Region(0,1,0,1),0,3)

    def test_identity_class_and_stream_comparisons_are_separate(self):
        sample=NativeSample(0,0,0,(2.,3.,4.),1,2,0,1,1,0)
        compare_samples([sample],[sample])
        for actual in ([sample,sample],[replace(sample,index=1)],
                       [replace(sample,continuation=2)],[replace(sample,rgb=(3.,3.,4.))]):
            with self.assertRaises(ValueError): compare_samples([sample],actual)
        self.assertEqual(complete_prefix([sample]),{(0,0):1})
        with self.assertRaises(ValueError): complete_prefix([sample,sample])
        with self.assertRaises(ValueError): complete_prefix([replace(sample,index=1)])

    def test_real_git_history_first_introduction_and_marker_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            def git(*args):
                return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.STDOUT)
            git('init','--quiet')
            git('config','user.name','Native validation test')
            git('config','user.email','native-validation@example.invalid')
            git('commit','--allow-empty','-m','base','--quiet')
            marker=root/'research/tc-r1/native-validation/execute-validation.json'
            marker.parent.mkdir(parents=True)
            marker.write_text('{}\n')
            git('add','.')
            git('commit','-m','first marker','--quiet')
            execution_guard(root,'1')
            for attempt in ('2','',None):
                with self.assertRaises(ValueError): execution_guard(root,attempt)
            git('commit','--allow-empty','-m','marker remains in parent','--quiet')
            with self.assertRaises(ValueError): execution_guard(root,'1')
            marker.unlink()
            git('add','.')
            git('commit','-m','delete marker','--quiet')
            marker.write_text('{}\n')
            git('add','.')
            git('commit','-m','re-add marker','--quiet')
            with self.assertRaises(ValueError): execution_guard(root,'1')


if __name__ == '__main__':
    unittest.main()
