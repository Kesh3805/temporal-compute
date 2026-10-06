"""One-time manifest bootstrap; not required to build or run TC-0."""
from pathlib import Path

dependencies = {
    'tc-core': ['serde', 'thiserror'],
    'tc-ir': ['tc-core', 'serde', 'toml', 'thiserror'],
    'tc-scheduler': ['tc-core', 'tc-ir', 'serde'],
    'tc-trace': ['tc-core', 'serde', 'serde_json'],
    'tc-metrics': ['tc-core', 'tc-ir', 'tc-trace', 'serde', 'thiserror'],
    'tc-sim': ['tc-core', 'tc-ir', 'tc-scheduler', 'tc-trace', 'tc-metrics', 'serde', 'thiserror'],
    'tc-cli': ['tc-ir', 'tc-scheduler', 'tc-trace', 'tc-sim', 'serde', 'serde_json', 'clap', 'anyhow'],
}
for name, deps in dependencies.items():
    root = Path('crates') / name
    (root / 'src').mkdir(parents=True, exist_ok=True)
    manifest = f'[package]\nname = "{name}"\nversion.workspace = true\nedition.workspace = true\nrust-version.workspace = true\nlicense.workspace = true\n\n[lints]\nworkspace = true\n\n[dependencies]\n'
    manifest += ''.join(f'{dep}.workspace = true\n' for dep in deps)
    if name == 'tc-cli':
        manifest += '\n[[bin]]\nname = "tc"\npath = "src/main.rs"\n'
    (root / 'Cargo.toml').write_text(manifest, encoding='utf-8')
