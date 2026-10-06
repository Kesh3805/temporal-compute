//! Evaluation-only batch adapter. Existing runtime/policy source remains unchanged.
use anyhow::{Context, Result, bail};
use serde::Deserialize;
use std::io::{self, BufRead, Write};
use tc_core::TaskId;
use tc_ir::{Scenario, TemporalTask};
use tc_scheduler::{Policy, Scheduler, SchedulingContext};

struct EdfPriority;

impl Scheduler for EdfPriority {
    fn name(&self) -> &str {
        "edf-priority"
    }
    fn select_next(&mut self, _: &SchedulingContext, runnable: &[&TemporalTask]) -> Option<TaskId> {
        runnable
            .iter()
            .min_by(|a, b| {
                (a.deadline_us.is_none(), a.deadline_us)
                    .cmp(&(b.deadline_us.is_none(), b.deadline_us))
                    .then_with(|| b.priority.cmp(&a.priority))
                    .then_with(|| a.arrival_time_us.cmp(&b.arrival_time_us))
                    .then_with(|| a.id.cmp(&b.id))
            })
            .map(|t| t.id.clone())
    }
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Request {
    scenario: Scenario,
    seed: u64,
    schedulers: Vec<String>,
}

fn write_run(
    scenario: &Scenario,
    scheduler: &mut impl Scheduler,
    seed: u64,
    writer: &mut impl Write,
) -> Result<()> {
    let first = tc_sim::simulate(scenario, scheduler, seed)?;
    let second = tc_sim::simulate(scenario, scheduler, seed)?;
    if first != second {
        bail!("replay mismatch: {} {}", scenario.name, scheduler.name());
    }
    serde_json::to_writer(&mut *writer, &first).context("encode complete run")?;
    writer.write_all(b"\n").context("write run newline")?;
    Ok(())
}

fn execute() -> Result<()> {
    let mode = std::env::args()
        .nth(1)
        .context("mode required: validate or evaluate")?;
    if mode != "validate" && mode != "evaluate" {
        bail!("unknown batch mode {mode}");
    }
    let mut output = io::BufWriter::new(io::stdout().lock());
    for (i, line) in io::stdin().lock().lines().enumerate() {
        let line = line.with_context(|| format!("read input line {}", i + 1))?;
        let request: Request =
            serde_json::from_str(&line).with_context(|| format!("parse line {}", i + 1))?;
        request
            .scenario
            .validate()
            .with_context(|| format!("validate {}", request.scenario.name))?;
        if mode == "validate" {
            // This branch does not invoke any scheduler or simulation function.
            writeln!(output, "{}", request.scenario.name)?;
            continue;
        }
        for name in request.schedulers {
            if name == "edf-priority" {
                write_run(
                    &request.scenario,
                    &mut EdfPriority,
                    request.seed,
                    &mut output,
                )?;
            } else {
                let mut policy: Policy = name.parse().map_err(anyhow::Error::msg)?;
                write_run(&request.scenario, &mut policy, request.seed, &mut output)?;
            }
        }
    }
    output.flush().context("flush batch output")
}

fn main() {
    if let Err(error) = execute() {
        eprintln!("error: {error:#}");
        std::process::exit(1);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn equal_deadlines_prefer_mission_priority() {
        let source = r#"{"schema_version":1,"name":"unit-only","description":"not EO corpus","tasks":[{"id":"a","arrival_time_us":0,"execution_cost_us":1,"deadline_us":10,"priority":0,"base_utility":1,"utility":{"kind":"constant"}},{"id":"b","arrival_time_us":0,"execution_cost_us":1,"deadline_us":10,"priority":5,"base_utility":1,"utility":{"kind":"constant"}}]}"#;
        let s: Scenario = serde_json::from_str(source).unwrap();
        assert_eq!(
            EdfPriority.select_next(
                &SchedulingContext {
                    now: tc_core::SimTime(0)
                },
                &[&s.tasks[0], &s.tasks[1]]
            ),
            Some(TaskId("b".into()))
        );
    }
}
