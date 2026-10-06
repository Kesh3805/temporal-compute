use crate::TemporalTask;
use serde::{Deserialize, Serialize};
use tc_core::{SimTime, Utility};

const SCALE: u128 = 1_000_000_000_000;

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum UtilityCurve {
    Constant,
    Linear,
    /// Discrete exponential: retention per interval, truncated integer points.
    Exponential {
        interval_us: u64,
        retention_ppm: u32,
    },
    /// Absolute utility from arrival, updated at inclusive elapsed-time boundaries.
    Step {
        steps: Vec<UtilityStep>,
    },
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct UtilityStep {
    pub after_us: u64,
    pub utility: Utility,
}

impl UtilityCurve {
    pub(crate) fn validate(&self, task: &TemporalTask) -> Result<(), &'static str> {
        match self {
            Self::Linear if task.deadline_us.is_none_or(|d| d <= task.arrival_time_us) => {
                Err("linear decay needs a deadline strictly after arrival")
            }
            Self::Exponential {
                interval_us,
                retention_ppm,
            } if *interval_us == 0 || *retention_ppm > 1_000_000 => {
                Err("exponential interval must be positive; retention must be 0..=1000000")
            }
            Self::Step { steps } => {
                let mut previous = None;
                let mut value = task.base_utility;
                for step in steps {
                    if previous.is_some_and(|p| step.after_us <= p) || step.utility > value {
                        return Err(
                            "steps must have strictly increasing times and nonincreasing utility <= base",
                        );
                    }
                    previous = Some(step.after_us);
                    value = step.utility;
                }
                Ok(())
            }
            _ => Ok(()),
        }
    }

    pub(crate) fn evaluate(&self, task: &TemporalTask, at: SimTime) -> Utility {
        let age = at.0 - task.arrival_time_us.0;
        let base = u128::from(task.base_utility.0);
        match self {
            Self::Constant => task.base_utility,
            Self::Linear => {
                // Invalid public task definitions still evaluate safely; simulator validates first.
                let Some(deadline) = task.deadline_us else {
                    return Utility(0);
                };
                let span = deadline.0.saturating_sub(task.arrival_time_us.0);
                if span == 0 {
                    return Utility(0);
                }
                Utility(
                    (base * u128::from(deadline.0.saturating_sub(at.0)) / u128::from(span)) as u64,
                )
            }
            Self::Exponential {
                interval_us,
                retention_ppm,
            } => {
                if *interval_us == 0 || *retention_ppm > 1_000_000 {
                    return Utility(0);
                }
                let mut exponent = age / interval_us;
                let mut factor = u128::from(*retention_ppm) * SCALE / 1_000_000;
                let mut retained = SCALE;
                // Fixed-point exponentiation by squaring avoids libm/platform variation.
                while exponent > 0 {
                    if exponent & 1 == 1 {
                        retained = retained * factor / SCALE;
                    }
                    factor = factor * factor / SCALE;
                    exponent >>= 1;
                }
                Utility((base * retained / SCALE) as u64)
            }
            Self::Step { steps } => steps
                .iter()
                .rev()
                .find(|s| s.after_us <= age)
                .map_or(task.base_utility, |s| s.utility),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tc_core::{Duration, Priority, TaskId};
    fn task(curve: UtilityCurve) -> TemporalTask {
        TemporalTask {
            id: TaskId("t".into()),
            arrival_time_us: SimTime(10),
            execution_cost_us: Duration(1),
            deadline_us: Some(SimTime(110)),
            priority: Priority(0),
            base_utility: Utility(100),
            utility: curve,
            fresh_until_us: None,
            input_time_us: None,
        }
    }
    #[test]
    fn boundaries_and_freshness() {
        let mut t = task(UtilityCurve::Constant);
        assert_eq!(t.utility_at(SimTime(9)), Utility(0));
        assert_eq!(t.utility_at(SimTime(110)), Utility(100));
        assert_eq!(t.utility_at(SimTime(111)), Utility(0));
        t.fresh_until_us = Some(SimTime(50));
        assert_eq!(t.utility_at(SimTime(50)), Utility(100));
        assert_eq!(t.utility_at(SimTime(51)), Utility(0));
        t.fresh_until_us = None;
        t.utility = UtilityCurve::Linear;
        assert_eq!(t.utility_at(SimTime(10)), Utility(100));
        assert_eq!(t.utility_at(SimTime(60)), Utility(50));
        assert_eq!(t.utility_at(SimTime(110)), Utility(0));
        t.utility = UtilityCurve::Exponential {
            interval_us: 10,
            retention_ppm: 500_000,
        };
        assert_eq!(t.utility_at(SimTime(19)), Utility(100));
        assert_eq!(t.utility_at(SimTime(20)), Utility(50));
        assert_eq!(t.utility_at(SimTime(30)), Utility(25));
        t.utility = UtilityCurve::Step {
            steps: vec![UtilityStep {
                after_us: 20,
                utility: Utility(7),
            }],
        };
        assert_eq!(t.utility_at(SimTime(29)), Utility(100));
        assert_eq!(t.utility_at(SimTime(30)), Utility(7));
    }
    #[test]
    fn all_curves_are_bounded_and_nonincreasing() {
        // Exhaustive finite-domain property test, including quantization boundaries.
        for base in [0, 1, 101, 10_000, u32::MAX as u64] {
            for curve in [
                UtilityCurve::Constant,
                UtilityCurve::Linear,
                UtilityCurve::Exponential {
                    interval_us: 3,
                    retention_ppm: 923_456,
                },
                UtilityCurve::Step {
                    steps: vec![UtilityStep {
                        after_us: 17,
                        utility: Utility(0),
                    }],
                },
            ] {
                let mut t = task(curve);
                t.base_utility = Utility(base);
                let mut previous = Utility(base);
                for time in 10..=112 {
                    let value = t.utility_at(SimTime(time));
                    assert!(value <= previous && value <= Utility(base));
                    previous = value;
                }
            }
        }
    }
}
