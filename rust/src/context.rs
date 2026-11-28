//! Bounded lexical context retrieval. No persistent index or model calls.
use crate::project::{Project, ReadResult};
use anyhow::{ensure, Result};
use std::{borrow::Cow, collections::{BTreeMap, BTreeSet}};
use std::path::Path;

const FILE_LIMIT: usize = 4;
const FILE_BYTES: usize = 12 * 1024;

pub struct Context {
    pub files: Vec<ReadResult>,
    pub incomplete: bool,
    pub ranges: Vec<(usize,usize)>,
}
const STOP: &[&str] = &["the","and","this","that","with","from","what","where","when","which",
    "please","find","explain","show","locate","fix","change","update","make","project","file",
    "files","code","function","method","class","return","does","into","about","using","should",
    "could","would","can","for","how","why","not","are","all"];

fn terms(task: &str) -> Vec<String> {
    query_terms(task, 4)
}

fn query_terms(task: &str, limit: usize) -> Vec<String> {
    let words: BTreeSet<String> = task.split(|c:char| !(c.is_alphanumeric() || c=='_'))
        .filter(|s| s.len()>=3 && s.len()<=80 && !STOP.contains(&s.to_ascii_lowercase().as_str()))
        .map(str::to_owned).collect();
    let mut v: Vec<_> = words.into_iter().collect();
    v.sort_by(|a,b| b.len().cmp(&a.len()).then_with(||a.cmp(b)));
    v.truncate(limit);
    v
}

pub fn retrieve(project: &Project, task: &str) -> Result<Context> {
    retrieve_with_minimum_score(project, task, 1)
}

/// Lab arm that excludes overview fallbacks and isolated single-term hits.
pub fn retrieve_selective(project: &Project, task: &str) -> Result<Context> {
    retrieve_with_minimum_score(project, task, 10)
}

fn retrieve_with_minimum_score(project: &Project, task: &str, minimum_score: u32) -> Result<Context> {
    ensure!(!task.trim().is_empty() && task.len()<=8192, "Invalid task");
    let words = terms(task);
    let (ranked, incomplete) = project.ranked_candidates(&words,task)?;
    let ranked = ranked_paths(project, task, ranked, minimum_score);
    collect_paths(project, ranked, &words, incomplete)
}

fn ranked_paths(project: &Project, task: &str, ranked: Vec<(String, u32)>, minimum_score: u32) -> Vec<String> {
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
    let mut ranked: Vec<_> = ranks.into_iter().filter(|(_, score)| *score >= minimum_score).collect();
    ranked.sort_by(|(pa,a),(pb,b)|b.cmp(a).then_with(||pa.cmp(pb)));
    ranked.into_iter().map(|(path, _)| path).collect()
}

fn collect_paths(project: &Project, paths: Vec<String>, words: &[String], incomplete: bool) -> Result<Context> {
    collect_excerpts(paths, incomplete, |path| project.excerpt(path, &words[..words.len().min(4)], FILE_BYTES))
}

fn collect_excerpts(
    paths: Vec<String>, mut incomplete: bool,
    excerpt_for: impl Fn(&str) -> Result<crate::project::ContextExcerpt>,
) -> Result<Context> {
    incomplete |= paths.len() > FILE_LIMIT;
    let mut files = Vec::new();
    let mut ranges = Vec::new();
    for path in paths {
        if files.len() == FILE_LIMIT {break;}
        match excerpt_for(&path) {
            Ok(excerpt) => {
                incomplete |= excerpt.read.truncated;
                ranges.push((excerpt.first_line,excerpt.last_line));
                files.push(excerpt.read);
            }
            Err(_) => incomplete=true,
        }
    }
    ensure!(!files.is_empty(),"No relevant readable files found; specify a file or symbol");
    Ok(Context {files,incomplete,ranges})
}

/// Experimental cumulative arms. The product and the existing selective lab
/// arm continue to call the original ranker.
#[derive(Debug, Clone, Copy, PartialEq, Eq, clap::ValueEnum)]
pub enum LabRetrieval {
    Baseline,
    Threshold,
    Expanded,
    Caseless,
    Normalized,
    Dependencies,
    Fallback,
}

pub fn retrieve_lab(project: &Project, task: &str, arm: LabRetrieval) -> Result<Context> {
    retrieve_lab_with_excerpt(project, task, arm, None)
}

/// Compare excerpt alignment with the frozen normalized file ranking.
pub fn retrieve_lab_aligned(project: &Project, task: &str, prefer_code: bool) -> Result<Context> {
    retrieve_lab_with_excerpt(project, task, LabRetrieval::Normalized, Some(prefer_code))
}

fn retrieve_lab_with_excerpt(
    project: &Project, task: &str, arm: LabRetrieval, alignment: Option<bool>,
) -> Result<Context> {
    match arm {
        LabRetrieval::Baseline => return retrieve_selective(project, task),
        LabRetrieval::Threshold => return retrieve_with_minimum_score(project, task, 5),
        _ => {}
    }
    ensure!(!task.trim().is_empty() && task.len() <= 8192, "Invalid task");
    let normalized = matches!(arm, LabRetrieval::Normalized | LabRetrieval::Dependencies | LabRetrieval::Fallback);
    let words = if normalized {
        let mut tokens: Vec<_> = identifier_terms(task).into_iter()
            .filter(|token| !STOP.contains(&token.as_str())).collect();
        tokens.sort_by(|a,b| b.len().cmp(&a.len()).then_with(||a.cmp(b)));
        tokens.truncate(32);
        tokens
    } else {
        query_terms(task, 32)
    };
    let (ranked, incomplete) = project.rank_with(&words, task, 32, |path, words| {
        if normalized {
            let filename = path.rsplit('/').next().unwrap_or(path);
            hits(&identifier_terms(filename), words)
        } else {
            let lower = path.to_ascii_lowercase();
            words.iter().filter(|word| lower.contains(&word.to_ascii_lowercase())).count()
        }
    }, |text, words| {
        if normalized {
            hits(&identifier_terms(text), words)
        } else if arm == LabRetrieval::Caseless {
            let lower = text.to_ascii_lowercase();
            words.iter().filter(|word| lower.contains(&word.to_ascii_lowercase())).count()
        } else {
            words.iter().filter(|word| text.contains(word.as_str())).count()
        }
    })?;
    let mut paths = ranked_paths(project, task, ranked, 5);
    if matches!(arm, LabRetrieval::Dependencies | LabRetrieval::Fallback) && !paths.is_empty() {
        paths = expand_dependencies(project, paths, &words)?;
    }
    if arm == LabRetrieval::Fallback && paths.is_empty() {
        paths = bounded_fallback(project)?;
    }
    let Some(prefer_code) = alignment else {
        return collect_paths(project, paths, &words, incomplete);
    };
    let terms: BTreeMap<_, _> = words.iter().enumerate()
        .map(|(i, term)| (term.as_str(), 1u32 << i)).collect();
    collect_excerpts(paths, incomplete, |path| {
        project.excerpt_with(path, FILE_BYTES, |line| {
            let mut found = 0;
            visit_identifier_terms(line, |term, _| found |= terms.get(term).copied().unwrap_or(0));
            let matches = found.count_ones() as usize;
            if prefer_code && !is_line_comment(line) { matches * 4 } else { matches }
        }, |line| {
            let mut first = None;
            visit_identifier_terms(line, |term, offset| {
                if first.is_none() && terms.contains_key(term) { first = Some(offset); }
            });
            first.unwrap_or(0)
        })
    })
}

fn is_line_comment(line: &str) -> bool {
    let line = line.trim_start();
    ["//", "#", "/*", "* ", "*/"].iter().any(|prefix| line.starts_with(prefix))
}

fn hits(tokens: &BTreeSet<String>, words: &[String]) -> usize {
    words.iter().filter(|word| tokens.contains(*word)).count()
}

fn identifier_terms(text: &str) -> BTreeSet<String> {
    let mut result = BTreeSet::new();
    visit_identifier_terms(text, |token, _| { result.insert(token.to_owned()); });
    result
}

fn visit_identifier_terms(text: &str, mut visit: impl FnMut(&str, usize)) {
    let mut word_offset = 0;
    for word in text.split_inclusive(|c: char| !c.is_ascii_alphanumeric()) {
        let letters = word.trim_end_matches(|c: char| !c.is_ascii_alphanumeric());
        let bytes = letters.as_bytes();
        let mut start = 0;
        for end in 1..=bytes.len() {
            let boundary = end == bytes.len() || (bytes[end].is_ascii_uppercase()
                && (bytes[end - 1].is_ascii_lowercase()
                    || bytes.get(end + 1).is_some_and(u8::is_ascii_lowercase)));
            if boundary {
                let offset = word_offset + start;
                let raw = &letters[start..end];
                start = end;
                if (3..=80).contains(&raw.len()) {
                    let token = if raw.bytes().any(|b| b.is_ascii_uppercase()) {
                        Cow::Owned(raw.to_ascii_lowercase())
                    } else {
                        Cow::Borrowed(raw)
                    };
                    visit(&token, offset);
                    if let Some(stem) = token.strip_suffix("ies").filter(|stem| stem.len() >= 3) {
                        visit(&format!("{stem}y"), offset);
                    }
                    // Conservative regular English inflections, with the
                    // exact token retained beside the normalized form.
                    for suffix in ["ing", "ed", "s"] {
                        if let Some(stem) = token.strip_suffix(suffix).filter(|stem| stem.len() >= 4) {
                            visit(stem, offset);
                            break;
                        }
                    }
                }
            }
        }
        word_offset += word.len();
    }
}

fn expand_dependencies(project: &Project, ranked: Vec<String>, words: &[String]) -> Result<Vec<String>> {
    let (inventory, _) = project.candidates(".")?;
    let mut selected = Vec::new();
    // Expand one hop from the top lexical anchor, then retain the lexical order.
    if let Some(anchor) = ranked.first() {
        selected.push(anchor.clone());
        if let Ok(excerpt) = project.excerpt(anchor, &words[..words.len().min(4)], FILE_BYTES) {
            let anchor_path = Path::new(anchor);
            let source = &excerpt.read.text;
            let names: BTreeSet<_> = source.match_indices("::")
                .filter_map(|(index, _)| source[..index].trim_end().rsplit(|c: char| !c.is_ascii_alphanumeric() && c != '_').next())
                .filter(|name| !name.is_empty()).collect();
            for path in &inventory {
                let candidate = Path::new(path);
                if path != anchor && candidate.parent() == anchor_path.parent()
                    && candidate.extension() == anchor_path.extension()
                    && candidate.file_stem().and_then(|stem| stem.to_str()).is_some_and(|stem| names.contains(stem)) {
                    selected.push(path.clone());
                    if selected.len() == FILE_LIMIT { break; }
                }
            }
        }
    }
    for path in ranked {
        if !selected.contains(&path) { selected.push(path); }
    }
    Ok(selected)
}

fn bounded_fallback(project: &Project) -> Result<Vec<String>> {
    let (inventory, limited) = project.candidates(".")?;
    let paths: Vec<_> = inventory.into_iter().filter(|path| {
        matches!(Path::new(path).extension().and_then(|ext| ext.to_str()),
            Some("php" | "rs" | "py" | "js" | "ts" | "go" | "rb" | "java"))
    }).collect();
    if limited || paths.len() > FILE_LIMIT { return Ok(Vec::new()); }
    let mut total = 0;
    for path in &paths {
        let entry = project.excerpt(path, &[], FILE_BYTES)?.read;
        total += entry.text.len();
        if entry.truncated || total > FILE_BYTES { return Ok(Vec::new()); }
    }
    Ok(paths)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn aligned_excerpt_reaches_an_identifier_late_on_an_oversized_utf8_line() {
        let dir = tempfile::tempdir().unwrap();
        let body = format!("{} fn VesselPressure() {{}} {}\n", "λ".repeat(8000), "λ".repeat(6800));
        fs::write(dir.path().join("telemetry.rs"), &body).unwrap();
        let project = Project::new(dir.path()).unwrap();
        let task = "Find vessel pressure.";
        let baseline = retrieve_lab(&project, task, LabRetrieval::Normalized).unwrap();
        let aligned = retrieve_lab_aligned(&project, task, false).unwrap();
        assert_eq!(baseline.files[0].path, aligned.files[0].path);
        assert!(!baseline.files[0].text.contains("VesselPressure"));
        assert!(aligned.files[0].text.contains("VesselPressure"));
        assert!(aligned.incomplete && aligned.files[0].truncated);
        assert!(aligned.files[0].text.len() <= FILE_BYTES);
        assert_eq!(aligned.ranges, [(1, 1)]);
    }

    #[test]
    fn identifier_visiting_preserves_byte_offsets_and_normalization() {
        let mut found = Vec::new();
        visit_identifier_terms("☃;;XMLChecks category_Overrides", |word, offset| {
            found.push((word.to_owned(), offset));
        });
        assert_eq!(found, [
            ("xml".into(), 5), ("checks".into(), 8), ("check".into(), 8),
            ("category".into(), 15), ("overrides".into(), 24), ("override".into(), 24),
        ]);
    }

    #[test]
    fn code_preference_retains_comment_only_evidence() {
        let dir = tempfile::tempdir().unwrap();
        let body = format!("{}# glacier calibration witness\n", "# archival filler\n".repeat(900));
        fs::write(dir.path().join("archive.py"), body).unwrap();
        let project = Project::new(dir.path()).unwrap();
        let aligned = retrieve_lab_aligned(&project, "Find glacier calibration.", true).unwrap();
        assert!(aligned.files[0].text.contains("glacier calibration witness"));
        assert!(aligned.incomplete && aligned.files[0].truncated);
    }
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
    fn deep_symbol_context_is_not_just_a_prefix() {
        let dir=tempfile::tempdir().unwrap();
        fs::write(dir.path().join("deep.rs"),format!("{}fn deep_symbol() {{}}\n","// line\n".repeat(3000))).unwrap();
        let p=Project::new(dir.path()).unwrap();
        let c=retrieve(&p,"Explain deep_symbol").unwrap();
        assert!(c.files[0].text.contains("deep_symbol"));
        assert!(c.files[0].truncated);
        assert!(c.ranges[0].0>1);
        assert!(c.incomplete);
    }
    #[test]
    fn missing_evidence_is_not_a_guess() {
        let dir=tempfile::tempdir().unwrap();
        let p=Project::new(dir.path()).unwrap();
        assert!(retrieve(&p,"Explain frobnicator").is_err());
    }
    #[test]
    fn selective_arm_keeps_named_source_and_drops_single_hit_and_overview() {
        let dir = tempfile::tempdir().unwrap();
        fs::write(dir.path().join("README.md"), "overview").unwrap();
        fs::write(dir.path().join("SeatPolicy.php"), "<?php class SeatPolicy {}").unwrap();
        fs::write(dir.path().join("composer.lock"), "SeatPolicy").unwrap();
        let project = Project::new(dir.path()).unwrap();
        let task = "Fix SeatPolicy";
        assert_eq!(retrieve(&project, task).unwrap().files.len(), 3);
        let selected = retrieve_selective(&project, task).unwrap();
        assert_eq!(selected.files.len(), 1);
        assert_eq!(selected.files[0].path, "SeatPolicy.php");
    }

    #[test]
    fn normalized_terms_match_camel_case_and_inflection_without_substrings() {
        let dir = tempfile::tempdir().unwrap();
        fs::write(dir.path().join("XMLPolicyReader.php"), "<?php function parse_policy() {}").unwrap();
        fs::write(dir.path().join("Unrelated.php"), "<?php function enforcement() {}").unwrap();
        let project = Project::new(dir.path()).unwrap();
        let result = retrieve_lab(&project, "Adjust readers for policies", LabRetrieval::Normalized).unwrap();
        assert_eq!(result.files.iter().map(|file| file.path.as_str()).collect::<Vec<_>>(), ["XMLPolicyReader.php"]);
    }

    #[test]
    fn expands_only_static_references_from_top_anchor_in_same_directory() {
        let dir = tempfile::tempdir().unwrap();
        fs::create_dir(dir.path().join("other")).unwrap();
        fs::write(dir.path().join("RateAdapter.php"), "<?php class RateAdapter { function rate() { return TariffConstants::RATE; } }").unwrap();
        fs::write(dir.path().join("TariffConstants.php"), "<?php class TariffConstants {}").unwrap();
        fs::write(dir.path().join("other/TariffConstants.php"), "<?php class TariffConstants {}").unwrap();
        let project = Project::new(dir.path()).unwrap();
        let task = "Repair RateAdapter";
        assert_eq!(retrieve_lab(&project, task, LabRetrieval::Normalized).unwrap().files.len(), 1);
        let context = retrieve_lab(&project, task, LabRetrieval::Dependencies).unwrap();
        assert_eq!(context.files.iter().map(|file| file.path.as_str()).collect::<Vec<_>>(),
            ["RateAdapter.php", "TariffConstants.php"]);
    }

    #[test]
    fn fallback_abstains_when_the_repository_cannot_fit_one_bounded_context() {
        let dir = tempfile::tempdir().unwrap();
        for path in ["alpha.rs", "beta.rs", "README.md", ".env"] {
            fs::write(dir.path().join(path), "source").unwrap();
        }
        let project = Project::new(dir.path()).unwrap();
        let task = "Repair frobnicator";
        assert!(retrieve_lab(&project, task, LabRetrieval::Dependencies).is_err());
        assert_eq!(retrieve_lab(&project, task, LabRetrieval::Fallback).unwrap().files.len(), 2);
        for path in ["gamma.rs", "delta.rs", "epsilon.rs"] {
            fs::write(dir.path().join(path), "source").unwrap();
        }
        assert!(retrieve_lab(&project, task, LabRetrieval::Fallback).is_err());
    }
}
