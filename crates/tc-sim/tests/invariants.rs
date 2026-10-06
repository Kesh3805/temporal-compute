use std::collections::{BTreeMap, BTreeSet};
use tc_core::{Duration, Priority, SimTime, TaskId, Utility};
use tc_ir::{Scenario, TemporalTask, UtilityCurve};
use tc_scheduler::{Policy, Scheduler, SchedulingContext};
use tc_sim::simulate;
use tc_trace::EventKind;

const FIXTURES: [&str; 7] = [
    "tc0-basic",
    "deadline-pressure",
    "temporal-decay",
    "freshness-decay",
    "mixed-utility",
    "fifo-equivalent",
    "density-trap",
];

fn fixture(name: &str) -> Scenario {
    let path = format!(
        "{}/../../scenarios/{name}/scenario.toml",
        env!("CARGO_MANIFEST_DIR")
    );
    Scenario::from_toml(&std::fs::read_to_string(path).unwrap()).unwrap()
}

#[test]
fn replay_and_invariants_for_every_fixture_and_policy() {
    for name in FIXTURES {
        let scenario = fixture(name);
        for mut policy in Policy::ALL {
            let first = simulate(&scenario, &mut policy, 42).unwrap();
            let second = simulate(&scenario, &mut policy, 42).unwrap();
            assert_eq!(first, second, "{name} {}", policy.as_str());
            let mut starts = BTreeMap::new();
            let mut terminal = BTreeSet::new();
            let mut now = SimTime(0);
            let mut active = None;
            let mut compute = 0;
            let mut wasted = 0;
            let mut total_utility = 0;
            let mut completed = 0;
            let mut expired = 0;
            for (sequence, event) in first.events.iter().enumerate() {
                assert_eq!(event.sequence, sequence as u64);
                assert!(event.sim_time_us >= now);
                now = event.sim_time_us;
                match &event.kind {
                    EventKind::TaskStarted {
                        task_id,
                        predicted_completion_us,
                        ..
                    } => {
                        let task = scenario.tasks.iter().find(|t| t.id == *task_id).unwrap();
                        assert!(now >= task.arrival_time_us);
                        assert_eq!(
                            *predicted_completion_us,
                            now.checked_add(task.execution_cost_us).unwrap()
                        );
                        assert!(active.is_none());
                        active = Some(task_id.clone());
                        assert!(starts.insert(task_id.clone(), now).is_none());
                        assert!(!terminal.contains(task_id));
                    }
                    EventKind::TaskCompleted {
                        task_id,
                        execution_cost_us,
                        utility,
                        ..
                    } => {
                        assert_eq!(active.take(), Some(task_id.clone()));
                        assert_eq!(now.elapsed_since(starts[task_id]), Some(*execution_cost_us));
                        let task = scenario.tasks.iter().find(|t| t.id == *task_id).unwrap();
                        assert_eq!(*utility, task.utility_at(now));
                        assert!(terminal.insert(task_id.clone()));
                        compute += execution_cost_us.0;
                        if utility.0 == 0 {
                            wasted += execution_cost_us.0;
                        }
                        total_utility += utility.0;
                        completed += 1;
                    }
                    EventKind::TaskExpired { task_id, .. } => {
                        assert_ne!(active.as_ref(), Some(task_id));
                        assert!(terminal.insert(task_id.clone()));
                        assert!(!starts.contains_key(task_id));
                        expired += 1;
                    }
                    _ => {}
                }
            }
            assert_eq!(terminal.len(), scenario.tasks.len());
            assert_eq!(first.metrics.tasks_completed, completed);
            assert_eq!(first.metrics.tasks_expired, expired);
            assert_eq!(first.metrics.compute_time_used_us, compute);
            assert_eq!(first.metrics.compute_time_wasted_us, wasted);
            assert_eq!(first.metrics.total_utility, total_utility);
            assert_eq!(
                first.metrics,
                tc_metrics::reduce(&scenario, &first.events).unwrap()
            );
            assert!(
                first
                    .metrics
                    .normalized_utility
                    .is_none_or(|u| (0.0..=1.0).contains(&u))
            );
        }
    }
}

#[test]
fn controls_expose_greedy_weaknesses_and_ties() {
    let s = fixture("deadline-pressure");
    assert!(
        simulate(&s, &mut Policy::Edf, 42)
            .unwrap()
            .metrics
            .total_utility
            > simulate(&s, &mut Policy::TemporalUtility, 42)
                .unwrap()
                .metrics
                .total_utility
    );
    let s = fixture("density-trap");
    assert!(
        simulate(&s, &mut Policy::TemporalUtility, 42)
            .unwrap()
            .metrics
            .total_utility
            > simulate(&s, &mut Policy::TemporalUtilityDensity, 42)
                .unwrap()
                .metrics
                .total_utility
    );
    let s = fixture("fifo-equivalent");
    let reference = simulate(&s, &mut Policy::Fifo, 42).unwrap().metrics;
    for mut policy in Policy::ALL {
        assert_eq!(simulate(&s, &mut policy, 42).unwrap().metrics, reference);
    }
}

fn single(arrival: u64, cost: u64, deadline: Option<u64>) -> Scenario {
    Scenario {
        schema_version: 1,
        name: "single".into(),
        description: "boundary".into(),
        tasks: vec![TemporalTask {
            id: TaskId("a".into()),
            arrival_time_us: SimTime(arrival),
            execution_cost_us: Duration(cost),
            deadline_us: deadline.map(SimTime),
            priority: Priority(0),
            base_utility: Utility(10),
            utility: UtilityCurve::Constant,
            fresh_until_us: None,
            input_time_us: None,
        }],
    }
}

#[test]
fn boundary_completion_and_zero_value_waste() {
    let on_time = simulate(&single(0, 5, Some(5)), &mut Policy::Fifo, 1).unwrap();
    assert_eq!(on_time.metrics.deadline_hit_rate, Some(1.0));
    let late = simulate(&single(0, 6, Some(5)), &mut Policy::Fifo, 1).unwrap();
    assert_eq!(late.metrics.tasks_completed, 1);
    assert_eq!(late.metrics.tasks_expired, 0);
    assert_eq!(late.metrics.compute_time_wasted_us, 6);
    assert_eq!(late.metrics.deadline_hit_rate, Some(0.0));
}

#[test]
fn validates_overflow_invalid_curves_duplicates_and_zero_cost() {
    for s in [
        single(u64::MAX, 1, None),
        single(0, 0, None),
        single(10, 1, Some(9)),
    ] {
        assert!(simulate(&s, &mut Policy::Fifo, 0).is_err());
    }
    let mut s = single(0, 1, None);
    s.tasks.push(s.tasks[0].clone());
    assert!(s.validate().is_err());
    s.tasks.pop();
    s.tasks[0].utility = UtilityCurve::Linear;
    assert!(s.validate().is_err());
    s.tasks[0].utility = UtilityCurve::Exponential {
        interval_us: 0,
        retention_ppm: 500_000,
    };
    assert!(s.validate().is_err());
}

#[test]
fn empty_workload_and_near_max_time() {
    let mut empty = single(0, 1, None);
    empty.tasks.clear();
    let run = simulate(&empty, &mut Policy::Edf, 0).unwrap();
    assert_eq!(run.events.len(), 2);
    assert_eq!(run.metrics.normalized_utility, None);
    let run = simulate(
        &single(u64::MAX - 1, 1, Some(u64::MAX)),
        &mut Policy::Fifo,
        0,
    )
    .unwrap();
    assert_eq!(run.metrics.simulation_end_us, u64::MAX);
}

struct InvalidScheduler;
impl Scheduler for InvalidScheduler {
    fn name(&self) -> &str {
        "invalid"
    }
    fn select_next(&mut self, _: &SchedulingContext, _: &[&TemporalTask]) -> Option<TaskId> {
        Some(TaskId("missing".into()))
    }
}

#[test]
fn scheduler_contract_is_enforced() {
    assert!(simulate(&single(0, 1, None), &mut InvalidScheduler, 0).is_err());
}

#[test]
fn permutations_do_not_change_event_stream_or_metrics() {
    let mut s = fixture("mixed-utility");
    let before = simulate(&s, &mut Policy::TemporalUtilityDensity, 42).unwrap();
    s.tasks.reverse();
    let after = simulate(&s, &mut Policy::TemporalUtilityDensity, 42).unwrap();
    assert_eq!(before.events, after.events);
    assert_eq!(before.metrics, after.metrics);
}
