"""v2 gate harness checks on fabricated rows; never computes the v2 verdict."""
import unittest

import numpy as np

import offline_gate as v1
import offline_gate_v2 as v2


class OfflineGateV2Tests(unittest.TestCase):
    def test_fresh_seed_namespace(self):
        for field in v1.FIELDS:
            self.assertNotEqual(v2.FieldV2(field, 3).seed, v1.Field(field, 3).seed)
            self.assertFalse(np.allclose(v2.FieldV2(field, 3).mu, v1.Field(field, 3).mu))
        np.testing.assert_allclose(v2.FieldV2('gaussian', 4, 10).draw(2, 1), 10*v2.FieldV2('gaussian', 4).draw(2, 1))

    def test_field_v2_matches_v1_construction_on_equal_raw_seeds(self):
        # FieldV2 duplicates v1.Field.__init__ to keep offline_gate.py byte-frozen;
        # with the seed function swapped back, every derived field must be identical.
        from unittest import mock
        with mock.patch.object(v2, 'field_seed', v1.field_seed):
            for field in v1.FIELDS:
                for rays in ('homogeneous', 'heterogeneous'):
                    a, b = v2.FieldV2(field, 3, 10.0, rays), v1.Field(field, 3, 10.0, rays)
                    self.assertEqual(a.seed, b.seed)
                    for attr in ('mu', 'param', 'variance', 'rays'):
                        np.testing.assert_array_equal(getattr(a, attr), getattr(b, attr), err_msg=attr)
                    np.testing.assert_array_equal(a.draw(5, 2), b.draw(5, 2))

    def test_verdict_logic_on_fabricated_rows(self):
        def rows(amended):
            return [dict(method=m, field=f, scale=s, seed=3,
                         efficiency={str(h): (0.5 if m == 'uniform' else amended if m.startswith('amended') else 0.4)
                                     for h in v1.HORIZONS})
                    for m in v2.METHODS for f in v1.FIELDS for s in v1.SCALES]

        def ident(det_het, eq_nonexplore):
            keys = ('full|wall|homogeneous', 'full|wall|heterogeneous', 'full|deterministic|homogeneous',
                    'full|deterministic|heterogeneous', 'equal-cost|deterministic|homogeneous')
            rates = {k: dict(d=0.0, d_nonexplore=0.0, post_decisions=1) for k in keys}
            rates['full|deterministic|heterogeneous']['d'] = det_het
            rates['equal-cost|deterministic|homogeneous']['d_nonexplore'] = eq_nonexplore
            return [dict(field='gaussian', seed=3, rates=rates, no_feedback_total_variation=0.0)]
        go = v2.evaluate(rows(0.9), ident(0.2, 0.0))
        self.assertEqual((go['gate_verdict'], go['amendment_effective']), ('GO', True))
        self.assertEqual(go['competence']['adaptive-mc-ucb-region']['verdict'], 'NOT COMPETENT')
        failed = v2.evaluate(rows(0.7), ident(0.0, 0.2))
        self.assertEqual((failed['gate_verdict'], failed['amendment_effective']), ('AMEND-BASELINE-FAILED', False))
        self.assertEqual(v2.evaluate(rows(0.9), ident(0.05, 0.05))['gate_verdict'], 'STOP-RETHINK')


if __name__ == '__main__':
    unittest.main()
