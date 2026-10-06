"""Validate every frozen TC-S1 definition in Rust without running policies."""
import subprocess
import tempfile
import tc_s1_generate as gen
from tc_s1 import build


def main():
    gen.verify()
    cfg = gen.config()
    binary = build()
    expected = []
    with tempfile.TemporaryFile() as source:
        for meta, scenario in gen.corpus(cfg, sensitivities=True):
            expected.append(meta['id'])
            source.write(gen.canonical(dict(scenario=scenario, seed=meta['seed'], schedulers=[])))
        source.seek(0)
        result = subprocess.run([str(binary), 'validate'], stdin=source, capture_output=True, check=True)
    if result.stdout.decode().splitlines() != expected:
        raise ValueError('Rust validation identity/count mismatch')
    print(f'{len(expected)} frozen definitions validated in Rust; no policy outcomes generated.')


if __name__ == '__main__':
    main()
