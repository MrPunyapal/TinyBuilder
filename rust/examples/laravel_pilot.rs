//! Lab-only proposal driver for the Laravel benchmark pilot.
use anyhow::{ensure, Context, Result};
use clap::Parser;
use serde::Deserialize;
use serde_json::{json, Value};
use std::{collections::BTreeMap, fs, path::PathBuf, time::Instant};
use tinybuilder::{context, grounded, project::{Project, ReadResult}, runtime::{IncompleteCompletion, Runtime}, workbench};

#[derive(Parser)]
struct Args {
    #[arg(long)] runtime: PathBuf,
    #[arg(long)] model: PathBuf,
    #[arg(long)] jobs: PathBuf,
    /// Replay only the model-selected line arm and emit sanitized failure details.
    #[arg(long)] diagnose_line: bool,
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
    #[serde(default)] compare_v1: bool,
    #[serde(default)] exact_retrieval: bool,
    #[serde(default)] source_ids: bool,
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
    let operator_selected = (job.compare_v1 || job.source_ids) && arm == "C";
    let provided = arm == "A" || ((job.compare_v1 || job.source_ids) && arm == "B") || operator_selected;
    let evidence = if provided {
        let mut files: Vec<_> = job.related.iter().map(|(path,text)| ReadResult {
            path:path.clone(), text:text.clone(), truncated:false
        }).collect();
        files.push(ReadResult {path:job.target.clone(),text:job.source.clone(),truncated:false});
        files.sort_by(|a,b| a.path.cmp(&b.path));
        Ok(files)
    } else if arm == "S" {
        context::retrieve_selective(&project, &job.task).map(|context| context.files)
    } else {
        workbench::collect(&project,&job.task).map(|context| context.files)
    };
    match evidence {
        Err(_) => row["category"] = json!("context_retrieval"),
        Ok(files) => {
            row["event"] = json!(if provided { "provided_source" } else { "retrieved_source" });
            row["evidence_bytes"] = json!(files.iter().map(|f| f.text.len()).sum::<usize>());
            row["evidence_paths"] = json!(files.iter().map(|f| &f.path).collect::<Vec<_>>());
            let has_complete = |path: &str| files.iter().any(|f| f.path == path && !f.truncated);
            if !has_complete(&job.target) || !job.related.keys().all(|path| has_complete(path)) {
                row["category"] = json!("context_retrieval");
            } else {
                let operator_source = if operator_selected {
                    let source = files.iter().find(|file| file.path == job.target).context("Missing selected file")?;
                    row["evidence_bytes"] = json!(source.text.len());
                    row["evidence_paths"] = json!([source.path]);
                    Some(source)
                } else {
                    None
                };
                let mut complete = |request| {
                    row["calls"] = json!(1);
                    row["request_json_bytes"] = json!(serde_json::to_vec(&request)?.len());
                    let completion = runtime.complete_with_usage(request).context("runtime_inference")?;
                    row["prompt_tokens"] = json!(completion.prompt_tokens);
                    row["completion_tokens"] = json!(completion.completion_tokens);
                    Ok(completion.message)
                };
                let result = if let Some(source) = operator_source {
                    grounded::propose_edit_at_line(&project, &job.task, source, job.line, complete)
                } else if job.source_ids && arm == "B" {
                    grounded::source_id_request(&job.task, &files)
                        .and_then(|(request, ids)| ids.prepare(&project, &complete(request)?))
                } else if job.compare_v1 && matches!(arm, "B" | "L" | "S") {
                    grounded::located_line_request(&job.task, &files)
                        .and_then(|request| grounded::prepare_located_line(&project, &files, &complete(request)?))
                } else {
                    grounded::edit_request(&job.task, &files)
                        .and_then(|request| grounded::prepare_edit(&project, &files, &complete(request)?))
                };
                match result {
                    Ok(edit) => {
                        row["category"] = json!("proposal");
                        row["path"] = json!(edit.path);
                        row["preview"] = json!(edit.patch.preview_text());
                    }
                    Err(error) => {
                        let detail = error.to_string();
                        if job.compare_v1 && matches!(arm, "B" | "L" | "S") {
                            row["proposal_detail"] = json!(match detail.as_str() {
                                "Invalid line proposal JSON" => "invalid_json",
                                "Line number was a string" => "line_string",
                                "Line number was absent or invalid" => "line_missing_or_invalid",
                                "Invalid model line proposal" => "invalid_envelope",
                                "Invalid line replacement" => "invalid_replacement",
                                "Patch target not in complete evidence" => "path_not_in_evidence",
                                "Selected line does not exist" => "out_of_range",
                                "Selected line is blank" => "blank_line",
                                "No change" => "no_change",
                                "File changed since context selection" => "stale_source",
                                _ => "other",
                            });
                        }
                        let local = match detail.as_str() {
                            "No change" => "reasoning",
                            "Replacement must match exactly once" => "replacement_match",
                            "Selected line does not exist" | "Selected line is blank" | "Unknown source identifier" => "invalid_location",
                            "Invalid line replacement" if job.source_ids && arm == "B" => "replacement_payload",
                            "Source identifier budget exceeded" => "context_retrieval",
                            "File changed since context selection" => "orchestration",
                            _ => "protocol",
                        };
                        row["category"] = if let Some(incomplete) = error.downcast_ref::<IncompleteCompletion>() {
                            row["finish_reason"] = json!(incomplete.reason);
                            row["prompt_tokens"] = json!(incomplete.prompt_tokens);
                            row["completion_tokens"] = json!(incomplete.completion_tokens);
                            json!(if incomplete.reason == "length" { "output_limit" } else { "incomplete_response" })
                        } else {
                            json!(category(&error, local))
                        };
                    }
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
    ensure!(jobs.iter().all(|job| !job.exact_retrieval || (job.cross_file && !job.compare_v1)),
        "Exact retrieval requires cross-file jobs with the exact-text protocol");
    ensure!(jobs.iter().all(|job| !job.source_ids || (job.cross_file && !job.compare_v1 && !job.exact_retrieval)),
        "Source identifiers require a dedicated cross-file comparison");
    ensure!(!args.diagnose_line || (!jobs.is_empty() && jobs.iter().all(|job| job.compare_v1 && job.cross_file)),
        "The line diagnostic requires Coding Intelligence v1 jobs");
    let start = Instant::now();
    let runtime = Runtime::start(&args.runtime, &args.model)?;
    println!("{}", json!({"ready_ms":start.elapsed().as_millis() as u64}));
    for job in &jobs {
        // Both models have the same order. No retries or interactive changes.
        if job.cross_file {
            let arms: &[&str] = if job.source_ids {
                if job.case == "seat_policy" { &["B", "A", "C"] } else { &["A", "B", "C"] }
            } else { match (args.diagnose_line, job.exact_retrieval, job.compare_v1, job.case.as_str()) {
                (true, _, _, _) => &["B"],
                (false, true, _, "seat_policy") => &["S", "L"],
                (false, true, _, _) => &["L", "S"],
                (false, false, true, "seat_policy") => &["B", "A", "C", "S", "L"],
                (false, false, true, _) => &["A", "B", "C", "L", "S"],
                (false, false, false, "seat_policy") => &["C", "A"],
                (false, false, false, _) => &["A", "C"],
            }};
            for arm in arms {
                let mut row = cross_file_trial(job, arm, &runtime)?;
                if args.diagnose_line {
                    row.as_object_mut().expect("Trial record is an object").remove("preview");
                }
                println!("{row}");
            }
            continue;
        }
        let arms = if job.case == "checkout_discount" { ["D", "C", "B", "A"] } else { ["A", "B", "C", "D"] };
        for arm in arms {
            println!("{}", trial(job, arm, &runtime)?);
        }
    }
    Ok(())
}
