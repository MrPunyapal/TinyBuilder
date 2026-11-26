//! Lab-only proposal driver for the Laravel benchmark pilot.
use anyhow::{ensure, Context, Result};
use clap::Parser;
use serde::Deserialize;
use serde_json::{json, Value};
use std::{collections::BTreeMap, fs, path::PathBuf, time::Instant};
use tinybuilder::{grounded, project::{Project, ReadResult}, runtime::Runtime, workbench};

#[derive(Parser)]
struct Args {
    #[arg(long)] runtime: PathBuf,
    #[arg(long)] model: PathBuf,
    #[arg(long)] jobs: PathBuf,
}

#[derive(Deserialize)]
struct Job {
    case: String,
    project: PathBuf,
    task: String,
    target: String,
    line: usize,
    source: String,
    #[serde(default)] cross_file: bool,
    #[serde(default)] related: BTreeMap<String, String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ReadAction {
    #[serde(rename = "type")]
    kind: String,
    path: String,
}

fn select(project: &Project, job: &Job, runtime: &Runtime) -> Result<ReadResult> {
    let files = project.list("app/Pilot")?;
    let paths: Vec<_> = files.lines().filter(|path| path.ends_with(".php")).collect();
    ensure!(!paths.is_empty(), "No selectable files");
    let mut request = grounded::selection_request(&job.task, "Choose one file from the following list");
    request["messages"][1]["content"] = json!(format!(
        "Task: {}\nCandidate paths:\n{}\nSelect exactly one project-relative file to read.",
        job.task, paths.join("\n")
    ));
    let response = runtime.complete(request).context("runtime_inference")?;
    let raw = response["content"].as_str().context("Missing selection content")?;
    let action: ReadAction = serde_json::from_str(raw)?;
    ensure!(action.kind == "read" && paths.contains(&action.path.as_str()), "Invalid read action");
    project.read(&action.path)
}

fn category(error: &anyhow::Error, default: &str) -> String {
    for cause in error.chain() {
        if let Some(io) = cause.downcast_ref::<std::io::Error>() {
            if matches!(io.kind(), std::io::ErrorKind::TimedOut | std::io::ErrorKind::WouldBlock) {
                return "timeout".into();
            }
        }
    }
    if error.chain().any(|cause| cause.to_string() == "runtime_inference") {
        return "runtime".into();
    }
    default.into()
}

// Compare sufficient supplied context with genuine bounded retrieval. Neither
// request receives the evaluator's target path or selected line as a hint.
fn cross_file_trial(job: &Job, arm: &str, runtime: &Runtime) -> Result<Value> {
    let project = Project::new(&job.project)?;
    let start = Instant::now();
    let mut row = json!({"case":job.case,"arm":arm,"calls":0});
    let evidence = if arm == "A" {
        let mut files: Vec<_> = job.related.iter().map(|(path,text)| ReadResult {
            path:path.clone(), text:text.clone(), truncated:false
        }).collect();
        files.push(ReadResult {path:job.target.clone(),text:job.source.clone(),truncated:false});
        files.sort_by(|a,b| a.path.cmp(&b.path));
        Ok(files)
    } else {
        workbench::collect(&project,&job.task).map(|context| context.files)
    };
    match evidence {
        Err(_) => row["category"] = json!("context_retrieval"),
        Ok(files) => {
            row["event"] = json!(if arm == "A" { "provided_source" } else { "retrieved_source" });
            row["evidence_bytes"] = json!(files.iter().map(|f| f.text.len()).sum::<usize>());
            row["evidence_paths"] = json!(files.iter().map(|f| &f.path).collect::<Vec<_>>());
            let has_complete = |path: &str| files.iter().any(|f| f.path == path && !f.truncated);
            if !has_complete(&job.target) || !job.related.keys().all(|path| has_complete(path)) {
                row["category"] = json!("context_retrieval");
            } else {
                let result = grounded::edit_request(&job.task,&files).and_then(|request| {
                    row["calls"] = json!(1);
                    let message = runtime.complete(request).context("runtime_inference")?;
                    grounded::prepare_edit(&project,&files,&message)
                });
                match result {
                    Ok(edit) => {
                        row["category"] = json!("proposal");
                        row["path"] = json!(edit.path);
                        row["preview"] = json!(edit.patch.preview_text());
                    }
                    Err(error) => row["category"] = json!(category(&error, if error.to_string()=="No change" {
                        "reasoning"
                    } else { "protocol" })),
                }
            }
        }
    }
    row["latency_ms"] = json!(start.elapsed().as_millis() as u64);
    Ok(row)
}

fn trial(job: &Job, arm: &str, runtime: &Runtime) -> Result<Value> {
    let project = Project::new(&job.project)?;
    let start = Instant::now();
    let mut calls = 0;
    let quality = match arm {
        "A" => Ok(ReadResult { path: job.target.clone(), text: job.source.clone(), truncated: false }),
        "B" => project.read(&job.target),
        "C" => workbench::collect(&project, &job.task).and_then(|context| {
            context.files.into_iter().next().context("Empty context")
        }),
        "D" => { calls += 1; select(&project, job, runtime) }
        _ => unreachable!(),
    };
    let mut row = json!({"case":job.case,"arm":arm});
    match quality {
        Err(error) => row["category"] = json!(category(&error, if arm == "D" { "protocol" } else { "context_retrieval" })),
        Ok(read) => {
            row["evidence_bytes"] = json!(read.text.len());
            row["event"] = json!(match arm { "A" => "provided_source", "B" => "known_path_read",
                "C" => "retrieved_source", _ => "model_selected_read" });
            if read.path != job.target || read.truncated {
                row["category"] = json!("context_retrieval");
            } else {
                let proposed = grounded::propose_edit_at_line(&project, &job.task, &read, job.line, |request| {
                    calls += 1;
                    runtime.complete(request).context("runtime_inference")
                });
                match proposed {
                    Ok(edit) => {
                        row["category"] = json!("proposal");
                        row["preview"] = json!(edit.patch.preview_text());
                    }
                    Err(error) => row["category"] = json!(category(&error, if error.to_string()=="No change" {
                        "reasoning"
                    } else {
                        "protocol"
                    })),
                }
            }
        }
    }
    row["calls"] = json!(calls);
    row["latency_ms"] = json!(start.elapsed().as_millis() as u64);
    Ok(row)
}

fn main() -> Result<()> {
    let args = Args::parse();
    let jobs: Vec<Job> = serde_json::from_slice(&fs::read(args.jobs)?)?;
    let start = Instant::now();
    let runtime = Runtime::start(&args.runtime, &args.model)?;
    println!("{}", json!({"ready_ms":start.elapsed().as_millis() as u64}));
    for job in &jobs {
        // Both models have the same order. No retries or interactive changes.
        if job.cross_file {
            let arms = if job.case == "seat_policy" { ["C", "A"] } else { ["A", "C"] };
            for arm in arms { println!("{}", cross_file_trial(job, arm, &runtime)?); }
            continue;
        }
        let arms = if job.case == "checkout_discount" { ["D", "C", "B", "A"] } else { ["A", "B", "C", "D"] };
        for arm in arms {
            println!("{}", trial(job, arm, &runtime)?);
        }
    }
    Ok(())
}
