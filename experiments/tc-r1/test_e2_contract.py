"""Numerical boundary tests do not render or access the registered corpus."""
import math
import unittest

from e2_contract import close, require


class E2ContractTests(unittest.TestCase):
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
