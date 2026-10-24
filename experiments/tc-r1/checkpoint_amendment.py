"""Amendment 0003 checkpoint contract: actual initialization plus fixed increments.

Kept separate from integration_budget.py, whose bytes are bound by the frozen
native-validation contract. Pure arithmetic; never render or activate budgets.
"""
import hashlib
import json
from pathlib import Path

from integration_budget import ORIGINAL, PIN, PROTOCOL, derive
from progressive_kernel import require


PROPOSAL_SHA256 = '27876cb722af9a86c317ca38e4bdf5f0f36817863f31adf58ed7c135bcfb54a2'
AMENDMENT_STATUS = 'adopted-pre-outcome-amendment; not active execution configuration until execution freeze'
IMIN = 2 * 256 * 256 * 16
IMAX = IMIN * 17
JMAX = 2 * 256 * 4 * 17
# Registered policy identities (native-validation paired runner names). No
# compatible PBRT-native adaptive baseline exists in the admitted path
# (research/tc-r1/native-baseline-inspection.json), so none is included; an
# execution manifest that admits one must pass the extended set explicitly.
REGISTERED_POLICIES = frozenset({'uniform', 'adaptive-mc-ucb-region', 'variance-guided',
                                 'tc-full', 'tc-equal-cost', 'tc-no-feedback'})
# SHA-256 of canonical JSON {derivation, rules} (sorted keys, compact separators,
# UTF-8): any wording change to a rule needs a new versioned amendment.
RULES_SHA256 = '09a0fd10b4a2fc956bc9bda81331e92fbf6628724f2dd17259ebffafa04661af'
RULES = {'identical_initialization', 'initialization_bound', 'completion', 'accounting', 'disclosure',
         'analysis_keys', 'unchanged'}


class InitializationMismatch(ValueError):
    """Policies disagree on a unit's initialization charge: retained correctness failure."""


class InitializationBoundViolation(ValueError):
    """Initialization charge outside the admitted envelope: integration stops."""


def _check_amendment(contract):
    require(contract['schema'] == 'tc-r1-integration-checkpoints-v2' and contract['status'] == AMENDMENT_STATUS,
            'not the adopted amendment 0003 checkpoint contract')
    require(contract['decision_date'] == '2026-10-12' and contract['policy_performance_observed'] is False,
            'undated or performance-informed amendment')
    require(contract['protocol_commit'] == PROTOCOL and contract['pbrt_commit'] == PIN,
            'wrong original protocol or renderer binding')
    require(contract['superseded_proposal'] == dict(path='research/tc-r1/integration/checkpoint-proposal.json',
                                                    sha256=PROPOSAL_SHA256, adopted=False),
            'superseded proposal binding drift')
    require(type(contract['rules']) is dict and set(contract['rules']) == RULES and
            all(type(v) is str and v for v in contract['rules'].values()), 'amendment rule set drift')
    canonical = json.dumps(dict(derivation=contract['derivation'], rules=contract['rules']), sort_keys=True,
                           separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    require(hashlib.sha256(canonical).hexdigest() == RULES_SHA256, 'amendment rule meaning drift')
    require(contract['checkpoint_kind'] == 'post-initialization increments', 'checkpoint labelling drift')
    increments = contract['post_initialization_increments']
    require(type(increments) is list and tuple(increments) == ORIGINAL and all(type(v) is int for v in increments),
            'increment drift')
    bounds = dict(initialization_lower_bound=IMIN, initialization_upper_bound=IMAX, paired_request_upper_bound=JMAX,
                  maximum_integer_checkpoint_overshoot=JMAX-1)
    require(all(type(contract[k]) is int and contract[k] == v for k, v in bounds.items()), 'bound drift')
    return contract


def validate_amendment(contract, proposal_bytes):
    """Validate the v2 contract against the preserved v1 proposal bytes."""
    _check_amendment(contract)
    require(hashlib.sha256(proposal_bytes).hexdigest() == PROPOSAL_SHA256, 'preserved proposal changed')
    proposal = derive(json.loads(proposal_bytes))
    require(proposal['mandatory_camera_samples'] == contract['initialization_lower_bound'] and
            proposal['initialization_charged_upper_bound'] == contract['initialization_upper_bound'] and
            proposal['paired_request_charged_upper_bound'] == contract['paired_request_upper_bound'],
            'amendment bounds disagree with source-bound derivation')
    return dict(schema='tc-r1-checkpoint-amendment-report-v2', active_execution_configuration=False,
                checkpoint_kind=contract['checkpoint_kind'], post_initialization_increments=list(ORIGINAL),
                initialization_lower_bound=IMIN, initialization_upper_bound=IMAX,
                paired_request_upper_bound=JMAX, maximum_integer_checkpoint_overshoot=JMAX-1,
                unit_total_range=[[IMIN + v, IMAX + v] for v in ORIGINAL],
                host_selected=False, native_validation_performed=False, comparative_execution_authorized=False)


def require_identical_initialization(charges_by_policy, policies=REGISTERED_POLICIES):
    """Return the unit's policy-independent initialization charge or fail the unit."""
    require(type(policies) is frozenset and policies >= REGISTERED_POLICIES, 'registered policy set required')
    require(type(charges_by_policy) is dict and set(charges_by_policy) == policies,
            'initialization charges must cover exactly the registered policies')
    require(all(type(v) is int for v in charges_by_policy.values()), 'initialization charge must be int')
    if len(set(charges_by_policy.values())) != 1:
        raise InitializationMismatch('policy initialization charges differ; unit is a retained correctness failure')
    return next(iter(charges_by_policy.values()))


def unit_checkpoints(actual_initialization, contract):
    """Absolute nominal thresholds A_u + I_k for one scene/frame/replicate unit."""
    _check_amendment(contract)
    require(type(actual_initialization) is int, 'initialization charge must be int')
    # Positive and, since every mandatory camera sample charges exactly one camera ray,
    # at least the camera-only initialization charge.
    if not 0 < contract['initialization_lower_bound'] <= actual_initialization <= contract['initialization_upper_bound']:
        raise InitializationBoundViolation('initialization charge outside admitted bound; stop integration')
    return tuple(actual_initialization + v for v in contract['post_initialization_increments'])


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    raw = (root/'research/tc-r1/integration/checkpoint-proposal.json').read_bytes()
    amendment = json.loads((root/'research/tc-r1/integration/checkpoint-amendment-0003.json').read_text())
    print(json.dumps(validate_amendment(amendment, raw), indent=2, allow_nan=False))
