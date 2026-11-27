//! Model-free lab retrieval probe. No target paths, fixture answers or runtime.
use anyhow::Result;
use clap::Parser;
use serde_json::json;
use std::{path::PathBuf, time::Instant};
use tinybuilder::{context::{retrieve_lab, LabRetrieval}, project::Project};

#[derive(Parser)]
struct Args {
    #[arg(long)]
    project: PathBuf,
    #[arg(long, value_enum)]
    strategy: LabRetrieval,
    task: String,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let project = Project::new(&args.project)?;
    let mut rows = Vec::new();
    for _ in 0..3 {
        let start = Instant::now();
        let result = retrieve_lab(&project, &args.task, args.strategy);
        let elapsed_us = start.elapsed().as_micros() as u64;
        rows.push(match result {
            Ok(context) => json!({
                "status": "selected", "elapsed_us": elapsed_us, "incomplete": context.incomplete,
                "files": context.files.iter().map(|file| json!({
                    "path": file.path, "complete": !file.truncated, "bytes": file.text.len()
                })).collect::<Vec<_>>()
            }),
            Err(_) => json!({"status": "no_context", "elapsed_us": elapsed_us, "files": []}),
        });
    }
    println!("{}", json!(rows));
    Ok(())
}
