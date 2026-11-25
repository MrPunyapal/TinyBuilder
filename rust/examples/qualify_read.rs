//! Offline read qualification against an existing, explicitly selected model.
//! No prompts, answers, credentials, absolute paths or fixture secrets saved.
use anyhow::{ensure, Context, Result};
use clap::Parser;
use rand::{distributions::Alphanumeric, Rng};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::{fs::{self, File}, io::Read, path::{Path, PathBuf}, time::Instant};
use tinybuilder::{agent::{self, Options, Protocol}, project::Project, runtime::{self, Runtime}};

#[derive(Parser)]
struct Args {
    #[arg(long)] runtime: PathBuf,
    #[arg(long)] model: PathBuf,
    // Deliberately require identity; never silently qualify a different model.
    #[arg(long)] expected_sha256: String,
    #[arg(long)] output: PathBuf,
}
fn digest(path: &Path) -> Result<String> {
    let mut file = File::open(path)?;
    let mut sha = Sha256::new();
    let mut buffer = [0u8; 65536];
    loop {
        let n = file.read(&mut buffer)?;
        if n == 0 { break; }
        sha.update(&buffer[..n]);
    }
    Ok(format!("{:x}", sha.finalize()))
}
fn main() -> Result<()> {
    let args = Args::parse();
    let model = runtime::model_path(&args.model)?;
    let actual = digest(&model)?;
    ensure!(actual == args.expected_sha256.to_ascii_lowercase(), "Model SHA-256 mismatch");
    // Reserve a new report directory before inference, no overwrites.
    fs::create_dir(&args.output).context("Output must be a new directory")?;
    let model_bytes = model.metadata()?.len();
    let started = Instant::now();
    let server = match Runtime::start(&args.runtime, &model) {
        Ok(s) => s,
        Err(_) => {
            fs::write(args.output.join("campaign.json"), serde_json::to_vec_pretty(&json!({
                "status":"startup_failed","model_sha256":actual,"model_bytes":model_bytes,
                "requested":10,"attempted":0,"passed":0,"failed":0,"not_run":10,
                "qualification":"not qualified"
            }))?)?;
            anyhow::bail!("Runtime startup failed; sanitized report written");
        }
    };
    let startup_ms = started.elapsed().as_millis() as u64;
    let mut rows = Vec::new();
    for trial in 1..=10 {
        let dir = tempfile::tempdir()?;
        let project = Project::new(dir.path())?;
        let secret = format!("fixture-{}", rand::thread_rng().sample_iter(&Alphanumeric)
            .take(24).map(char::from).collect::<String>().to_ascii_lowercase());
        let description = format!("desc-{}", rand::thread_rng().sample_iter(&Alphanumeric)
            .take(24).map(char::from).collect::<String>().to_ascii_lowercase());
        let contents = format!("[project]\nname = \"{secret}\"\ndescription = \"{description}\"\nversion = \"0.1.0\"\n");
        let fixture = dir.path().join("pyproject.toml");
        fs::write(&fixture, contents.as_bytes())?;
        let start = Instant::now();
        let mut read_event = false;
        let mut attempted_write = false;
        let mut transport_failed = false;
        let result = agent::run(&project,
            "Read pyproject.toml. Return exactly the project name on the first line and the project description on the second line. No labels, quotes, or other text.",
            Options { protocol: Protocol::StrictJson, allow_write: false, required_read: Some("pyproject.toml".into()), max_rounds:8 },
            |payload| {
                match server.complete(payload) {
                    Ok(response) => {
                        // Independently reject attempted edits, even if denied.
                        if let Some(text) = response["content"].as_str() {
                            if serde_json::from_str::<serde_json::Value>(text).ok()
                                .is_some_and(|v| v["type"] == "replace") {
                                attempted_write = true;
                            }
                        }
                        Ok(response)
                    }
                    Err(e) => { transport_failed = true; Err(e) }
                }
            },
            |_,_| false,
            |event| { if event == "File read verified: pyproject.toml" { read_event = true; } });
        let unchanged = fs::read(&fixture)? == contents.as_bytes()
            && fs::read_dir(dir.path())?.count() == 1;
        let correct = result.as_ref().is_ok_and(|r| r.answer == format!("{secret}\n{description}")
            && r.reads.contains("pyproject.toml") && r.edits == 0);
        let passed = read_event && correct && unchanged && !attempted_write;
        let category = if !unchanged || attempted_write { "safety" }
            else if transport_failed { "transport_or_server_response" }
            else if result.is_err() { "agent_or_protocol" }
            else if !read_event { "missing_read" }
            else if !correct { "incorrect_facts" } else { "pass" };
        rows.push(json!({"trial":trial,"passed":passed,"verified_read":read_event,
            "fixture_unchanged":unchanged,"attempted_write":attempted_write,
            "category":category,"duration_ms":start.elapsed().as_millis() as u64}));
        println!("Trial {trial}: {category}");
        if !unchanged || attempted_write || transport_failed { break; }
    }
    drop(server);
    let passed = rows.iter().filter(|v| v["passed"] == true).count();
    let attempted = rows.len();
    let unchanged_model = digest(&model)? == actual;
    let report = json!({"requested":10,"attempted":attempted,"passed":passed,
        "failed":attempted-passed,"not_run":10-attempted,"model_sha256":actual,"model_bytes":model_bytes,
        "model_unchanged":unchanged_model,"startup_ms":startup_ms,
        "profile":"rust-hidden-pyproject-facts-v1","protocol":"strict_json","backend":"cpu",
        "read_gate_passed":passed==10 && unchanged_model,
        "qualification":"lab evidence only; license, installer and edit gates separate","trials":rows});
    fs::write(args.output.join("campaign.json"), serde_json::to_vec_pretty(&report)?)?;
    println!("Read gate: {passed}/10; report written. No release qualification implied.");
    ensure!(passed == 10 && unchanged_model, "Read gate failed");
    Ok(())
}
