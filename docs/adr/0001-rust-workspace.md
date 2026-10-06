# ADR-0001: Rust workspace

Status: accepted.

Use edition 2024 Rust with seven small responsibility-based crates. Checked integer arithmetic and immutable task inputs make invariants explicit. Workspace version, license and lints are shared. Dependencies are limited to serialization, TOML, errors and CLI parsing; no services or async runtime. Separate crate compilation has some overhead, but avoids coupling CLI/file/provenance behavior to simulation semantics.
