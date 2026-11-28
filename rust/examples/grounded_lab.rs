//! Experimental context-first natural language read/patch workbench.
use anyhow::{ensure, Result};
use clap::{Parser, Subcommand};
use serde_json::{json, Value};
use std::{io::{self,Write}, path::PathBuf, time::Instant};
use tinybuilder::{context::{retrieve_lab, LabRetrieval}, workbench, project::Project, runtime::Runtime, show, terminal};

#[derive(Parser)]
struct Cli {
    #[arg(long)] project: PathBuf,
    #[arg(long)] runtime: PathBuf,
    #[arg(long)] model: PathBuf,
    #[command(subcommand)] command: Action,
}
#[derive(Subcommand)]
enum Action {
    Ask { task: String },
    Edit {
        task: String,
        #[arg(long)] allow_write: bool,
        /// Supply one project-relative file as the complete patch context.
        #[arg(long)] target: Option<String>,
        /// Replace one explicitly selected source line using model-generated text.
        #[arg(long, requires = "target")]
        line: Option<usize>,
        /// Use the lab's selective lexical retriever without a target hint.
        #[arg(long, conflicts_with = "target", requires = "allowed_edit_path")]
        selective_context: bool,
        /// Choose an opt-in lab-only retrieval arm.
        #[arg(long, requires = "selective_context", value_enum)]
        retrieval_strategy: Option<LabRetrieval>,
        /// Restrict the approved edit to this exact relative path. Repeat for multiple files.
        #[arg(long)]
        allowed_edit_path: Vec<String>,
        /// Emit sanitized retrieval, inference and approval measurements.
        #[arg(long)]
        proposal_metrics: bool,
        /// Bound the pinned runtime's context for a measured lab condition.
        #[arg(long, requires = "selective_context", value_parser = clap::value_parser!(u32).range(2048..=8192))]
        context_tokens: Option<u32>,
    },
}

fn metric(enabled: bool, row: Value) {
    if enabled { println!("Proposal metrics: {row}"); }
}

fn main() -> Result<()> {
    let args=Cli::parse();
    let project=Project::new(&args.project)?;
    let (task, edit, target, line, retrieval, allowed, metrics, context_tokens)=match args.command {
        Action::Ask{task}=>(task,false,None,None,None,Vec::new(),false,None),
        Action::Edit{task,allow_write,target,line,selective_context,retrieval_strategy,allowed_edit_path,proposal_metrics,context_tokens}=>{
            ensure!(allow_write,"Edit requires explicit --allow-write lab opt-in");
            let retrieval = selective_context.then_some(retrieval_strategy.unwrap_or(LabRetrieval::Baseline));
            (task,true,target,line,retrieval,allowed_edit_path,proposal_metrics,context_tokens)
        }
    };
    let retrieval_start = Instant::now();
    let selected = match (target, retrieval) {
        (Some(path), _) => workbench::collect_edit_target(&project, &path),
        (None, Some(arm)) => retrieve_lab(&project, &task, arm),
        (None, None) => workbench::collect(&project, &task),
    };
    let retrieval_ms = retrieval_start.elapsed().as_millis() as u64;
    let selected = selected.inspect_err(|_| metric(metrics, json!({
        "phase":"retrieval", "status":"context_retrieval_failed", "elapsed_ms":retrieval_ms
    })))?;
    if metrics {
        let files: Vec<_> = selected.files.iter().map(|f| json!({"path":f.path,"complete":!f.truncated})).collect();
        metric(true, json!({"phase":"retrieval","status":"selected","elapsed_ms":retrieval_ms,
                            "files":files,"incomplete":selected.incomplete}));
    }
    println!("Deterministic context selection (not model-selected tool use):");
    for (f,(first,last)) in selected.files.iter().zip(&selected.ranges) {println!("File read verified: {} (lines {}–{}){}",terminal(&f.path),first,last,if f.truncated{" [excerpt only]"}else{""});}
    if selected.incomplete {println!("Context may be incomplete; search and file budgets apply.");}
    let startup = Instant::now();
    let server=match context_tokens {
        Some(tokens) => Runtime::start_bounded(&args.runtime, &args.model, tokens),
        None => Runtime::start(&args.runtime, &args.model),
    }.inspect_err(|_| metric(metrics, json!({
        "phase":"startup","status":"startup_failed","elapsed_ms":startup.elapsed().as_millis() as u64
    })))?;
    metric(metrics, json!({"phase":"startup","status":"ready","context_tokens":context_tokens,
        "elapsed_ms":startup.elapsed().as_millis() as u64}));
    if !edit {
        let answer=workbench::ask(&task,&selected,|request|server.complete(request))?;
        println!("Model answer (verify factual claims):");
        show(&answer);
    } else {
        let mut calls = 0;
        let mut inference_error = false;
        let mut usage = (None, None);
        let mut finish_reason = None;
        let start = Instant::now();
        let complete = |request| {
            calls += 1;
            match server.complete_with_usage(request) {
                Ok(reply) => {
                    usage = (reply.prompt_tokens, reply.completion_tokens);
                    Ok(reply.message)
                }
                Err(error) => {
                    inference_error = true;
                    if let Some(detail) = error.downcast_ref::<tinybuilder::runtime::IncompleteCompletion>() {
                        usage = (detail.prompt_tokens, detail.completion_tokens);
                        finish_reason = Some(detail.reason);
                    }
                    Err(error)
                }
            }
        };
        let patch = match line {
            Some(line) => tinybuilder::grounded::propose_edit_at_line(&project, &task, &selected.files[0], line, complete),
            None => workbench::propose(&project, &task, &selected, complete),
        };
        let status = match &patch {
            Ok(patch) if allowed.is_empty() || allowed.contains(&patch.path) => "proposal_ready",
            Ok(_) => "scope_rejected",
            Err(_) if finish_reason.is_some() => "incomplete_response",
            Err(_) if inference_error => "runtime_failure",
            Err(error) => match error.to_string().as_str() {
                "Replacement must match exactly once" => "replacement_match",
                "Patch target not in complete evidence" => "target_not_in_evidence",
                "File changed since context selection" => "stale_evidence",
                "No change" => "no_change",
                _ if calls == 0 => "request_rejected",
                _ => "proposal_invalid",
            },
        };
        metric(metrics, json!({"phase":"proposal","status":status,"calls":calls,
            "elapsed_ms":start.elapsed().as_millis() as u64,
            "prompt_tokens":usage.0,"completion_tokens":usage.1,"finish_reason":finish_reason,
            "path":patch.as_ref().ok().filter(|_| status == "proposal_ready").map(|p| &p.path)}));
        let patch = patch?;
        ensure!(allowed.is_empty() || allowed.contains(&patch.path), "Proposal is outside the approved file scope");
        println!("Proposed model-generated replacement in {}",terminal(&patch.path));
        show(&patch.patch.diff);
        print!("Apply this exact patch? Type yes: ");
        io::stdout().flush()?;
        let mut answer=String::new();
        let approved=io::stdin().read_line(&mut answer)? > 0 && answer.trim()=="yes";
        if approved {
            project.apply(patch.patch,true)?;
            println!("Approved patch applied. Independent tests are still required.");
            metric(metrics, json!({"phase":"approval","status":"applied"}));
        } else {
            println!("Patch declined. No changes made.");
            metric(metrics, json!({"phase":"approval","status":"not_approved"}));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn selective_lab_requires_scope_and_excludes_operator_target_hints() {
        let base = ["lab", "--project", "fixture", "--runtime", "runtime", "--model", "model",
                    "edit", "task", "--allow-write", "--selective-context"];
        assert!(Cli::try_parse_from(base).is_err());
        let args = base.into_iter().chain(["--allowed-edit-path", "app/Case.php"]);
        assert!(Cli::try_parse_from(args.clone()).is_ok());
        assert!(Cli::try_parse_from(args.clone().chain(["--context-tokens", "4096"])).is_ok());
        assert!(Cli::try_parse_from(args.clone().chain(["--context-tokens", "100000"])).is_err());
        assert!(Cli::try_parse_from(args.chain(["--target", "app/Case.php"])).is_err());
    }
}
