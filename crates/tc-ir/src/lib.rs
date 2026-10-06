//! Validated workload representation shared by every policy.
mod utility;
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use tc_core::{Duration, Priority, SimTime, TaskId, Utility};
use thiserror::Error;
pub use utility::{UtilityCurve, UtilityStep};

#[derive(Debug, Error)]
pub enum ScenarioError {
    #[error("invalid TOML: {0}")]
    Parse(#[from] toml::de::Error),
    #[error("invalid scenario: {0}")]
    Invalid(String),
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TemporalTask {
    pub id: TaskId,
    pub arrival_time_us: SimTime,
    pub execution_cost_us: Duration,
    pub deadline_us: Option<SimTime>,
    #[serde(default)]
    pub priority: Priority,
    pub base_utility: Utility,
    pub utility: UtilityCurve,
    pub fresh_until_us: Option<SimTime>,
    pub input_time_us: Option<SimTime>,
}

impl TemporalTask {
    pub fn expiry_limit(&self) -> Option<SimTime> {
        match (self.deadline_us, self.fresh_until_us) {
            (Some(a), Some(b)) => Some(a.min(b)),
            (a, b) => a.or(b),
        }
    }

    pub fn utility_at(&self, completion: SimTime) -> Utility {
        if completion < self.arrival_time_us
            || self.expiry_limit().is_some_and(|limit| completion > limit)
        {
            return Utility(0);
        }
        self.utility.evaluate(self, completion)
    }

    pub fn input_time(&self) -> SimTime {
        self.input_time_us.unwrap_or(self.arrival_time_us)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Scenario {
    pub schema_version: u32,
    pub name: String,
    pub description: String,
    pub tasks: Vec<TemporalTask>,
}

impl Scenario {
    pub fn from_toml(source: &str) -> Result<Self, ScenarioError> {
        let scenario: Self = toml::from_str(source)?;
        scenario.validate()?;
        Ok(scenario)
    }

    pub fn validate(&self) -> Result<(), ScenarioError> {
        let fail = |s: String| ScenarioError::Invalid(s);
        if self.schema_version != 1 || self.name.trim().is_empty() {
            return Err(fail("expected schema_version=1 and a nonempty name".into()));
        }
        let mut ids = BTreeSet::new();
        let mut compute = 0_u64;
        let mut utility = 0_u64;
        let mut last_arrival = 0;
        for task in &self.tasks {
            let invalid = |why: &str| fail(format!("task {}: {why}", task.id.0));
            if task.id.0.trim().is_empty() || !ids.insert(&task.id) {
                return Err(invalid("empty or duplicate id"));
            }
            if task.execution_cost_us.0 == 0 {
                return Err(invalid("execution cost must be positive"));
            }
            if task
                .expiry_limit()
                .is_some_and(|t| t < task.arrival_time_us)
                || task.input_time() > task.arrival_time_us
            {
                return Err(invalid(
                    "deadline/freshness precedes arrival or input follows arrival",
                ));
            }
            task.utility.validate(task).map_err(invalid)?;
            compute = compute
                .checked_add(task.execution_cost_us.0)
                .ok_or_else(|| invalid("total compute overflow"))?;
            utility = utility
                .checked_add(task.base_utility.0)
                .ok_or_else(|| invalid("total utility overflow"))?;
            last_arrival = last_arrival.max(task.arrival_time_us.0);
        }
        // A conservative bound makes all scheduling completion predictions safe.
        last_arrival
            .checked_add(compute)
            .ok_or_else(|| fail("simulation time bound overflows".into()))?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn rejects_unknown_configuration() {
        assert!(
            Scenario::from_toml("schema_version=1\nname='x'\ndescription=''\ntasks=[]\ncpus=2")
                .is_err()
        );
    }
}
