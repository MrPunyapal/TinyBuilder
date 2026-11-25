//! Proposal-only diagnostic: no writes to source, no execution of generated code.
//! Exact source oracle is intentionally narrower than functional coding qualification.
use anyhow::{ensure, Context, Result};
use clap::Parser;
use rand::{distributions::Alphanumeric, Rng};
use serde_json::json;
use sha2::{Digest,Sha256};
use std::{fs::{self,File},io::Read,path::{Path,PathBuf},time::Instant};
use tinybuilder::{project::Project,runtime::{self,Runtime},workbench};

#[derive(Parser)]
struct Args {
    #[arg(long)] runtime:PathBuf,
    #[arg(long)] model:PathBuf,
    #[arg(long)] expected_sha256:String,
    #[arg(long)] output:PathBuf,
}
fn digest(path:&Path)->Result<String>{
    let mut file=File::open(path)?;
    let mut sha=Sha256::new();
    let mut buf=[0;65536];
    loop {let n=file.read(&mut buf)?;if n==0{break;}sha.update(&buf[..n]);}
    Ok(format!("{:x}",sha.finalize()))
}
struct Case {name:&'static str,path:&'static str,source:&'static str,expected:&'static str,task:&'static str}
const CASES:[Case;3]=[
    Case{name:"python_boundary",path:"limits.py",source:"def is_allowed(age):\n    return age > 18\n",
        expected:"def is_allowed(age):\n    return age >= 18\n",
        task:"Fix is_allowed in limits.py so age 18 is accepted. Preserve all other code."},
    Case{name:"php_validation",path:"validation.php",source:"<?php\nfunction is_valid($count) {\n    return $count >= 0;\n}\n",
        expected:"<?php\nfunction is_valid($count) {\n    return $count > 0;\n}\n",
        task:"Fix is_valid in validation.php: zero must be rejected, positive counts accepted. Preserve all other code."},
    Case{name:"rust_operator",path:"calc.rs",source:"pub fn area(width: i32, height: i32) -> i32 {\n    width + height\n}\n",
        expected:"pub fn area(width: i32, height: i32) -> i32 {\n    width * height\n}\n",
        task:"Fix area in calc.rs to calculate rectangle area using multiplication. Preserve all other code."},
];
fn main()->Result<()>{
    let args=Args::parse();
    let model=runtime::model_path(&args.model)?;
    let hash=digest(&model)?;
    ensure!(hash==args.expected_sha256.to_ascii_lowercase(),"Model SHA-256 mismatch");
    fs::create_dir(&args.output).context("Output must be new")?;
    let server=Runtime::start(&args.runtime,&model)?;
    let mut rows=Vec::new();
    let mut stopped=false;
    for case in CASES {
        let dir=tempfile::tempdir()?;
        let tag:String=rand::thread_rng().sample_iter(&Alphanumeric).take(20).map(char::from).collect();
        let suffix=if case.path.ends_with(".py"){format!("# fixture {tag}\n")}else{format!("// fixture {tag}\n")};
        let source=format!("{}{suffix}",case.source);
        let expected=format!("{}{suffix}",case.expected);
        fs::write(dir.path().join(case.path),&source)?;
        fs::write(dir.path().join("unrelated.txt"),"Do not modify this file.")?;
        let p=Project::new(dir.path())?;
        let start=Instant::now();
        let c=workbench::collect(&p,case.task)?;
        let read=c.files.iter().any(|f|f.path==case.path&&!f.truncated&&f.text==source);
        let mut transport_failed=false;
        let proposal=workbench::propose(&p,case.task,&c,|req|match server.complete(req){
            Ok(r)=>Ok(r),
            Err(e)=>{transport_failed=true;Err(e)}
        });
        let unchanged=fs::read(dir.path().join(case.path))?==source.as_bytes()
            && fs::read(dir.path().join("unrelated.txt"))?==b"Do not modify this file."
            && fs::read_dir(dir.path())?.count()==2;
        let exact=proposal.as_ref().is_ok_and(|r|r.path==case.path&&r.patch.preview_text()==expected);
        let valid=proposal.is_ok();
        let category=if !unchanged{"safety"}else if transport_failed{"transport_or_server"}
            else if !read{"missing_complete_evidence"}else if !valid{"invalid_proposal"}
            else if !exact{"wrong_patch"}else{"exact_proposal"};
        rows.push(json!({"case":case.name,"complete_file_read":read,"valid_proposal":valid,
            "exact_proposal":exact,"source_unchanged":unchanged,"category":category,
            "elapsed_ms":start.elapsed().as_millis() as u64}));
        println!("{}: {category}",case.name);
        if !unchanged||transport_failed{stopped=true;break;}
    }
    drop(server);
    let unchanged_model=digest(&model)?==hash;
    let passed=rows.iter().filter(|r|r["category"]=="exact_proposal").count();
    fs::write(args.output.join("patch-diagnostic.json"),serde_json::to_vec_pretty(&json!({
        "profile":"exact-source-proposal-v1","requested":3,"attempted":rows.len(),"exact":passed,
        "model_sha256":hash,"model_unchanged":unchanged_model,"stopped":stopped,
        "semantic_qualification":false,"applied_edits":0,"executed_generated_code":false,
        "trials":rows
    }))?)?;
    println!("Exact proposals: {passed}/3. No patches applied or code executed.");
    ensure!(!stopped&&unchanged_model&&passed==3,"Proposal diagnostic failed");
    Ok(())
}
