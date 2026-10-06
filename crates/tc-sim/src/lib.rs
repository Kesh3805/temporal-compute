//! Single-CPU non-preemptive discrete-event simulator; no wall clock or RNG.
mod engine;
pub use engine::simulate;
use serde::{Deserialize, Serialize};
use tc_ir::{Scenario, ScenarioError};
use tc_metrics::{Metrics, MetricsError};
use tc_trace::Event;
use thiserror::Error;

pub const SIMULATION_VERSION: &str = "tc0-1";

#[derive(Debug, Error)]
pub enum SimulationError {
    #[error(transparent)]
    Scenario(#[from] ScenarioError),
    #[error(transparent)]
    Time(#[from] tc_core::TimeOverflow),
    #[error(transparent)]
    Metrics(#[from] MetricsError),
    #[error("scheduler contract violation: {0}")]
    Scheduler(String),
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Configuration {
    pub cpu_count: u32,
    pub preemption: bool,
    pub time_unit: String,
    pub expiry_mode: String,
}

impl Default for Configuration {
    fn default() -> Self {
        Self {
            cpu_count: 1,
            preemption: false,
            time_unit: "microseconds".into(),
            expiry_mode: "waiting_after_inclusive_limit".into(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RunResult {
    pub schema_version: u32,
    pub simulation_version: String,
    pub scenario: Scenario,
    pub scheduler: String,
    pub seed: u64,
    pub configuration: Configuration,
    pub metrics: Metrics,
    pub events: Vec<Event>,
}
