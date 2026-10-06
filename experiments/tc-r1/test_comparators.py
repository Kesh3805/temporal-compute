import unittest
from comparators import select_quality,select_time,restricted_mean


class Comparators(unittest.TestCase):
    def test_global_choice_does_not_stitch_case_winners(self):
        method,scores=select_quality({'adaptive':[1,100],'variance':[100,2],'uniform':[15,15]})
        self.assertEqual(method,'adaptive')
        self.assertEqual(len(scores),3)
        self.assertGreater(scores[method],0)  # a casewise [1,2] oracle is different

    def test_quality_and_time_select_independently(self):
        q,_=select_quality({'adaptive':[1,1],'variance':[2,2]})
        t,_=select_time({'adaptive':[(8.,True),(10.,False)],'variance':[(5.,True),(5.,True)]},10.)
        self.assertEqual((q,t),('adaptive','variance'))
        self.assertEqual(restricted_mean([(8.,True),(10.,False)],10.),9.)

    def test_ties_use_registration_order_not_dictionary_order(self):
        self.assertEqual(select_quality({'variance':[1],'uniform':[1]})[0],'uniform')
        self.assertEqual(select_time({'variance':[(1.,True)],'adaptive':[(1.,True)]},10.)[0],'adaptive')

    def test_missing_units_and_early_censoring_rejected(self):
        with self.assertRaises(ValueError):
            select_quality({'uniform':[1],'adaptive':[1,2]})
        with self.assertRaises(ValueError):
            restricted_mean([(2.,False)],10.)


if __name__=='__main__':
    unittest.main()
