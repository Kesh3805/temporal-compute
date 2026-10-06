use crate::{Configuration, RunResult, SIMULATION_VERSION, SimulationError};
use tc_core::{Duration, SimTime};
use tc_ir::Scenario;
use tc_scheduler::{Scheduler, SchedulingContext};
use tc_trace::{Candidate, Event, EventKind, ExpiryReason, TRACE_SCHEMA_VERSION};

#[derive(Clone, Copy, PartialEq, Eq)]
enum State {
    Pending,
    Waiting,
    Running,
    Completed,
    Expired,
}

struct Engine<'a> {
    scenario: &'a Scenario,
    scheduler: String,
    states: Vec<State>,
    events: Vec<Event>,
    now: SimTime,
}

impl Engine<'_> {
    fn emit(&mut self, kind: EventKind) {
        self.events.push(Event {
            schema_version: TRACE_SCHEMA_VERSION,
            sequence: self.events.len() as u64,
            sim_time_us: self.now,
            scheduler: self.scheduler.clone(),
            kind,
        });
    }

    fn next_external(&self) -> Option<SimTime> {
        self.scenario
            .tasks
            .iter()
            .zip(&self.states)
            .filter_map(|(t, state)| match state {
                State::Pending => Some(t.arrival_time_us),
                State::Waiting => t
                    .expiry_limit()
                    .and_then(|limit| limit.0.checked_add(1).map(SimTime)),
                _ => None,
            })
            .min()
    }

    fn process_external(&mut self) {
        // Canonical ID order: arrivals first, then expirations at equal timestamps.
        let mut indices: Vec<_> = (0..self.states.len()).collect();
        indices.sort_by_key(|&i| &self.scenario.tasks[i].id);
        for &i in &indices {
            let task = &self.scenario.tasks[i];
            if self.states[i] == State::Pending && task.arrival_time_us == self.now {
                self.states[i] = State::Waiting;
                self.emit(EventKind::TaskArrived {
                    task_id: task.id.clone(),
                });
            }
        }
        for i in indices {
            let task = &self.scenario.tasks[i];
            if self.states[i] == State::Waiting && task.expiry_limit().is_some_and(|t| self.now > t)
            {
                let reason = if task.deadline_us == task.expiry_limit() {
                    ExpiryReason::Deadline
                } else {
                    ExpiryReason::Freshness
                };
                self.states[i] = State::Expired;
                self.emit(EventKind::TaskExpired {
                    task_id: task.id.clone(),
                    reason,
                });
            }
        }
    }

    fn advance_to(&mut self, target: SimTime) {
        while let Some(next) = self.next_external().filter(|t| *t <= target) {
            self.now = next;
            self.process_external();
        }
        self.now = target;
    }
}

pub fn simulate(
    scenario: &Scenario,
    scheduler: &mut impl Scheduler,
    seed: u64,
) -> Result<RunResult, SimulationError> {
    scenario.validate()?;
    let mut engine = Engine {
        scenario,
        scheduler: scheduler.name().to_owned(),
        states: vec![State::Pending; scenario.tasks.len()],
        events: Vec::new(),
        now: SimTime(0),
    };
    engine.emit(EventKind::SimulationStarted {
        scenario: scenario.name.clone(),
        seed,
    });
    engine.process_external();
    loop {
        let mut indices: Vec<_> = engine
            .states
            .iter()
            .enumerate()
            .filter_map(|(i, s)| (*s == State::Waiting).then_some(i))
            .collect();
        indices.sort_by_key(|&i| &scenario.tasks[i].id);
        if indices.is_empty() {
            if let Some(next) = engine.next_external() {
                engine.advance_to(next);
                continue;
            }
            break;
        }
        let runnable: Vec<_> = indices.iter().map(|&i| &scenario.tasks[i]).collect();
        let selected = scheduler
            .select_next(&SchedulingContext { now: engine.now }, &runnable)
            .ok_or_else(|| SimulationError::Scheduler("declined a nonempty runnable set".into()))?;
        let index = indices
            .iter()
            .copied()
            .find(|&i| scenario.tasks[i].id == selected)
            .ok_or_else(|| {
                SimulationError::Scheduler(format!("selected non-runnable task {}", selected.0))
            })?;
        let mut candidates = Vec::with_capacity(runnable.len());
        for task in runnable {
            let completion = engine.now.checked_add(task.execution_cost_us)?;
            candidates.push(Candidate {
                task_id: task.id.clone(),
                predicted_completion_us: completion,
                predicted_utility: task.utility_at(completion),
                execution_cost_us: task.execution_cost_us,
            });
        }
        engine.emit(EventKind::SchedulerDecision {
            selected,
            candidates,
        });
        let task = &scenario.tasks[index];
        let completion = engine.now.checked_add(task.execution_cost_us)?;
        engine.states[index] = State::Running;
        engine.emit(EventKind::TaskStarted {
            task_id: task.id.clone(),
            predicted_completion_us: completion,
            predicted_utility: task.utility_at(completion),
        });
        engine.advance_to(completion);
        engine.states[index] = State::Completed;
        engine.emit(EventKind::TaskCompleted {
            task_id: task.id.clone(),
            utility: task.utility_at(completion),
            deadline_met: task.deadline_us.map(|d| completion <= d),
            fresh: task.fresh_until_us.is_none_or(|d| completion <= d),
            execution_cost_us: task.execution_cost_us,
            completion_latency_us: Duration(completion.0 - task.arrival_time_us.0),
            result_age_us: Duration(completion.0 - task.input_time().0),
        });
    }
    engine.emit(EventKind::SimulationCompleted);
    let metrics = tc_metrics::reduce(scenario, &engine.events)?;
    Ok(RunResult {
        schema_version: 1,
        simulation_version: SIMULATION_VERSION.into(),
        scenario: scenario.clone(),
        scheduler: engine.scheduler,
        seed,
        configuration: Configuration::default(),
        metrics,
        events: engine.events,
    })
}
