//! Experimental context-first natural language read/patch workbench.
use anyhow::{ensure, Result};
use clap::{Parser, Subcommand};
use std::{io::{self,Write}, path::PathBuf};
use tinybuilder::{workbench, project::Project, runtime::Runtime, show, terminal};

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
        /// Restrict the approved edit to this exact relative path. Repeat for multiple files.
        #[arg(long)]
        allowed_edit_path: Vec<String>,
    },
}

fn main() -> Result<()> {
    let args=Cli::parse();
    let project=Project::new(&args.project)?;
    let (task, edit, target, line, selective, allowed)=match args.command {
        Action::Ask{task}=>(task,false,None,None,false,Vec::new()),
        Action::Edit{task,allow_write,target,line,selective_context,allowed_edit_path}=>{
            ensure!(allow_write,"Edit requires explicit --allow-write lab opt-in");
            (task,true,target,line,selective_context,allowed_edit_path)
        }
    };
    let selected = match target {
        Some(path) => workbench::collect_edit_target(&project, &path)?,
        None if selective => tinybuilder::context::retrieve_selective(&project, &task)?,
        None => workbench::collect(&project, &task)?,
    };
    println!("Deterministic context selection (not model-selected tool use):");
    for (f,(first,last)) in selected.files.iter().zip(&selected.ranges) {println!("File read verified: {} (lines {}–{}){}",terminal(&f.path),first,last,if f.truncated{" [excerpt only]"}else{""});}
    if selected.incomplete {println!("Context may be incomplete; search and file budgets apply.");}
    let server=Runtime::start(&args.runtime,&args.model)?;
    if !edit {
        let answer=workbench::ask(&task,&selected,|request|server.complete(request))?;
        println!("Model answer (verify factual claims):");
        show(&answer);
    } else {
        let complete = |request| server.complete(request);
        let patch = match line {
            Some(line) => tinybuilder::grounded::propose_edit_at_line(&project, &task, &selected.files[0], line, complete)?,
            None => workbench::propose(&project, &task, &selected, complete)?,
        };
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
        } else {
            println!("Patch declined. No changes made.");
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
        assert!(Cli::try_parse_from(args.chain(["--target", "app/Case.php"])).is_err());
    }
}
