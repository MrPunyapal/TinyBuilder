//! Context-first workflow shared by the CLI and offline diagnostics.
//! No tool calls or commands are inferred from answer text.
use crate::{context::{self, Context}, grounded::{self, AnswerMode, ProposedEdit}, project::Project};
use anyhow::{ensure, Result};
use serde_json::Value;

pub fn collect(project: &Project, task: &str) -> Result<Context> {
    context::retrieve(project,task)
}
/// An explicit lab target keeps unrelated context out of the proposal request.
pub fn collect_edit_target(project: &Project, path: &str) -> Result<Context> {
    let file = project.read(path)?;
    ensure!(!file.truncated, "Patch target exceeds complete-read budget");
    let last_line = file.text.lines().count();
    Ok(Context { files: vec![file], incomplete: false, ranges: vec![(1, last_line)] })
}

pub fn ask(task: &str, context: &Context, complete: impl FnOnce(Value)->Result<Value>) -> Result<String> {
    let request=grounded::answer_request_with_ranges(task,&context.files,AnswerMode::Plain,Some(&context.ranges))?;
    grounded::decode_answer(&complete(request)?,AnswerMode::Plain)
}
/// Explicitly selected constrained proposal path. Does not apply a patch.
pub fn propose(project: &Project, task: &str, context: &Context, complete: impl FnOnce(Value)->Result<Value>) -> Result<ProposedEdit> {
    let request=grounded::edit_request(task,&context.files)?;
    grounded::prepare_edit(project,&context.files,&complete(request)?)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::fs;
    #[test]
    fn workbench_never_applies_model_proposals_implicitly() {
        let dir=tempfile::tempdir().unwrap();
        fs::write(dir.path().join("calc.rs"),"fn total() -> i32 { 2 + 3 }\n").unwrap();
        let p=Project::new(dir.path()).unwrap();
        let c=collect(&p,"Fix total in calc.rs").unwrap();
        let proposed=propose(&p,"Fix total in calc.rs",&c,|r|{
            assert!(r.get("tools").is_none());
            assert!(r.get("response_format").is_some());
            Ok(json!({"role":"assistant","content":"{\"path\":\"calc.rs\",\"old\":\"2 + 3\",\"new\":\"2 * 3\"}"}))
        }).unwrap();
        assert_eq!(proposed.patch.preview_text(),"fn total() -> i32 { 2 * 3 }\n");
        assert_eq!(p.read("calc.rs").unwrap().text,"fn total() -> i32 { 2 + 3 }\n");
        assert!(p.apply(proposed.patch,false).is_err());
    }
    #[test]
    fn explicit_patch_target_restricts_evidence_and_proposal_paths() {
        let dir = tempfile::tempdir().unwrap();
        fs::write(dir.path().join("a.php"), "<?php return false;\n").unwrap();
        fs::write(dir.path().join("b.php"), "<?php return false;\n").unwrap();
        let project = Project::new(dir.path()).unwrap();
        assert!(collect_edit_target(&project, "../b.php").is_err());
        let context = collect_edit_target(&project, "a.php").unwrap();
        assert_eq!(context.files.len(), 1);
        assert!(propose(&project, "Fix a.php", &context, |request| {
            assert!(!request.to_string().contains("b.php"));
            Ok(json!({"role":"assistant", "content":r#"{"path":"b.php","old":"false","new":"true"}"#}))
        }).is_err());
        assert_eq!(project.read("b.php").unwrap().text, "<?php return false;\n");
    }

    #[test]
    fn plain_answer_cannot_invoke_a_tool() {
        let dir=tempfile::tempdir().unwrap();
        fs::write(dir.path().join("a.txt"),"secret").unwrap();
        let p=Project::new(dir.path()).unwrap();
        let c=collect(&p,"Read a.txt").unwrap();
        assert!(ask("Read a.txt",&c,|r|{
            assert!(r.get("response_format").is_none());
            assert!(r.get("tools").is_none());
            Ok(json!({"role":"assistant","content":"x","tool_calls":[{"type":"function"}]}))
        }).is_err());
    }
}
