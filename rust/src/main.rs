use anyhow::{ensure, Context, Result};
use clap::{Parser, Subcommand};
use std::{io::{self, Write}, path::PathBuf};
use tinybuilder::{agent::{self, Options, Protocol}, project::Project, runtime::{self, Runtime}, workbench, show, terminal};

#[derive(Parser)]
#[command(name="tinybuilder", version, about="Native experimental local coding assistant")]
struct Cli {
    #[command(subcommand)]
    command: Option<Command>,
}
#[derive(Subcommand)]
enum Command {
    App {
        #[arg(long)] project: Option<PathBuf>,
        #[arg(long)] runtime: Option<PathBuf>,
        #[arg(long)] model: Option<PathBuf>,
    },
    Chat {
        task: String,
        #[arg(long, default_value=".")] project: PathBuf,
        #[arg(long)] runtime: PathBuf,
        #[arg(long)] model: PathBuf,
        #[arg(long)] strict_json: bool,
        #[arg(long)] allow_write: bool,
        #[arg(long)] required_read: Option<String>,
    },
    /// Inspect context without starting a model or writing files.
    Inspect {
        task: String,
        #[arg(long, default_value=".")] project: PathBuf,
    },
    /// Experimental context-first answer or reviewed patch proposal.
    Grounded {
        task: String,
        #[arg(long, default_value=".")] project: PathBuf,
        #[arg(long)] runtime: PathBuf,
        #[arg(long)] model: PathBuf,
        #[arg(long)] strict_json: bool,
        #[arg(long, requires="strict_json")] propose: bool,
        #[arg(long, requires="propose")] allow_write: bool,
    },
    Read {
        path: String,
        #[arg(long, default_value=".")] project: PathBuf,
    },
    Search {
        query: String,
        #[arg(long, default_value=".")] project: PathBuf,
    },
    Doctor {
        #[arg(long, default_value=".")] project: PathBuf,
        #[arg(long)] runtime: Option<PathBuf>,
    },
}
fn input(prompt: &str) -> Result<Option<String>> {
    print!("{prompt}");
    io::stdout().flush()?;
    let mut line = String::new();
    if io::stdin().read_line(&mut line)? == 0 { return Ok(None); }
    Ok(Some(line.trim().to_owned()))
}
fn yes(prompt: &str) -> bool {
    input(prompt).ok().flatten().is_some_and(|s| s == "yes")
}
fn choose(value: Option<PathBuf>, prompt: &str) -> Result<PathBuf> {
    match value {
        Some(p) => Ok(p),
        None => Ok(PathBuf::from(input(prompt)?.filter(|s| !s.is_empty()).context("No path selected")?)),
    }
}
fn installed_runtime() -> Option<PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let dir = exe.parent()?;
    for candidate in [dir.join("runtime"), dir.parent()?.join("runtime")] {
        if candidate.join("runtime-manifest.json").is_file() { return Some(candidate); }
    }
    None
}
fn task(project: &Project, server: &Runtime, text: &str, protocol: Protocol, allow_write: bool, required: Option<String>) -> Result<()> {
    let result = agent::run(project, text, Options { protocol, allow_write, required_read:required, max_rounds:8 },
        |p| server.complete(p),
        |path, diff| {
            println!("Proposed replacement in {}", terminal(path));
            show(diff);
            yes("Apply this exact patch? Type yes: ")
        },
        |event| println!("{}", terminal(event)))?;
    println!("Model response (verify factual claims):");
    show(&result.answer);
    println!("Evidence: {} file(s) read, {} searches, {} listings, {} approved edits.",
        result.reads.len(), result.searches, result.listings, result.edits);
    Ok(())
}
fn show_context(context: &tinybuilder::context::Context) {
    println!("Deterministic context selection:");
    for (file,(first,last)) in context.files.iter().zip(&context.ranges) {
        println!("File read verified: {} (lines {}–{}){}",terminal(&file.path),first,last,
            if file.truncated {" [excerpt only]"}else{""});
    }
    if context.incomplete {println!("Context incomplete; bounded search and excerpt limits apply.");}
}
fn grounded_task(project: &Project, server: &Runtime, text: &str, proposal: bool, allow_write: bool) -> Result<()> {
    let context=workbench::collect(project,text)?;
    show_context(&context);
    if !proposal {
        show(&workbench::ask(text,&context,|p|server.complete(p))?);
    } else {
        let result=workbench::propose(project,text,&context,|p|server.complete(p))?;
        println!("Proposed replacement in {}",terminal(&result.path));
        show(&result.patch.diff);
        if allow_write && yes("Apply this exact patch to the disposable project? Type yes: ") {
            project.apply(result.patch,true)?;
            println!("Approved patch applied. Independent verification still required.");
        } else {
            println!("Proposal only; no files changed.");
        }
    }
    Ok(())
}
fn help() {
    println!("/read PATH (verified AI-assisted read), /cat PATH (no inference), /search TEXT, /ask QUESTION (context-first read), /strict, /write, /help, /quit");
}
fn app(project: Option<PathBuf>, runtime_dir: Option<PathBuf>, model: Option<PathBuf>) -> Result<()> {
    println!("TinyBuilder native Rust — experimental. Read-only by default. No automatic downloads.");
    let project = Project::new(&choose(project, "Project directory: ")?)?;
    let root = choose(runtime_dir.or_else(installed_runtime), "Absolute trusted runtime directory: ")?;
    let model = choose(model, "Existing GGUF path: ")?;
    runtime::model_path(&model)?;
    println!("Starting CPU runtime; model compatibility and intelligence are not guaranteed.");
    let server = Runtime::start(&root, &model)?;
    println!("Ready. Ask a natural-language project question. /help shows optional commands.");
    let mut protocol = Protocol::Native;
    let mut allow_write = false;
    while let Some(line) = input("Task: ")? {
        if line.is_empty() { continue; }
        match line.as_str() {
            "/quit" => break,
            "/help" => help(),
            "/strict" => {
                if protocol == Protocol::StrictJson {
                    protocol = Protocol::Native;
                    println!("Native tools selected.");
                } else if yes("Enable experimental strict JSON for this session? Type yes: ") {
                    protocol = Protocol::StrictJson;
                }
            }
            "/write" => {
                allow_write = yes("Allow patch proposals for the next task? Every patch still needs approval. Type yes: ");
            }
            _ if line.starts_with("/read ") => {
                // This explicit read flow uses constrained actions only after
                // session consent, never inherits a pending write permission.
                allow_write = false;
                let path = line[6..].trim();
                if protocol != Protocol::StrictJson {
                    if !yes("Enable experimental strict JSON for verified reads this session? Type yes: ") {
                        println!("Read cancelled; no inference requested.");
                        continue;
                    }
                    protocol = Protocol::StrictJson;
                }
                let Some(question) = input("Question about this file (blank = summarize): ")? else { break; };
                let question = if question.is_empty() { "Summarize the file based on its actual contents.".to_owned() } else { question };
                if task(&project, &server, &question, protocol, false, Some(path.to_owned())).is_err() {
                    println!("Read failed or required evidence missing; no final answer.");
                }
            }
            _ if line.starts_with("/ask ") => {
                allow_write=false;
                if grounded_task(&project,&server,line[5..].trim(),false,false).is_err() {
                    println!("Context-first answer failed. Specify a file or symbol and try again.");
                }
            }
            _ if line.starts_with("/cat ") => {
                match project.read(line[5..].trim()) {
                    Ok(read) => { println!("File read verified: {}", terminal(&read.path)); show(&read.text); if read.truncated { println!("[Truncated]"); } }
                    Err(_) => println!("Read rejected or unavailable."),
                }
            }
            _ if line.starts_with("/search ") => {
                match project.search(line[8..].trim()) {
                    Ok(rows) => show(&rows),
                    Err(_) => println!("Search rejected."),
                }
            }
            _ if line.starts_with('/') => help(),
            _ => {
                let write = std::mem::take(&mut allow_write);
                if task(&project, &server, &line, protocol, write, None).is_err() {
                    println!("Task failed or no verified final answer. No automatic retry. Check prior tool activity for any approved edits.");
                }
            }
        }
    }
    Ok(())
}
fn run() -> Result<()> {
    let cli = Cli::parse();
    match cli.command.unwrap_or(Command::App { project:None,runtime:None,model:None }) {
        Command::App {project,runtime,model} => app(project,runtime,model),
        Command::Chat {task:text,project,runtime,model,strict_json,allow_write,required_read} => {
            let project = Project::new(&project)?;
            let server = Runtime::start(&runtime,&model)?;
            task(&project,&server,&text,if strict_json {Protocol::StrictJson} else {Protocol::Native},allow_write,required_read)
        }
        Command::Inspect {task:text,project} => {
            let project=Project::new(&project)?;
            let context=workbench::collect(&project,&text)?;
            show_context(&context);
            for file in context.files {println!("Source: {}",terminal(&file.path));show(&file.text);}
            Ok(())
        }
        Command::Grounded {task:text,project,runtime,model,strict_json,propose,allow_write} => {
            ensure!(!propose||strict_json,"Explicit strict JSON consent required");
            let project=Project::new(&project)?;
            let server=Runtime::start(&runtime,&model)?;
            grounded_task(&project,&server,&text,propose,allow_write)
        }
        Command::Read {path,project} => {
            let result = Project::new(&project)?.read(&path)?;
            println!("File read verified: {}", terminal(&result.path)); show(&result.text);
            if result.truncated { println!("[Truncated]"); }
            Ok(())
        }
        Command::Search {query,project} => {show(&Project::new(&project)?.search(&query)?); Ok(())}
        Command::Doctor {project,runtime} => {
            ensure!(Project::new(&project)?.root().is_dir(),"Project unavailable");
            println!("Project directory valid. Native Rust executable.");
            if let Some(root) = runtime { runtime::verify_runtime(&root)?; println!("Runtime inventory verified (not authenticated distribution evidence)."); }
            Ok(())
        }
    }
}
fn main() {
    if run().is_err() {
        eprintln!("TinyBuilder operation failed. Check arguments, project, trusted runtime and GGUF.");
        std::process::exit(1);
    }
}
