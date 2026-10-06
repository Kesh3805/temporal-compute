use anyhow::{Context, Result, bail};
use clap::{Parser, Subcommand, ValueEnum};
use serde::Serialize;
use std::{
    fs,
    io::{self, Write},
    path::PathBuf,
};
use tc_ir::Scenario;
use tc_scheduler::Policy;
use tc_sim::RunResult;

#[derive(Parser)]
#[command(
    name = "tc",
    version,
    about = "Ostrium Temporal Compute deterministic research simulator"
)]
struct Cli {
    #[command(subcommand)]
    command: Action,
}

#[derive(Subcommand)]
enum Action {
    Simulate {
        scenario: PathBuf,
        #[arg(long, default_value = "temporal-utility")]
        scheduler: Policy,
        #[arg(long, default_value_t = 42)]
        seed: u64,
        #[arg(long, value_enum, default_value_t = Format::Human)]
        format: Format,
        #[arg(long)]
        trace: Option<PathBuf>,
        #[arg(long)]
        output: Option<PathBuf>,
    },
    Compare {
        scenario: PathBuf,
        #[arg(
            long,
            value_delimiter = ',',
            default_value = "fifo,fixed-priority,edf,temporal-utility,temporal-utility-density"
        )]
        schedulers: Vec<Policy>,
        #[arg(long, default_value_t = 42)]
        seed: u64,
        #[arg(long, value_enum, default_value_t = Format::Human)]
        format: Format,
        #[arg(long)]
        output: Option<PathBuf>,
    },
}

#[derive(Clone, Copy, ValueEnum)]
enum Format {
    Human,
    Json,
}

#[derive(Serialize)]
struct Report {
    schema_version: u32,
    git_commit: Option<String>,
    git_dirty: Option<bool>,
    rustc_version: Option<&'static str>,
    scenario_path: String,
    runs: Vec<RunResult>,
}

fn execute() -> Result<()> {
    let (path, policies, seed, format, trace, output) = match Cli::parse().command {
        Action::Simulate {
            scenario,
            scheduler,
            seed,
            format,
            trace,
            output,
        } => (scenario, vec![scheduler], seed, format, trace, output),
        Action::Compare {
            scenario,
            schedulers,
            seed,
            format,
            output,
        } => (scenario, schedulers, seed, format, None, output),
    };
    if policies.is_empty() {
        bail!("at least one scheduler is required");
    }
    let source =
        fs::read_to_string(&path).with_context(|| format!("read scenario {}", path.display()))?;
    let scenario = Scenario::from_toml(&source)
        .with_context(|| format!("validate scenario {}", path.display()))?;
    let mut runs = Vec::new();
    for mut policy in policies {
        runs.push(
            tc_sim::simulate(&scenario, &mut policy, seed)
                .with_context(|| format!("simulate {}", policy.as_str()))?,
        );
    }
    if let Some(path) = trace {
        let file =
            fs::File::create(&path).with_context(|| format!("create trace {}", path.display()))?;
        let mut writer = io::BufWriter::new(file);
        tc_trace::write_jsonl(&mut writer, &runs[0].events).context("serialize trace")?;
        writer.flush().context("flush trace")?;
    }
    let report = Report {
        schema_version: 1,
        git_commit: option_env!("TC_BUILD_GIT_COMMIT").map(str::to_owned),
        git_dirty: option_env!("TC_BUILD_GIT_DIRTY").and_then(|value| value.parse().ok()),
        rustc_version: option_env!("TC_BUILD_RUSTC"),
        scenario_path: path.to_string_lossy().replace('\\', "/"),
        runs,
    };
    let rendered = match format {
        Format::Json => serde_json::to_string_pretty(&report).context("serialize report")?,
        Format::Human => {
            let mut text = format!(
                "{} — seed {} — {}\n\n{:<26} {:>10} {:>10} {:>10} {:>10} {:>12}\n",
                scenario.name,
                seed,
                tc_sim::SIMULATION_VERSION,
                "scheduler",
                "utility",
                "normalized",
                "completed",
                "expired",
                "wasted us"
            );
            for run in &report.runs {
                let m = &run.metrics;
                text.push_str(&format!(
                    "{:<26} {:>10} {:>10} {:>10} {:>10} {:>12}\n",
                    run.scheduler,
                    m.total_utility,
                    m.normalized_utility
                        .map_or_else(|| "n/a".into(), |u| format!("{u:.4}")),
                    m.tasks_completed,
                    m.tasks_expired,
                    m.compute_time_wasted_us
                ));
            }
            text
        }
    };
    if let Some(path) = output {
        fs::write(&path, format!("{rendered}\n"))
            .with_context(|| format!("write report {}", path.display()))?;
    } else {
        writeln!(io::stdout().lock(), "{rendered}").context("write stdout")?;
    }
    Ok(())
}

fn main() {
    if let Err(error) = execute() {
        eprintln!("error: {error:#}");
        std::process::exit(1);
    }
}
