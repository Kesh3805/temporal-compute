//! Stateless, deterministic baseline and greedy temporal policies.
use serde::{Deserialize, Serialize};
use std::{cmp::Ordering, str::FromStr};
use tc_core::{SimTime, TaskId, Utility};
use tc_ir::TemporalTask;

#[derive(Debug, Clone, Copy)]
pub struct SchedulingContext {
    pub now: SimTime,
}

pub trait Scheduler {
    fn name(&self) -> &str;
    fn select_next(
        &mut self,
        context: &SchedulingContext,
        runnable: &[&TemporalTask],
    ) -> Option<TaskId>;
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum Policy {
    Fifo,
    FixedPriority,
    Edf,
    TemporalUtility,
    TemporalUtilityDensity,
}

impl Policy {
    pub const ALL: [Self; 5] = [
        Self::Fifo,
        Self::FixedPriority,
        Self::Edf,
        Self::TemporalUtility,
        Self::TemporalUtilityDensity,
    ];

    pub fn as_str(self) -> &'static str {
        match self {
            Self::Fifo => "fifo",
            Self::FixedPriority => "fixed-priority",
            Self::Edf => "edf",
            Self::TemporalUtility => "temporal-utility",
            Self::TemporalUtilityDensity => "temporal-utility-density",
        }
    }

    pub fn predicted_utility(task: &TemporalTask, now: SimTime) -> Utility {
        now.checked_add(task.execution_cost_us)
            .map_or(Utility(0), |at| task.utility_at(at))
    }

    fn compare(self, a: &TemporalTask, b: &TemporalTask, now: SimTime) -> Ordering {
        let rank = match self {
            Self::Fifo => Ordering::Equal,
            Self::FixedPriority => b.priority.cmp(&a.priority),
            Self::Edf => a
                .deadline_us
                .unwrap_or(SimTime(u64::MAX))
                .cmp(&b.deadline_us.unwrap_or(SimTime(u64::MAX))),
            Self::TemporalUtility => {
                Self::predicted_utility(b, now).cmp(&Self::predicted_utility(a, now))
            }
            Self::TemporalUtilityDensity => {
                let left = u128::from(Self::predicted_utility(a, now).0)
                    * u128::from(b.execution_cost_us.0);
                let right = u128::from(Self::predicted_utility(b, now).0)
                    * u128::from(a.execution_cost_us.0);
                right.cmp(&left)
            }
        };
        rank.then_with(|| a.arrival_time_us.cmp(&b.arrival_time_us))
            .then_with(|| a.id.cmp(&b.id))
    }
}

impl FromStr for Policy {
    type Err = String;
    fn from_str(value: &str) -> Result<Self, Self::Err> {
        Self::ALL
            .into_iter()
            .find(|p| p.as_str() == value)
            .ok_or_else(|| {
                format!(
                    "unknown scheduler '{value}'; choose {}",
                    Self::ALL.map(Self::as_str).join(", ")
                )
            })
    }
}

impl Scheduler for Policy {
    fn name(&self) -> &str {
        self.as_str()
    }
    fn select_next(
        &mut self,
        context: &SchedulingContext,
        runnable: &[&TemporalTask],
    ) -> Option<TaskId> {
        runnable
            .iter()
            .min_by(|a, b| self.compare(a, b, context.now))
            .map(|t| t.id.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tc_core::{Duration, Priority};
    use tc_ir::UtilityCurve;
    fn task(id: &str, cost: u64, value: u64) -> TemporalTask {
        TemporalTask {
            id: TaskId(id.into()),
            arrival_time_us: SimTime(0),
            execution_cost_us: Duration(cost),
            deadline_us: None,
            priority: Priority(0),
            base_utility: Utility(value),
            utility: UtilityCurve::Constant,
            fresh_until_us: None,
            input_time_us: None,
        }
    }
    #[test]
    fn ties_do_not_depend_on_input_order() {
        let a = task("a", 1, 2);
        let b = task("b", 1, 2);
        for mut policy in Policy::ALL {
            assert_eq!(
                policy.select_next(&SchedulingContext { now: SimTime(0) }, &[&b, &a]),
                Some(a.id.clone())
            );
        }
    }
    #[test]
    fn absolute_and_density_are_distinct_and_edf_handles_no_deadline() {
        let a = task("a", 10, 100);
        let mut b = task("b", 1, 20);
        b.deadline_us = Some(SimTime(20));
        let context = SchedulingContext { now: SimTime(0) };
        assert_eq!(
            Policy::TemporalUtility.select_next(&context, &[&a, &b]),
            Some(a.id.clone())
        );
        assert_eq!(
            Policy::TemporalUtilityDensity.select_next(&context, &[&a, &b]),
            Some(b.id.clone())
        );
        assert_eq!(
            Policy::Edf.select_next(&context, &[&a, &b]),
            Some(b.id.clone())
        );
    }
}
