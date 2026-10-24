"""Amendment 0005 section 2: medians with censoring only at the common cap."""
import itertools
import unittest

from analysis import median_observation

CAP = 100.0


class CommonCapMedianTests(unittest.TestCase):
    def test_every_attainment_pattern_is_exact_or_right_censored_at_cap(self):
        times = (10.0, 35.0, 80.0)
        for attained in itertools.product((True, False), repeat=3):
            repeats = [(t if hit else CAP, hit) for t, hit in zip(times, attained)]
            value, event = median_observation(repeats, CAP)
            hits = sorted(t for t, hit in zip(times, attained) if hit)
            with self.subTest(attained=attained):
                if len(hits) >= 2:
                    self.assertEqual((value, event), (hits[1], True))
                else:
                    # Never an attainment time; C is a censoring time only.
                    self.assertEqual((value, event), (CAP, False))

    def test_attainment_exactly_at_cap_stays_an_event(self):
        self.assertEqual(median_observation([(5.0, True), (CAP, True), (CAP, False)], CAP), (CAP, True))


if __name__ == '__main__':
    unittest.main()
