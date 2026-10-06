//! Integer microsecond time and integer utility points, with checked arithmetic.
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
#[error("simulated time overflow")]
pub struct TimeOverflow;

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(transparent)]
pub struct SimTime(pub u64);

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Duration(pub u64);

impl SimTime {
    pub fn checked_add(self, duration: Duration) -> Result<Self, TimeOverflow> {
        self.0.checked_add(duration.0).map(Self).ok_or(TimeOverflow)
    }

    pub fn elapsed_since(self, earlier: Self) -> Option<Duration> {
        self.0.checked_sub(earlier.0).map(Duration)
    }
}

#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(transparent)]
pub struct TaskId(pub String);

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Utility(pub u64);

#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, PartialOrd, Ord, Serialize, Deserialize)]
#[serde(transparent)]
pub struct Priority(pub i32);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn time_is_checked_and_cannot_be_negative() {
        assert_eq!(
            SimTime(u64::MAX).checked_add(Duration(1)),
            Err(TimeOverflow)
        );
        assert_eq!(SimTime(3).elapsed_since(SimTime(4)), None);
        assert_eq!(SimTime(4).elapsed_since(SimTime(3)), Some(Duration(1)));
    }
}
