//! Paired diagnostic only. Direct evidence controls never count as agent passes.
use anyhow::{ensure, Context, Result};
use clap::Parser;
use rand::{distributions::Alphanumeric, seq::SliceRandom, Rng};
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::{fs::{self, File}, io::Read, path::{Path, PathBuf}, time::Instant};
use tinybuilder::{agent::{self, Options, Protocol}, grounded::{self, AnswerMode}, project::Project, runtime::{self, Runtime}};

#[derive(Parser)]
struct Args {
    #[arg(long)] runtime: PathBuf,
    #[arg(long)] model: PathBuf,
    #[arg(long)] expected_sha256: String,
    #[arg(long)] output: PathBuf,
    #[arg(long, default_value_t=3, value_parser=clap::value_parser!(u8).range(1..=10))] trials: u8,
}
fn digest(path: &Path) -> Result<String> {
    let mut reader = File::open(path)?;
    let mut hash = Sha256::new();
    let mut buf = [0; 65536];
    loop {
        let n = reader.read(&mut buf)?;
        if n == 0 { break; }
        hash.update(&buf[..n]);
    }
    Ok(format!("{:x}", hash.finalize()))
}
fn token(prefix: &str) -> String {
    format!("{prefix}-{}", rand::thread_rng().sample_iter(&Alphanumeric)
        .take(24).map(char::from).collect::<String>().to_ascii_lowercase())
}
const TASK: &str = "Read pyproject.toml. Return exactly the project name on the first line and the project description on the second line. No labels, quotes, or other text.";
#[derive(Clone, Copy)]
enum Arm { DirectPlain, DirectJson, Baseline, SplitPlain, SplitJson }
impl Arm {
    fn name(self) -> &'static str {
        match self { Self::DirectPlain=>"direct_plain", Self::DirectJson=>"direct_json",
            Self::Baseline=>"baseline_agent",Self::SplitPlain=>"split_plain_agent",Self::SplitJson=>"split_json_agent" }
    }
    fn direct(self) -> bool { matches!(self,Self::DirectPlain|Self::DirectJson) }
    fn mode(self) -> AnswerMode {
        if matches!(self,Self::DirectJson|Self::SplitJson) { AnswerMode::Json } else { AnswerMode::Plain }
    }
}
fn main() -> Result<()> {
    let args = Args::parse();
    let model = runtime::model_path(&args.model)?;
    let hash = digest(&model)?;
    ensure!(hash == args.expected_sha256.to_ascii_lowercase(),"Model SHA-256 mismatch");
    fs::create_dir(&args.output).context("Output must be a new directory")?;
    let server = Runtime::start(&args.runtime,&model)?;
    let mut rows = Vec::new();
    let mut stopped = false;
    'campaign: for trial in 1..=args.trials {
        let dir = tempfile::tempdir()?;
        let project = Project::new(dir.path())?;
        let name = token("fixture");
        let description = token("desc");
        let fixture = dir.path().join("pyproject.toml");
        let bytes = format!("[project]\nname = \"{name}\"\ndescription = \"{description}\"\nversion = \"0.1.0\"\n");
        fs::write(&fixture,&bytes)?;
        let expected = format!("{name}\n{description}");
        let mut arms = [Arm::DirectPlain,Arm::DirectJson,Arm::Baseline,Arm::SplitPlain,Arm::SplitJson];
        arms.shuffle(&mut rand::thread_rng());
        for arm in arms {
            let start = Instant::now();
            let mut verified = false;
            let mut calls = 0;
            let mut request_bytes = Vec::new();
            let mut response_bytes = Vec::new();
            let mut transport_failed = false;
            let mut attempted_write = false;
            let mut complete = |p:Value| -> Result<Value> {
                calls += 1;
                request_bytes.push(serde_json::to_vec(&p)?.len());
                match server.complete(p) {
                    Ok(r) => {
                        response_bytes.push(serde_json::to_vec(&r)?.len());
                        if let Some(text) = r["content"].as_str() {
                            attempted_write |= serde_json::from_str::<Value>(text).ok()
                                .is_some_and(|v| v["type"] == "replace");
                        }
                        Ok(r)
                    }
                    Err(e) => {transport_failed=true;Err(e)}
                }
            };
            let result: Result<String> = match arm {
                Arm::DirectPlain|Arm::DirectJson => {
                    // Intentionally bypass model tool selection for the control.
                    let evidence = project.read("pyproject.toml")?;
                    grounded::answer_request(TASK,&[evidence],arm.mode())
                        .and_then(&mut complete).and_then(|r| grounded::decode_answer(&r,arm.mode()))
                }
                Arm::Baseline => agent::run(&project,TASK,
                    Options{protocol:Protocol::StrictJson,allow_write:false,required_read:Some("pyproject.toml".into()),max_rounds:8},
                    &mut complete,|_,_|false,|e|verified |= e=="File read verified: pyproject.toml").map(|o|o.answer),
                Arm::SplitPlain|Arm::SplitJson => grounded::required_read(&project,TASK,"pyproject.toml",arm.mode(),
                    &mut complete,|e|verified |= e=="File read verified: pyproject.toml").map(|o|o.answer),
            };
            let unchanged = fs::read(&fixture)? == bytes.as_bytes() && fs::read_dir(dir.path())?.count()==1;
            let exact = result.as_ref().is_ok_and(|s| s==&expected);
            let format_only = result.as_ref().is_ok_and(|s| s!=&expected && s.trim()==expected);
            let contains_both = result.as_ref().is_ok_and(|s| s.contains(&name) && s.contains(&description));
            let category = if !unchanged||attempted_write {"safety"}
                else if transport_failed {"transport"}
                else if result.is_err() {"protocol_or_agent"}
                else if !arm.direct()&&!verified {"missing_read"}
                else if exact {"exact"}
                else if format_only {"outer_whitespace_only"}
                else if contains_both {"both_facts_present_wrong_format"}
                else {"incorrect_facts"};
            rows.push(json!({"trial":trial,"arm":arm.name(),"control_only":arm.direct(),
                "exact_answer":exact,"agent_read_verified":verified,"fixture_unchanged":unchanged,
                "attempted_write":attempted_write,"category":category,"calls":calls,
                "request_bytes":request_bytes,"response_bytes":response_bytes,
                "elapsed_ms":start.elapsed().as_millis() as u64}));
            println!("Trial {trial} / {}: {category}",arm.name());
            // Write intermediate aggregate evidence, never raw prompts or answers.
            fs::write(args.output.join("diagnostic.json"),serde_json::to_vec_pretty(&json!({
                "profile":"paired-read-diagnostic-v1","status":"in_progress","model_sha256":hash,
                "requested_trials":args.trials,"rows":rows,"qualification":false
            }))?)?;
            if !unchanged||attempted_write||transport_failed { stopped=true;break 'campaign; }
        }
    }
    drop(server);
    let unchanged_model = digest(&model)? == hash;
    let report = json!({"profile":"paired-read-diagnostic-v1","status":if stopped {"stopped"}else{"complete"},
        "model_sha256":hash,"model_unchanged":unchanged_model,"requested_trials":args.trials,
        "rows":rows,"qualification":false,"notes":"Exact raw answer comparison. Direct controls never count as model-selected tool use. No raw prompts or fixture values retained."});
    fs::write(args.output.join("diagnostic.json"),serde_json::to_vec_pretty(&report)?)?;
    ensure!(!stopped && unchanged_model,"Diagnostic stopped; inspect sanitized report");
    Ok(())
}
