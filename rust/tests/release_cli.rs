use std::{fs,process::Command};
fn cli()->Command {Command::new(env!("CARGO_BIN_EXE_tinybuilder"))}
#[test]
fn release_version_matches_canonical_source(){
    let result=cli().arg("--version").output().unwrap();
    assert!(result.status.success());
    assert_eq!(String::from_utf8_lossy(&result.stdout).trim(),
        format!("tinybuilder {}",include_str!("../PRODUCT_VERSION").trim()));
}
#[test]
fn normal_cli_does_not_expose_mutation_or_exec(){
    let result=cli().arg("--help").output().unwrap();
    assert!(result.status.success());
    let help=String::from_utf8_lossy(&result.stdout);
    for unsupported in ["create","exec","--allow-write","--propose","mcp"]{
        assert!(!help.contains(unsupported),"{unsupported} exposed");
    }
    for args in [vec!["create","new.rs"],vec!["exec","anything"],vec!["mcp"],
        vec!["chat","test","--allow-write"],vec!["grounded","test","--propose"]]{
        let result=cli().args(args).output().unwrap();
        assert!(!result.status.success());
    }
    let help=cli().args(["chat","--help"]).output().unwrap();
    assert!(!String::from_utf8_lossy(&help.stdout).contains("--allow-write"));
}
#[test]
fn inspect_deep_source_without_writes_or_model(){
    let dir=tempfile::tempdir().unwrap();
    let path=dir.path().join("deep.rs");
    let body=format!("{}fn target_symbol() {{}}\n","// filler\n".repeat(3000));
    fs::write(&path,&body).unwrap();
    let result=cli().args(["inspect","Explain target_symbol","--project"])
        .arg(dir.path()).output().unwrap();
    assert!(result.status.success());
    assert!(String::from_utf8_lossy(&result.stdout).contains("fn target_symbol"));
    assert_eq!(fs::read_to_string(path).unwrap(),body);
    assert_eq!(fs::read_dir(dir.path()).unwrap().count(),1);
}
