"""Corpus boundary/provenance tests; never render the primary scenes."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('corpus', Path(__file__).with_name('corpus.py'))
corpus = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(corpus)


class CorpusTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for path in ['research/tc-r1/corpus/schema.json', 'research/tc-r1/corpus/specifications.json',
                     'experiments/tc-r1/corpus.py', 'LICENSE-MIT', 'LICENSE-APACHE']:
            destination = self.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(corpus.ROOT / path, destination)

    def definition(self):
        return copy.deepcopy(corpus.source_scenes(self.root)[1][0]['frames'][0]['definition'])

    def test_authored_corpus_reconstructs_all_thirty_assets(self):
        result = corpus.write(self.root)
        self.assertEqual((result['scenes'], result['frames']), (10, 30))
        self.assertFalse(result['rendering_performed'])
        self.assertEqual(result, corpus.verify())
        with self.assertRaisesRegex(ValueError, 'already authored'):
            corpus.write(self.root)

    def test_asset_and_input_tampering_are_retained_as_failures(self):
        corpus.write(self.root)
        scene = self.root / 'research/tc-r1/corpus/scenes/uniform-01/f0.pbrt'
        original = scene.read_bytes()
        scene.write_bytes(original + b'Texture "escape" "spectrum" "imagemap"\n')
        with self.assertRaisesRegex(ValueError, 'asset bytes differ'):
            corpus.verify(self.root)
        scene.write_bytes(original)
        license_path = self.root / 'LICENSE-MIT'
        license_path.write_bytes(license_path.read_bytes() + b'changed\n')
        with self.assertRaisesRegex(ValueError, 'manifest/source/hash mismatch'):
            corpus.verify(self.root)

    def test_missing_additional_and_path_spoofed_assets_fail(self):
        corpus.write(self.root)
        scene = self.root / 'research/tc-r1/corpus/scenes/uniform-01/f0.pbrt'
        original = scene.read_bytes()
        scene.unlink()
        with self.assertRaisesRegex(ValueError, 'missing or additional'):
            corpus.verify(self.root)
        scene.write_bytes(original)
        extra = scene.with_name('extra.pbrt')
        extra.write_bytes(original)
        with self.assertRaisesRegex(ValueError, 'missing or additional'):
            corpus.verify(self.root)
        extra.unlink()
        path = self.root / 'research/tc-r1/corpus/manifest.json'
        manifest = corpus.load(path)
        manifest['scenes'][0]['frames'][0]['path'] = '../../escape.pbrt'
        path.write_bytes(corpus.canonical(manifest))
        with self.assertRaisesRegex(ValueError, 'manifest/source/hash mismatch'):
            corpus.verify(self.root)

    def test_out_of_envelope_features_and_parameters_rejected(self):
        for mutate in [
            lambda d: d['camera'].update(lensradius=1),
            lambda d: d.update(media=[]),
            lambda d: d['materials']['neutral'].update(normalmap='x.png'),
            lambda d: d['materials']['neutral'].update(type='subsurface'),
            lambda d: d['lights'][0].update(filename='environment.exr'),
            lambda d: d['objects'][0]['shape'].update(type='plymesh'),
        ]:
            with self.subTest(mutation=mutate):
                definition = self.definition()
                mutate(definition)
                with self.assertRaises(ValueError):
                    corpus.serialize(definition)

    def test_invalid_numeric_camera_and_geometry_definitions_rejected(self):
        for mutate in [
            lambda d: d['camera'].update(target=d['camera']['position']),
            lambda d: d['camera'].update(fov=float('nan')),
            lambda d: d['camera'].update(fov=True),
            lambda d: d['objects'][0]['shape'].update(indices=[0, 1, 99]),
            lambda d: d['objects'][0]['shape'].update(indices=[0, 0, 1]),
            lambda d: d['objects'][-1]['shape'].update(radius=-1),
            lambda d: d['materials']['neutral'].update(reflectance=[1.1, .5, .5]),
        ]:
            with self.subTest(mutation=mutate):
                definition = self.definition()
                mutate(definition)
                with self.assertRaises(ValueError):
                    corpus.serialize(definition)

    def test_scene_family_identity_and_frame_invariants_rejected(self):
        path = self.root / 'research/tc-r1/corpus/specifications.json'
        original = path.read_bytes()
        for mutate in [
            lambda scenes: scenes.pop(),
            lambda scenes: scenes[0].update(family='highly-specular'),
            lambda scenes: scenes[0]['frames'][1].update(time=.25),
            lambda scenes: scenes[0]['frames'][1]['definition']['camera'].update(fov=46),
            lambda scenes: scenes[6]['frames'][1].update(definition=scenes[6]['frames'][0]['definition']),
        ]:
            with self.subTest(mutation=mutate):
                scenes = json.loads(original)
                mutate(scenes)
                path.write_bytes(corpus.canonical(scenes))
                with self.assertRaises(ValueError):
                    corpus.expected(self.root)
        path.write_bytes(original)

    def test_duplicate_json_keys_fail_closed(self):
        path = self.root / 'duplicate.json'
        path.write_text('{"camera": {}, "camera": {}}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate JSON field'):
            corpus.load(path)

    def test_schema_cannot_silently_admit_new_streams_or_renderer_features(self):
        path = self.root / 'research/tc-r1/corpus/schema.json'
        original = path.read_bytes()
        for mutate in [
            lambda schema: schema['envelope'].update(integrator='volpath'),
            lambda schema: schema['streams'].update(master_seed=123),
            lambda schema: schema['streams'].update(reference_replicate=1),
            lambda schema: schema.update(resolution=[512, 512]),
        ]:
            with self.subTest(mutation=mutate):
                schema = json.loads(original)
                mutate(schema)
                path.write_bytes(corpus.canonical(schema))
                with self.assertRaisesRegex(ValueError, 'frozen schema identities/envelope'):
                    corpus.expected(self.root)
        path.write_bytes(original)

    def test_in_repository_file_and_directory_symlinks_rejected(self):
        corpus.write(self.root)
        scene_root = self.root / 'research/tc-r1/corpus/scenes'
        asset = scene_root / 'uniform-01/f0.pbrt'
        duplicate = self.root / 'identical.pbrt'
        duplicate.write_bytes(asset.read_bytes())
        asset.unlink()
        try:
            asset.symlink_to(duplicate)
        except OSError as error:
            self.skipTest('Host cannot create symlinks: ' + str(error))
        with self.assertRaisesRegex(ValueError, 'symlinked or non-regular'):
            corpus.verify(self.root)
        asset.unlink()
        asset.write_bytes(duplicate.read_bytes())
        moved = self.root / 'moved-scenes'
        scene_root.rename(moved)
        scene_root.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlinked scene parent'):
            corpus.verify(self.root)

    @unittest.skipIf(os.name == 'nt', 'POSIX named pipe fixture')
    def test_non_regular_scene_entry_rejected(self):
        corpus.write(self.root)
        os.mkfifo(self.root / 'research/tc-r1/corpus/scenes/extra.pipe')
        with self.assertRaisesRegex(ValueError, 'non-regular'):
            corpus.verify(self.root)

    def test_external_canonical_manifest_symlink_rejected(self):
        corpus.write(self.root)
        manifest = self.root / 'research/tc-r1/corpus/manifest.json'
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'manifest.json'
            target.write_bytes(manifest.read_bytes())
            manifest.unlink()
            try:
                manifest.symlink_to(target)
            except OSError as error:
                self.skipTest('Host cannot create symlinks: ' + str(error))
            with self.assertRaisesRegex(ValueError, 'manifest must be an in-root regular file'):
                corpus.verify(self.root)

    @unittest.skipIf(os.name == 'nt', 'POSIX named pipe fixture')
    def test_non_regular_manifest_rejected_before_read(self):
        corpus.write(self.root)
        manifest = self.root / 'research/tc-r1/corpus/manifest.json'
        manifest.unlink()
        os.mkfifo(manifest)
        with self.assertRaisesRegex(ValueError, 'manifest must be an in-root regular file'):
            corpus.verify(self.root)


if __name__ == '__main__':
    unittest.main()
