"""Retained native evidence integrity; no renderer execution or extraction."""
import hashlib
import json
from pathlib import Path
import tarfile
import unittest


ROOT = Path(__file__).resolve().parents[2]


class RetainedNativeValidationTests(unittest.TestCase):
    def test_terminal_native_evidence_and_all_archive_hashes(self):
        root=ROOT/'research/tc-r1/native-validation'
        retention=json.loads((root/'retention.json').read_text())
        self.assertEqual(retention['id'],37756401842)
        self.assertEqual(retention['run_attempt'],1)
        self.assertEqual(retention['head_sha'],'4f9eb2fab2e8587b58cfe75827944494bad80e32')
        self.assertEqual(retention['conclusion'],'success')
        archive=root/'raw-artifacts.tar.gz'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),retention['archive_sha256'])
        self.assertEqual(hashlib.sha256((root/'artifact-hashes.json').read_bytes()).hexdigest(),retention['artifact_hash_manifest_sha256'])
        hashes=json.loads((root/'artifact-hashes.json').read_text())
        self.assertEqual(len(hashes),3956)
        with tarfile.open(archive,'r:gz') as bundle:
            members={m.name:m for m in bundle.getmembers()}
            self.assertEqual(len(members),3957)
            self.assertTrue(all(m.isfile() for m in members.values()))
            self.assertEqual(set(members),set(hashes)|{'artifact-hashes.json'})
            self.assertEqual(bundle.extractfile(members['artifact-hashes.json']).read(),(root/'artifact-hashes.json').read_bytes())
            for name,digest in hashes.items():
                with self.subTest(name=name):
                    self.assertEqual(hashlib.sha256(bundle.extractfile(members[name]).read()).hexdigest(),digest)
            for name in ('report.json','build-manifest.json'):
                self.assertEqual(bundle.extractfile(members[name]).read(),(root/name).read_bytes())
        report=json.loads((root/'report.json').read_text())
        self.assertEqual(report['status'],'PASS')
        self.assertEqual(report['native_commands'],580)
        self.assertEqual(report['comparative_outcomes'],0)
        self.assertEqual(report['references_produced'],0)
        self.assertEqual(report['amendment_0002'],'inactive')
        self.assertEqual(report['checks']['corpus_parser']['assets'],30)
        self.assertFalse(report['checks']['corpus_parser']['rendering'])
        self.assertEqual([c['overshoot'] for c in report['checks']['checkpoint_mechanics']['checkpoints']],[256,128])
        build=json.loads((root/'build-manifest.json').read_text())
        self.assertFalse(build['scientific_host_selected'])
        self.assertTrue(build['cpu_float_build_verified'])
        self.assertEqual(report['binary_sha256'],build['binary_sha256'])
        self.assertEqual(report['build_manifest_sha256'],hashlib.sha256((root/'build-manifest.json').read_bytes()).hexdigest())
        self.assertEqual(report['implementation_sha256'],hashlib.sha256((ROOT/'experiments/tc-r1/native_validation.py').read_bytes()).hexdigest())
        self.assertEqual(report['contract_sha256'],hashlib.sha256((root/'contract.json').read_bytes()).hexdigest())

    def test_all_298_historical_e3_artifacts_remain_unchanged(self):
        root=ROOT/'research/tc-r1/e3'
        archive=root/'raw-artifacts.tar.gz'
        # Historical archive identity observed before this native-validation gate.
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),
                         '01dfa1476b15c3f7db252f98a98582afb82ba7820e1f39ba6ea83904a2b4a405')
        hashes=json.loads((root/'artifact-hashes.json').read_text())['files']
        self.assertEqual(len(hashes),298)
        with tarfile.open(archive,'r:gz') as bundle:
            members={m.name:m for m in bundle.getmembers() if m.isfile()}
            self.assertEqual(set(members),set(hashes))
            for name,digest in hashes.items():
                with self.subTest(name=name):
                    self.assertEqual(hashlib.sha256(bundle.extractfile(members[name]).read()).hexdigest(),digest)


if __name__=='__main__':
    unittest.main()
