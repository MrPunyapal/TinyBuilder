use anyhow::{ensure, Context, Result};
use clap::{Parser, Subcommand};
use std::{io::{self, Write}, path::PathBuf};
use tinybuilder::{agent::{self, Options, Protocol}, project::Project, runtime::{self, Runtime}, show, terminal};

fn product_version()->&'static str { include_str!("../PRODUCT_VERSION").trim() }

#[derive(Parser)]
#[command(name="tinybuilder", version=product_version(), about="Experimental read-only local codebase assistant")]
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
        #[arg(long)] required_read: Option<String>,
    },
    /// Find relevant source without loading a model.
    Inspect {
        task: String,
        #[arg(long, default_value=".")] project: PathBuf,
    },
    /// Ask a read-only question using deterministic source selection.
    Grounded {
        task: String,
        #[arg(long, default_value=".")] project: PathBuf,
        #[arg(long)] runtime: PathBuf,
        #[arg(long)] model: PathBuf,
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
fn task(project: &Project, server: &Runtime, text: &str, protocol: Protocol, required: Option<String>) -> Result<()> {
    let result = agent::run(project, text, Options { protocol, allow_write:false, required_read:required, max_rounds:8 },
        |p| server.complete(p),
        |_, _| false,
        |event| println!("{}", terminal(event)))?;
    println!("Model response (verify factual claims):");
    show(&result.answer);
    println!("Evidence: {} file(s) read, {} searches, {} listings, {} approved edits.",
        result.reads.len(), result.searches, result.listings, result.edits);
    Ok(())
}
fn display_context(c:&tinybuilder::context::Context) {
    println!("Deterministic source selection:");
    for (f,(first,last)) in c.files.iter().zip(&c.ranges) {
        println!("Verified source: {} (lines {}–{}){}",terminal(&f.path),first,last,
            if f.truncated {" [excerpt only]"}else{""});
    }
    if c.incomplete {println!("Context incomplete; bounded scan and excerpt limits apply.");}
}
fn grounded(project:&Project,server:&Runtime,text:&str)->Result<()> {
    let c=tinybuilder::context::retrieve(project,text)?;
    display_context(&c);
    let req=tinybuilder::grounded::answer_request_with_ranges(text,&c.files,
        tinybuilder::grounded::AnswerMode::Plain,Some(&c.ranges))?;
    let answer=tinybuilder::grounded::decode_answer(&server.complete(req)?,tinybuilder::grounded::AnswerMode::Plain)?;
    println!("Model answer; verify factual claims:");
    show(&answer);
    Ok(())
}
fn help() {
    println!("/read PATH (verified AI-assisted read), /cat PATH (no inference), /search TEXT, /ask QUESTION, /strict, /help, /quit");
}
fn app(project: Option<PathBuf>, runtime_dir: Option<PathBuf>, model: Option<PathBuf>) -> Result<()> {
    println!("TinyBuilder 0.1 candidate — experimental, read-only. No automatic downloads.");
    let project = Project::new(&choose(project, "Project directory: ")?)?;
    let root = choose(runtime_dir.or_else(installed_runtime), "Absolute trusted runtime directory: ")?;
    let model = choose(model, "Existing GGUF path: ")?;
    runtime::model_path(&model)?;
    println!("Starting CPU runtime; model compatibility and intelligence are not guaranteed.");
    let server = Runtime::start(&root, &model)?;
    println!("Ready. Ask a natural-language project question. /help shows optional commands.");
    let mut protocol = Protocol::Native;
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
            _ if line.starts_with("/read ") => {
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
                if task(&project, &server, &question, protocol, Some(path.to_owned())).is_err() {
                    println!("Read failed or required evidence missing; no final answer.");
                }
            }
            _ if line.starts_with("/ask ") => {
                if grounded(&project,&server,line[5..].trim()).is_err() {
                    println!("Context-first answer failed; specify a file or symbol.");
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
                if task(&project, &server, &line, protocol, None).is_err() {
                    println!("Task failed or no verified final answer. No automatic retry.");
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
        Command::Chat {task:text,project,runtime,model,strict_json,required_read} => {
            let project = Project::new(&project)?;
            let server = Runtime::start(&runtime,&model)?;
            task(&project,&server,&text,if strict_json {Protocol::StrictJson} else {Protocol::Native},required_read)
        }
        Command::Inspect {task,project} => {
            let c=tinybuilder::context::retrieve(&Project::new(&project)?,&task)?;
            display_context(&c);
            for f in c.files {println!("Source: {}",terminal(&f.path));show(&f.text);}
            Ok(())
        }
        Command::Grounded {task,project,runtime,model} => {
            let project=Project::new(&project)?;
            let server=Runtime::start(&runtime,&model)?;
            grounded(&project,&server,&task)
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
