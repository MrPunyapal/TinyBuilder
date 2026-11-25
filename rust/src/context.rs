//! Bounded lexical context retrieval. No persistent index or model calls.
use crate::project::{Project, ReadResult};
use anyhow::{ensure, Result};
use std::collections::{BTreeMap, BTreeSet};

pub struct Context {
    pub files: Vec<ReadResult>,
    pub incomplete: bool,
}
const STOP: &[&str] = &["the","and","this","that","with","from","what","where","when","which",
    "please","find","explain","show","locate","fix","change","update","make","project","file",
    "files","code","function","method","class","return","does","into","about","using","should",
    "could","would","can","for","how","why","not","are","all"];

fn terms(task: &str) -> Vec<String> {
    let words: BTreeSet<String> = task.split(|c:char| !(c.is_alphanumeric() || c=='_'))
        .filter(|s| s.len()>=3 && s.len()<=80 && !STOP.contains(&s.to_ascii_lowercase().as_str()))
        .map(str::to_owned).collect();
    let mut v: Vec<_> = words.into_iter().collect();
    v.sort_by(|a,b| b.len().cmp(&a.len()).then_with(||a.cmp(b)));
    v.truncate(4);
    v
}

pub fn retrieve(project: &Project, task: &str) -> Result<Context> {
    ensure!(!task.trim().is_empty() && task.len()<=8192, "Invalid task");
    let words = terms(task);
    let (ranked, mut incomplete) = project.ranked_candidates(&words,task)?;
    let mut ranks: BTreeMap<String,u32> = ranked.into_iter().collect();
    // Explicit file paths can lie beyond the bounded listing. Project::read
    // validates every candidate independently.
    for word in task.split_whitespace().take(128) {
        let path = word.trim_matches(|c:char| c as u32 == 96 || matches!(c,'"'|'\''|','|';'|'?'|'('|')'));
        if path.contains('.') && path.len()<=4096 {
            if let Ok(r) = project.read(path) {
                ranks.insert(r.path,150);
            }
        }
    }
    let mut ranked: Vec<_> = ranks.into_iter().collect();
    ranked.sort_by(|(pa,a),(pb,b)|b.cmp(a).then_with(||pa.cmp(pb)));
    incomplete |= ranked.len()>4;
    let mut files = Vec::new();
    for (path,_) in ranked {
        if files.len() == 4 {break;}
        match project.read(&path) {
            Ok(mut read) => {
                if read.text.len()>12*1024 {
                    let mut end=12*1024;
                    while !read.text.is_char_boundary(end) {end-=1;}
                    read.text.truncate(end);
                    read.truncated=true;
                }
                incomplete |= read.truncated;
                files.push(read);
            }
            Err(_) => incomplete=true,
        }
    }
    ensure!(!files.is_empty(),"No relevant readable files found; specify a file or symbol");
    Ok(Context {files,incomplete})
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    #[test]
    fn locates_symbol_and_ignores_dependency_trees() {
        let dir=tempfile::tempdir().unwrap();
        fs::write(dir.path().join("README.md"),"project overview").unwrap();
        fs::write(dir.path().join("alpha.rs"),"fn compute_total() {}").unwrap();
        fs::write(dir.path().join("beta.rs"),"fn unrelated() {}").unwrap();
        fs::create_dir(dir.path().join("vendor")).unwrap();
        fs::write(dir.path().join("vendor/other.rs"),"compute_total").unwrap();
        let p=Project::new(dir.path()).unwrap();
        let c=retrieve(&p,"Locate and explain compute_total").unwrap();
        assert_eq!(c.files[0].path,"alpha.rs");
        assert!(c.files.iter().all(|r|!r.path.starts_with("vendor/")));
        assert!(c.files.iter().all(|r|r.path!="beta.rs"));
    }
    #[test]
    fn missing_evidence_is_not_a_guess() {
        let dir=tempfile::tempdir().unwrap();
        let p=Project::new(dir.path()).unwrap();
        assert!(retrieve(&p,"Explain frobnicator").is_err());
    }
}
