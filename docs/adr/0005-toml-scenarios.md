# ADR-0005: TOML scenarios

Status: accepted.

Use versioned TOML with Serde and strict unknown-field rejection. Tasks and curves are readable without a custom DSL. Check in fixtures and their deterministic generation recipe. Embed full parsed definitions in JSON reports for reproduction. A new schema version is required for incompatible workload changes; no scheduler-specific configuration behavior exists.
