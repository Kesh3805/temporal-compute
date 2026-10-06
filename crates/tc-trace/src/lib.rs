//! Versioned event schema and JSON Lines encoding. File ownership stays in the CLI.
use serde::{Deserialize, Serialize};
use std::io::Write;
use tc_core::{Duration, SimTime, TaskId, Utility};

pub const TRACE_SCHEMA_VERSION: u32 = 1;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Candidate {
    pub task_id: TaskId,
    pub predicted_completion_us: SimTime,
    pub predicted_utility: Utility,
    pub execution_cost_us: Duration,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Event {
    pub schema_version: u32,
    pub sequence: u64,
    pub sim_time_us: SimTime,
    pub scheduler: String,
    #[serde(flatten)]
    pub kind: EventKind,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "event", rename_all = "snake_case")]
pub enum EventKind {
    SimulationStarted { scenario: String, seed: u64 },
    TaskArrived { task_id: TaskId },
    SchedulerDecision { selected: TaskId, candidates: Vec<Candidate> },
    TaskStarted { task_id: TaskId, predicted_completion_us: SimTime, predicted_utility: Utility },
    TaskCompleted { task_id: TaskId, utility: Utility, deadline_met: Option<bool>, fresh: bool, execution_cost_us: Duration, completion_latency_us: Duration, result_age_us: Duration },
    TaskExpired { task_id: TaskId, reason: ExpiryReason },
    SimulationCompleted,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ExpiryReason { Deadline, Freshness }

pub fn write_jsonl(writer: &mut impl Write, events: &[Event]) -> Result<(), serde_json::Error> {
    for event in events {
        serde_json::to_writer(&mut *writer, event)?;
        writer.write_all(b"\n").map_err(serde_json::Error::io)?;
    }
    Ok(())
}
