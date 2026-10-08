"""Source-bound checkpoint proposal arithmetic; never render or activate budgets."""
import json
from pathlib import Path

from progressive_kernel import require


ORIGINAL = (2**20, 2**22, 2**24, 2**26)
PIN = 'b4ce9687e6c695f5582997c61b0c66cf064bdb4a'
PROTOCOL = '99ad341775ed3e60bd262134783eeb2244700e76'
CORPUS = 'f9b094765daea47d0ebb6f05fd891a6de505d14a611df3d28aca88019f8b628f'
SOURCE_HASHES = {
    'src/pbrt/cpu/integrators.cpp': 'c5f7c8dafb4dc44cac78ab969e34217c13358a5cea6a6d2052581d68c7bc762e',
    'src/pbrt/cpu/integrators.h': '98068db62e6bbca119f45aea4e3d967edca46f6f975146bf1a785ad9c4d43a0c',
}


def derive(proposal):
    require(proposal['schema'] == 'tc-r1-integration-checkpoints-v1' and
            proposal['status'] == 'proposed-pre-outcome-amendment; not active execution configuration',
            'not a proposed integration checkpoint contract')
    require(proposal['pbrt_commit'] == PIN and proposal['policy_performance_observed'] is False,
            'wrong renderer or performance-informed proposal')
    require(proposal['protocol_commit'] == PROTOCOL and proposal['corpus_manifest_sha256'] == CORPUS,
            'wrong original protocol or corpus binding')
    require(proposal['source_sha256'] == SOURCE_HASHES, 'changed source invalidates the inspected bound')
    frozen = dict(width=256, height=256, paired_streams=2, mandatory_spp_per_stream=16,
                  batch_spp_per_stream=4, maximum_region_pixels=256, maximum_path_depth=8)
    require(all(type(proposal[name]) is int and proposal[name] == value
                for name, value in frozen.items()), 'changed candidate/envelope needs another explicit decision')
    require(proposal['per_camera_charge_bound'] == dict(camera=1, continuation=8, visibility=8),
            'unsupported path-work bound')
    require(all(type(v) is int for v in proposal['per_camera_charge_bound'].values()), 'invalid ray bound type')
    require(tuple(proposal['original_checkpoints']) == ORIGINAL and
            all(type(v) is int for v in proposal['original_checkpoints']), 'original checkpoint drift')
    per_camera = 1 + 2 * frozen['maximum_path_depth']
    camera_samples = frozen['paired_streams'] * frozen['width'] * frozen['height'] * frozen['mandatory_spp_per_stream']
    initialization = camera_samples * per_camera
    request = frozen['paired_streams'] * frozen['maximum_region_pixels'] * frozen['batch_spp_per_stream'] * per_camera
    checkpoints = tuple(initialization + value for value in ORIGINAL)
    require(tuple(proposal['proposed_total_checkpoints']) == checkpoints and
            all(type(v) is int for v in proposal['proposed_total_checkpoints']), 'incorrect checkpoint derivation')
    require(checkpoints[0] > initialization and
            all(b-a > request for a, b in zip(checkpoints, checkpoints[1:])), 'initialization or checkpoint gap')
    return dict(schema='tc-r1-checkpoint-proposal-report-v1', active_execution_configuration=False,
                mandatory_camera_samples=camera_samples, per_camera_charge_upper_bound=per_camera,
                initialization_charged_upper_bound=initialization, paired_request_charged_upper_bound=request,
                maximum_integer_checkpoint_overshoot=request-1, proposed_total_checkpoints=list(checkpoints),
                host_selected=False, native_validation_performed=False, comparative_execution_authorized=False)


def validate_sample_bound(camera, continuation, visibility):
    require(all(type(v) is int for v in (camera, continuation, visibility)) and camera == 1 and
            0 <= continuation <= 8 and 0 <= visibility <= 8, 'native sample exceeds admitted class bound')
    return camera + continuation + visibility


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[2]
    proposal = json.loads((root/'research/tc-r1/integration/checkpoint-proposal.json').read_text())
    print(json.dumps(derive(proposal), indent=2, allow_nan=False))
