"""Independent bound/threshold checks; no source fetch, binary or rendering."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from checkpoint_amendment import (InitializationBoundViolation, InitializationMismatch,
                                  require_identical_initialization, unit_checkpoints, validate_amendment)
from integration_budget import derive, validate_sample_bound


class IntegrationBudgetTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.proposal = json.loads((root/'research/tc-r1/integration/checkpoint-proposal.json').read_text())

    def test_independent_initialization_and_schedule_answers(self):
        report = derive(self.proposal)
        self.assertEqual(report['mandatory_camera_samples'], 2097152)
        self.assertEqual(report['initialization_charged_upper_bound'], 35651584)
        self.assertEqual(report['paired_request_charged_upper_bound'], 34816)
        self.assertEqual(report['proposed_total_checkpoints'], [36700160, 39845888, 52428800, 102760448])
        self.assertFalse(report['active_execution_configuration'])
        self.assertFalse(report['host_selected'])
        self.assertFalse(report['comparative_execution_authorized'])

    def test_actual_classes_not_camera_multiplier_are_charged(self):
        # Independent synthetic ledger with missing direct lighting and a
        # generated continuation discarded before another intersection query.
        events = ['camera', 'continuation', 'continuation', 'visibility']
        charged = validate_sample_bound(*(events.count(k) for k in ('camera','continuation','visibility')))
        self.assertEqual(charged, len(events))
        self.assertEqual(validate_sample_bound(1, 8, 8), 17)
        self.assertEqual(validate_sample_bound(1, 0, 0), 1)
        for counts in ((0,0,0),(2,0,0),(1,9,0),(1,0,9),(1,-1,0),(True,0,0)):
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                validate_sample_bound(*counts)

    def test_proposal_binds_retained_upstream_and_exact_corpus(self):
        root = Path(__file__).resolve().parents[2]
        retained = json.loads((root/'research/tc-r1/e3/build-manifest.json').read_text())
        self.assertEqual(self.proposal['pbrt_commit'], retained['upstream_commit'])
        self.assertEqual(self.proposal['source_sha256']['src/pbrt/cpu/integrators.cpp'], retained['source_sha256'])
        corpus = root/'research/tc-r1/corpus/manifest.json'
        self.assertEqual(self.proposal['corpus_manifest_sha256'], hashlib.sha256(corpus.read_bytes()).hexdigest())
        manifest = json.loads(corpus.read_text())
        self.assertEqual(manifest['envelope']['maxdepth'], 8)
        self.assertEqual(manifest['resolution'], [256,256])

    def test_complete_pair_at_integer_boundary_has_declared_overshoot(self):
        report = derive(self.proposal)
        request = report['paired_request_charged_upper_bound']
        for threshold in report['proposed_total_checkpoints']:
            before = threshold-1
            # A complete worst-case request counts two streams separately;
            # threshold crossing never discards the second stream or long paths.
            after = before + 17408 + 17408
            self.assertEqual(after-threshold, 34815)
            self.assertEqual(after-threshold, report['maximum_integer_checkpoint_overshoot'])
            self.assertLess(report['initialization_charged_upper_bound'], threshold)

    def test_drift_and_false_execution_claims_rejected(self):
        for name, value in (('width',128),('paired_streams',1),('mandatory_spp_per_stream',8),
                            ('maximum_path_depth',9),('batch_spp_per_stream',True),
                            ('policy_performance_observed',True),('status','execution-ready'),
                            ('protocol_commit','unregistered'),('corpus_manifest_sha256','unbound'),
                            ('source_sha256',{}),
                            ('original_checkpoints',[4194304,4194304,16777216,67108864]),
                            ('proposed_total_checkpoints',[4194304,16777216,67108864,268435456])):
            changed = deepcopy(self.proposal)
            changed[name] = value
            with self.subTest(name=name), self.assertRaises(ValueError): derive(changed)


POLICIES = ('uniform', 'adaptive', 'variance', 'controller', 'no-feedback', 'equal-cost')


class AmendmentThreeTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.raw = (root/'research/tc-r1/integration/checkpoint-proposal.json').read_bytes()
        self.contract = json.loads((root/'research/tc-r1/integration/checkpoint-amendment-0003.json').read_text())

    def test_contract_binds_preserved_proposal_and_bounds(self):
        report = validate_amendment(self.contract, self.raw)
        self.assertEqual(self.contract['superseded_proposal']['sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(report['post_initialization_increments'], [2**20, 2**22, 2**24, 2**26])
        self.assertEqual(report['initialization_upper_bound'], 2*256*256*16*17)
        self.assertEqual(report['maximum_integer_checkpoint_overshoot'], 34815)
        self.assertFalse(report['active_execution_configuration'])
        self.assertFalse(report['native_validation_performed'])
        with self.assertRaises(ValueError):
            validate_amendment(self.contract, self.raw + b' ')

    def test_unit_totals_are_actual_initialization_plus_increments(self):
        # Fixture class-sum ratio ~1.99 applied to the mandatory camera samples.
        actual = 4173069
        self.assertEqual(unit_checkpoints(actual, self.contract),
                         (actual + 1048576, actual + 4194304, actual + 16777216, actual + 67108864))
        self.assertEqual(unit_checkpoints(35651584, self.contract), (36700160, 39845888, 52428800, 102760448))
        self.assertEqual(unit_checkpoints(2097152, self.contract)[0], 3145728)
        totals = unit_checkpoints(actual, self.contract)
        self.assertEqual([b - a for a, b in zip(totals, totals[1:])], [3145728, 12582912, 50331648])

    def test_rejects_non_int_and_out_of_bound_initialization(self):
        for value in (True, 4173069.0, '4173069', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                unit_checkpoints(value, self.contract)
        for value in (0, -1, 2097151, 35651585):
            with self.subTest(value=value), self.assertRaises(InitializationBoundViolation):
                unit_checkpoints(value, self.contract)

    def test_initialization_must_be_identical_across_six_policies(self):
        self.assertEqual(require_identical_initialization(dict.fromkeys(POLICIES, 4173069)), 4173069)
        mismatched = dict.fromkeys(POLICIES, 4173069)
        mismatched['controller'] = 4173070
        with self.assertRaises(InitializationMismatch):
            require_identical_initialization(mismatched)
        for charges in ({p: 4173069 for p in POLICIES[:5]}, {**dict.fromkeys(POLICIES, 4173069), 'extra': 4173069},
                        {**dict.fromkeys(POLICIES, 4173069), 'uniform': 4173069.0},
                        {**dict.fromkeys(POLICIES, True)}, list(POLICIES)):
            with self.subTest(charges=charges), self.assertRaises(ValueError):
                require_identical_initialization(charges)

    def test_contract_drift_rejected(self):
        for name, value in (('schema', 'tc-r1-integration-checkpoints-v1'), ('status', 'execution-ready'),
                            ('decision_date', '2026-10-13'), ('policy_performance_observed', True),
                            ('protocol_commit', 'unregistered'), ('pbrt_commit', 'other'),
                            ('checkpoint_kind', 'total charged rays'),
                            ('post_initialization_increments', [4194304, 4194304, 16777216, 67108864]),
                            ('post_initialization_increments', [1048576.0, 4194304, 16777216, 67108864]),
                            ('initialization_lower_bound', 1), ('initialization_upper_bound', 35651585),
                            ('initialization_upper_bound', True), ('paired_request_upper_bound', 34817),
                            ('maximum_integer_checkpoint_overshoot', 34816), ('rules', {}),
                            ('superseded_proposal', {'path': 'research/tc-r1/integration/checkpoint-proposal.json',
                                                     'sha256': '0'*64, 'adopted': False}),
                            ('superseded_proposal', {'path': 'research/tc-r1/integration/checkpoint-proposal.json',
                                                     'sha256': self.contract['superseded_proposal']['sha256'],
                                                     'adopted': True})):
            changed = deepcopy(self.contract)
            changed[name] = value
            with self.subTest(name=name, value=value):
                with self.assertRaises(ValueError): validate_amendment(changed, self.raw)
                with self.assertRaises(ValueError): unit_checkpoints(4173069, changed)


if __name__ == '__main__':
    unittest.main()
