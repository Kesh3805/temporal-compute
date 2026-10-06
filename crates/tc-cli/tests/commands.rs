use std::process::Command;

#[test]
fn compare_json_replays_and_invalid_input_is_contextual() {
    let scenario = format!(
        "{}/../../scenarios/mixed-utility/scenario.toml",
        env!("CARGO_MANIFEST_DIR")
    );
    let run = || {
        Command::new(env!("CARGO_BIN_EXE_tc"))
            .args(["compare", &scenario, "--format", "json", "--seed", "42"])
            .output()
            .unwrap()
    };
    let a = run();
    let b = run();
    assert!(a.status.success());
    assert_eq!(a.stdout, b.stdout);
    let json: serde_json::Value = serde_json::from_slice(&a.stdout).unwrap();
    assert_eq!(json["runs"].as_array().unwrap().len(), 5);
    let error = Command::new(env!("CARGO_BIN_EXE_tc"))
        .args(["simulate", "missing.toml"])
        .output()
        .unwrap();
    assert!(!error.status.success());
    assert!(String::from_utf8_lossy(&error.stderr).contains("read scenario missing.toml"));
}

#[test]
fn jsonl_roundtrips_complete_event_stream() {
    let scenario = format!(
        "{}/../../scenarios/tc0-basic/scenario.toml",
        env!("CARGO_MANIFEST_DIR")
    );
    let trace = std::env::temp_dir().join(format!("tc-trace-{}.jsonl", std::process::id()));
    let result = Command::new(env!("CARGO_BIN_EXE_tc"))
        .args(["simulate", &scenario, "--format", "json", "--trace"])
        .arg(&trace)
        .output()
        .unwrap();
    assert!(result.status.success());
    let report: serde_json::Value = serde_json::from_slice(&result.stdout).unwrap();
    let events: Vec<serde_json::Value> = std::fs::read_to_string(&trace)
        .unwrap()
        .lines()
        .map(|s| serde_json::from_str(s).unwrap())
        .collect();
    assert_eq!(
        serde_json::Value::Array(events),
        report["runs"][0]["events"]
    );
    std::fs::remove_file(trace).unwrap();
}
