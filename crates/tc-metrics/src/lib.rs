//! Metrics are reduced from the authoritative event stream.
use serde::{Deserialize, Serialize};
use tc_ir::Scenario;
use tc_trace::{Event, EventKind};
use thiserror::Error;

#[derive(Debug, Error)]
#[error("metric accumulator overflow or inconsistent trace")]
pub struct MetricsError;

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Metrics {
    pub tasks_total: u64,
    pub tasks_completed: u64,
    pub tasks_expired: u64,
    pub deadline_tasks_total: u64,
    pub deadline_hits: u64,
    pub deadline_hit_rate: Option<f64>,
    pub total_utility: u64,
    pub maximum_task_utility_sum: u64,
    pub normalized_utility: Option<f64>,
    pub compute_time_used_us: u64,
    pub compute_time_wasted_us: u64,
    pub average_completion_latency_us: Option<f64>,
    pub average_result_age_us: Option<f64>,
    pub simulation_end_us: u64,
}

fn add(target: &mut u64, value: u64) -> Result<(), MetricsError> {
    *target = target.checked_add(value).ok_or(MetricsError)?;
    Ok(())
}

pub fn reduce(scenario: &Scenario, events: &[Event]) -> Result<Metrics, MetricsError> {
    let mut m = Metrics { tasks_total: scenario.tasks.len() as u64, tasks_completed: 0, tasks_expired: 0,
        deadline_tasks_total: scenario.tasks.iter().filter(|t| t.deadline_us.is_some()).count() as u64,
        deadline_hits: 0, deadline_hit_rate: None, total_utility: 0, maximum_task_utility_sum: 0,
        normalized_utility: None, compute_time_used_us: 0, compute_time_wasted_us: 0,
        average_completion_latency_us: None, average_result_age_us: None, simulation_end_us: 0 };
    let mut latency = 0_u128;
    let mut age = 0_u128;
    for task in &scenario.tasks { add(&mut m.maximum_task_utility_sum, task.base_utility.0)?; }
    for event in events {
        m.simulation_end_us = event.sim_time_us.0;
        match &event.kind {
            EventKind::TaskCompleted { utility, deadline_met, execution_cost_us, completion_latency_us, result_age_us, .. } => {
                add(&mut m.tasks_completed, 1)?;
                add(&mut m.deadline_hits, u64::from(*deadline_met == Some(true)))?;
                add(&mut m.total_utility, utility.0)?;
                add(&mut m.compute_time_used_us, execution_cost_us.0)?;
                if utility.0 == 0 { add(&mut m.compute_time_wasted_us, execution_cost_us.0)?; }
                latency = latency.checked_add(u128::from(completion_latency_us.0)).ok_or(MetricsError)?;
                age = age.checked_add(u128::from(result_age_us.0)).ok_or(MetricsError)?;
            }
            EventKind::TaskExpired { .. } => add(&mut m.tasks_expired, 1)?,
            _ => {}
        }
    }
    if m.tasks_completed.checked_add(m.tasks_expired) != Some(m.tasks_total) { return Err(MetricsError); }
    m.deadline_hit_rate = ratio(m.deadline_hits, m.deadline_tasks_total);
    m.normalized_utility = ratio(m.total_utility, m.maximum_task_utility_sum);
    if m.tasks_completed > 0 {
        m.average_completion_latency_us = Some(latency as f64 / m.tasks_completed as f64);
        m.average_result_age_us = Some(age as f64 / m.tasks_completed as f64);
    }
    Ok(m)
}

fn ratio(numerator: u64, denominator: u64) -> Option<f64> {
    (denominator > 0).then(|| numerator as f64 / denominator as f64)
}
