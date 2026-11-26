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
    },
}

fn main() -> Result<()> {
    let args=Cli::parse();
    let project=Project::new(&args.project)?;
    let (task, edit, target, line)=match args.command {
        Action::Ask{task}=>(task,false,None,None),
        Action::Edit{task,allow_write,target,line}=>{
            ensure!(allow_write,"Edit requires explicit --allow-write lab opt-in");
            (task,true,target,line)
        }
    };
    let selected = match target {
        Some(path) => workbench::collect_edit_target(&project, &path)?,
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
