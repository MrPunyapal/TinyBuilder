//! Experimental context-first natural language read/patch workbench.
use anyhow::{ensure, Result};
use clap::{Parser, Subcommand};
use std::{io::{self,Write}, path::PathBuf};
use tinybuilder::{context, grounded::{self, AnswerMode}, project::Project, runtime::Runtime, show, terminal};

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
    },
}

fn main() -> Result<()> {
    let args=Cli::parse();
    let project=Project::new(&args.project)?;
    let (task, edit)=match args.command {
        Action::Ask{task}=>(task,false),
        Action::Edit{task,allow_write}=>{
            ensure!(allow_write,"Edit requires explicit --allow-write lab opt-in");
            (task,true)
        }
    };
    let selected=context::retrieve(&project,&task)?;
    println!("Deterministic context selection (not model-selected tool use):");
    for (f,(first,last)) in selected.files.iter().zip(&selected.ranges) {println!("File read verified: {} (lines {}–{}){}",terminal(&f.path),first,last,if f.truncated{" [excerpt only]"}else{""});}
    if selected.incomplete {println!("Context may be incomplete; search and file budgets apply.");}
    let server=Runtime::start(&args.runtime,&args.model)?;
    if !edit {
        let request=grounded::answer_request_with_ranges(&task,&selected.files,AnswerMode::Plain,Some(&selected.ranges))?;
        let answer=grounded::decode_answer(&server.complete(request)?,AnswerMode::Plain)?;
        println!("Model answer (verify factual claims):");
        show(&answer);
    } else {
        let proposal=grounded::edit_request(&task,&selected.files)?;
        let response=server.complete(proposal)?;
        let patch=grounded::prepare_edit(&project,&selected.files,&response)?;
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
