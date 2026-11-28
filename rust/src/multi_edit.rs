//! Experimental, inert multi-edit previews. Never writes or executes source.
//! The caller supplies complete evidence and a separate trusted edit scope.
use crate::project::{Project, ReadResult};
use anyhow::{ensure, Context, Result};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use similar::TextDiff;
use std::collections::{BTreeMap, BTreeSet};

pub const MAX_FILES: usize = 8;
pub const MAX_EDITS: usize = 16;
pub const MAX_FILE_BYTES: usize = 32 * 1024;
pub const MAX_STATE_BYTES: usize = 128 * 1024;
pub const MAX_FRAGMENT_BYTES: usize = 8 * 1024;
pub const MAX_EDIT_BYTES: usize = 64 * 1024;
pub const MAX_JSON_BYTES: usize = 64 * 1024;
pub const MAX_DIFF_BYTES: usize = 64 * 1024;

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Batch {
    edits: Vec<Replacement>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Replacement {
    path: String,
    old: String,
    new: String,
}

/// Inert metadata only. This is not a Project::Patch or approval token.
pub struct FilePreview {
    pub path: String,
    pub original_sha256: String,
    pub proposed_sha256: String,
    pub proposed_bytes: usize,
}

pub struct Preview {
    pub files: Vec<FilePreview>,
    pub edits: usize,
    /// Untrusted text: render with crate::show, never pass to a patch command.
    pub combined_diff: String,
}

/// A project-bound virtual source state. Failed batches leave it unchanged.
/// Complete snapshots are checked at construction, before/after staging,
/// and on review. Concurrent hostile writers are not supported.
pub struct VirtualWorkspace<'a> {
    project: &'a Project,
    original: BTreeMap<String, String>,
    current: BTreeMap<String, String>,
    scope: BTreeSet<String>,
    edits: usize,
    edit_bytes: usize,
}

fn check_path(path: &str) -> Result<()> {
    ensure!(!path.is_empty() && path.len() <= 4096
        && !path.contains('\\') && !path.contains(':')
        && !path.chars().any(char::is_control)
        && path.split('/').all(|p| !p.is_empty() && p != "." && p != ".."),
        "Expected exact canonical project-relative path");
    Ok(())
}

fn verify_snapshot(project: &Project, path: &str, original: &str) -> Result<()> {
    let read = project.read(path).context("Source snapshot unavailable")?;
    ensure!(!read.truncated && read.path == path && read.text == original,
        "Source snapshot changed or is incomplete");
    Ok(())
}

fn digest(text: &str) -> String {
    format!("{:x}", Sha256::digest(text.as_bytes()))
}

impl<'a> VirtualWorkspace<'a> {
    /// Evidence includes complete editable files and optional complete
    /// supporting files. Truncated excerpts must not enter this workspace.
    /// Scope must be a nonempty subset of exact evidence paths.
    pub fn new(project: &'a Project, evidence: &[ReadResult], allowed_paths: &[String]) -> Result<Self> {
        ensure!((1..=MAX_FILES).contains(&evidence.len()), "Invalid evidence count");
        ensure!((1..=MAX_FILES).contains(&allowed_paths.len()), "Explicit edit scope required");
        let mut original = BTreeMap::new();
        let mut aliases = BTreeSet::new();
        let mut bytes = 0usize;
        for read in evidence {
            check_path(&read.path)?;
            ensure!(!read.truncated && read.text.len() <= MAX_FILE_BYTES,
                "Complete bounded source required");
            // Conservative case-insensitive alias rejection on every OS.
            ensure!(aliases.insert(read.path.to_lowercase()), "Duplicate or aliased evidence");
            bytes += read.text.len();
            ensure!(bytes <= MAX_STATE_BYTES, "Source budget exceeded");
            verify_snapshot(project, &read.path, &read.text)?;
            original.insert(read.path.clone(), read.text.clone());
        }
        let mut scope = BTreeSet::new();
        for path in allowed_paths {
            check_path(path)?;
            ensure!(original.contains_key(path), "Scope lacks complete evidence");
            ensure!(scope.insert(path.clone()), "Duplicate scope path");
        }
        let workspace = Self { project, current: original.clone(), original, scope,
            edits: 0, edit_bytes: 0 };
        workspace.verify_fresh()?;
        Ok(workspace)
    }

    fn verify_fresh(&self) -> Result<()> {
        for (path, text) in &self.original {
            verify_snapshot(self.project, path, text)?;
        }
        Ok(())
    }

    /// Inspect the current virtual bytes for a subsequent reasoning round.
    /// No disk writes, implicit retrieval, or scope expansion.
    pub fn virtual_source(&self, path: &str) -> Result<&str> {
        self.verify_fresh()?;
        self.current.get(path).map(String::as_str).context("Path not in evidence")
    }

    /// Strict JSON object {"edits":[{"path":...,"old":...,"new":...}]}.
    /// Each old fragment matches exactly once in the CURRENT virtual text,
    /// including earlier edits in this batch. Reject overlapping matches.
    /// All limits are cumulative across successive batches.
    pub fn stage_json(&mut self, raw: &str) -> Result<Preview> {
        ensure!(raw.len() <= MAX_JSON_BYTES, "Proposal JSON exceeds budget");
        let batch: Batch = serde_json::from_str(raw)
            .map_err(|_| anyhow::anyhow!("Invalid multi-edit proposal"))?;
        ensure!(!batch.edits.is_empty() && batch.edits.len() <= MAX_EDITS - self.edits,
            "Edit count budget exceeded");
        self.verify_fresh()?;

        // Work on a bounded temporary state; publish only after all checks.
        let mut next = self.current.clone();
        let mut edit_bytes = self.edit_bytes;
        let mut state_bytes: usize = next.values().map(String::len).sum();
        for edit in &batch.edits {
            check_path(&edit.path)?;
            ensure!(self.scope.contains(&edit.path), "Edit outside explicit scope");
            ensure!(!edit.old.is_empty() && edit.old.len() <= MAX_FRAGMENT_BYTES
                && edit.new.len() <= MAX_FRAGMENT_BYTES && edit.old != edit.new
                && !edit.old.contains('\0') && !edit.new.contains('\0'),
                "Invalid exact replacement");
            edit_bytes += edit.old.len() + edit.new.len();
            ensure!(edit_bytes <= MAX_EDIT_BYTES, "Cumulative edit bytes exceeded");

            let text = next.get_mut(&edit.path).context("Edit lacks evidence")?;
            // Search from the next UTF-8 boundary, not the end of the
            // match: overlapping occurrences are ambiguous too.
            let start = text.find(edit.old.as_str()).context("Exact replacement not found")?;
            let next_boundary = start + text[start..].chars().next()
                .context("Invalid replacement boundary")?.len_utf8();
            ensure!(!text[next_boundary..].contains(edit.old.as_str()),
                "Exact replacement is ambiguous");
            let end = start + edit.old.len();
            let size = text.len() - edit.old.len() + edit.new.len();
            ensure!(size <= MAX_FILE_BYTES, "Virtual file budget exceeded");
            state_bytes = state_bytes - text.len() + size;
            ensure!(state_bytes <= MAX_STATE_BYTES, "Virtual state budget exceeded");
            text.replace_range(start..end, &edit.new);
        }

        let edits = self.edits + batch.edits.len();
        let preview = self.build_preview(&next, edits)?;
        self.verify_fresh()?;
        self.current = next;
        self.edits = edits;
        self.edit_bytes = edit_bytes;
        Ok(preview)
    }

    /// Revalidate original snapshots before presenting a combined review.
    pub fn preview(&self) -> Result<Preview> {
        self.verify_fresh()?;
        let preview = self.build_preview(&self.current, self.edits)?;
        self.verify_fresh()?;
        Ok(preview)
    }

    fn build_preview(&self, state: &BTreeMap<String, String>, edits: usize) -> Result<Preview> {
        let mut files = Vec::new();
        let mut combined_diff = String::new();
        // BTreeMap gives stable path order independent of edit ordering.
        for (path, original) in &self.original {
            let proposed = &state[path];
            if original == proposed { continue; }
            let diff = TextDiff::from_lines(original, proposed).unified_diff()
                .header(&format!("a/{path}"), &format!("b/{path}")).to_string();
            ensure!(!diff.is_empty(), "Empty review diff");
            ensure!(combined_diff.len() + diff.len() <= MAX_DIFF_BYTES,
                "Combined diff exceeds review budget");
            combined_diff.push_str(&diff);
            files.push(FilePreview { path: path.clone(), original_sha256: digest(original),
                proposed_sha256: digest(proposed), proposed_bytes: proposed.len() });
        }
        ensure!(!files.is_empty(), "No net changes to review");
        Ok(Preview { files, edits, combined_diff })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    use std::fs;

    fn payload(edits: &[(&str, &str, &str)]) -> String {
        json!({"edits": edits.iter().map(|(path, old, new)|
            json!({"path":path,"old":old,"new":new})).collect::<Vec<_>>()}).to_string()
    }

    fn fixture() -> (tempfile::TempDir, Project, Vec<ReadResult>, Vec<String>) {
        let dir = tempfile::tempdir().unwrap();
        fs::write(dir.path().join("a.php"), "<?php\r\nreturn 'α';\r\n").unwrap();
        fs::write(dir.path().join("b.php"), "<?php\nreturn 10;\n").unwrap();
        fs::write(dir.path().join("support.php"), "<?php\nreturn 99;\n").unwrap();
        let project = Project::new(dir.path()).unwrap();
        let evidence = ["a.php", "b.php", "support.php"].iter()
            .map(|p| project.read(p).unwrap()).collect();
        (dir, project, evidence, vec!["a.php".into(), "b.php".into()])
    }

    #[test]
    fn two_files_and_sequential_virtual_edits_are_inert_and_deterministic() {
        let (dir, project, evidence, scope) = fixture();
        let mut w = VirtualWorkspace::new(&project, &evidence, &scope).unwrap();
        let preview = w.stage_json(&payload(&[("b.php", "10", "20"),
            ("a.php", "'α'", "'β'"), ("a.php", "'β'", "'γ'")])).unwrap();
        assert_eq!(preview.edits, 3);
        assert_eq!(preview.files.iter().map(|f| f.path.as_str()).collect::<Vec<_>>(),
            ["a.php", "b.php"]);
        assert_eq!(w.virtual_source("a.php").unwrap(), "<?php\r\nreturn 'γ';\r\n");
        assert_eq!(w.virtual_source("b.php").unwrap(), "<?php\nreturn 20;\n");
        assert_eq!(preview.files[0].original_sha256, digest(&evidence[0].text));
        assert_eq!(preview.files[0].proposed_sha256, digest(w.virtual_source("a.php").unwrap()));
        assert!(preview.combined_diff.contains("--- a/a.php"));
        assert!(preview.combined_diff.contains("+++ b/b.php"));
        assert_eq!(preview.combined_diff, w.preview().unwrap().combined_diff);
        assert_eq!(fs::read(dir.path().join("a.php")).unwrap(), evidence[0].text.as_bytes());
        assert_eq!(fs::read(dir.path().join("b.php")).unwrap(), evidence[1].text.as_bytes());
        assert_eq!(fs::read(dir.path().join("support.php")).unwrap(), evidence[2].text.as_bytes());
    }

    #[test]
    fn invalid_late_edit_does_not_publish_earlier_edits_or_spend_budget() {
        let (_dir, project, evidence, scope) = fixture();
        let mut w = VirtualWorkspace::new(&project, &evidence, &scope).unwrap();
        assert!(w.stage_json(&payload(&[("a.php", "'α'", "'β'"),
            ("support.php", "99", "0")])).is_err());
        assert_eq!(w.virtual_source("a.php").unwrap(), evidence[0].text);
        assert_eq!(w.edits, 0);
        assert_eq!(w.edit_bytes, 0);
        assert!(w.preview().is_err());
        w.stage_json(&payload(&[("a.php", "'α'", "'β'")])).unwrap();
        let before = w.preview().unwrap().combined_diff;
        assert!(w.stage_json(&payload(&[("b.php", "10", "20"), ("a.php", "missing", "x")])).is_err());
        assert_eq!(w.preview().unwrap().combined_diff, before);
        assert_eq!(w.virtual_source("b.php").unwrap(), evidence[1].text);
    }

    #[test]
    fn rejects_stale_support_and_target_at_construction_and_review() {
        let (dir, project, evidence, scope) = fixture();
        let mut w = VirtualWorkspace::new(&project, &evidence, &scope).unwrap();
        w.stage_json(&payload(&[("b.php", "10", "20")])).unwrap();
        fs::write(dir.path().join("support.php"), "changed").unwrap();
        assert!(w.preview().is_err());
        assert!(w.virtual_source("b.php").is_err());
        assert!(w.stage_json(&payload(&[("b.php", "20", "30")])).is_err());
        assert!(VirtualWorkspace::new(&project, &evidence, &scope).is_err());
        fs::write(dir.path().join("support.php"), &evidence[2].text).unwrap();
        fs::write(dir.path().join("b.php"), "changed").unwrap();
        assert!(w.preview().is_err());
    }

    #[test]
    fn rejects_unknown_duplicate_malformed_and_out_of_scope_actions() {
        let (_dir, project, evidence, scope) = fixture();
        let mut w = VirtualWorkspace::new(&project, &evidence, &scope).unwrap();
        for bad in [
            r#"{"edits":[]}"#,
            r#"{"edits":[{"path":"b.php","old":"10","new":"20","command":"php"}]}"#,
            r#"{"edits":[{"path":"b.php","path":"a.php","old":"10","new":"20"}]}"#,
            r#"{"edits":[],"edits":[{"path":"b.php","old":"10","new":"20"}]}"#,
            r#"{"edits":[{"path":"b.php","old":"10","new":20}]}"#,
            r#"{"edits":[{"path":"b.php","old":"","new":"20"}]}"#,
            r#"{"edits":[{"path":"b.php","old":"10","new":"10"}]}"#,
            r#"{"edits":[{"path":"b.php","old":"10","new":"\u0000"}]}"#,
            r#"{"edits":[{"path":"./b.php","old":"10","new":"20"}]}"#,
            r#"{"edits":[{"path":"../b.php","old":"10","new":"20"}]}"#,
            r#"{"edits":[{"path":"B.php","old":"10","new":"20"}]}"#,
            r#"{"edits":[{"path":"new.php","old":"10","new":"20"}]}"#,
            "Here is JSON: {}",
        ] {
            assert!(w.stage_json(bad).is_err(), "accepted {bad}");
        }
        assert_eq!(w.edits, 0);
        assert_eq!(w.virtual_source("b.php").unwrap(), evidence[1].text);
    }

    #[test]
    fn rejects_ambiguous_overlapping_fragments_and_net_zero() {
        let dir = tempfile::tempdir().unwrap();
        fs::write(dir.path().join("a.txt"), "aaa\n").unwrap();
        let project = Project::new(dir.path()).unwrap();
        let reads = [project.read("a.txt").unwrap()];
        let scope = ["a.txt".to_owned()];
        let mut w = VirtualWorkspace::new(&project, &reads, &scope).unwrap();
        assert!(w.stage_json(&payload(&[("a.txt", "aa", "b")])).is_err());
        assert!(w.stage_json(&payload(&[("a.txt", "aaa", "b"), ("a.txt", "b", "aaa")])).is_err());
        assert_eq!(w.virtual_source("a.txt").unwrap(), "aaa\n");
        w.stage_json(&payload(&[("a.txt", "aaa", "")])).unwrap();
        assert_eq!(w.virtual_source("a.txt").unwrap(), "\n");
    }

    #[test]
    fn scope_and_evidence_must_be_complete_unique_and_project_bound() {
        let (_dir, project, evidence, scope) = fixture();
        assert!(VirtualWorkspace::new(&project, &evidence, &[]).is_err());
        assert!(VirtualWorkspace::new(&project, &evidence, &["missing.php".into()]).is_err());
        assert!(VirtualWorkspace::new(&project, &evidence, &["a.php".into(), "a.php".into()]).is_err());
        let duplicate = [project.read("a.php").unwrap(), project.read("a.php").unwrap()];
        assert!(VirtualWorkspace::new(&project, &duplicate, &scope[..1]).is_err());
        let incomplete = [ReadResult {path:"a.php".into(), text:evidence[0].text.clone(), truncated:true}];
        assert!(VirtualWorkspace::new(&project, &incomplete, &scope[..1]).is_err());
        let other = tempfile::tempdir().unwrap();
        fs::write(other.path().join("a.php"), "different").unwrap();
        let other_project = Project::new(other.path()).unwrap();
        assert!(VirtualWorkspace::new(&other_project, &evidence[..1], &scope[..1]).is_err());
    }

    #[test]
    fn cumulative_edit_count_and_payload_budget_are_enforced() {
        let (_dir, project, evidence, scope) = fixture();
        let mut w = VirtualWorkspace::new(&project, &evidence, &scope).unwrap();
        assert!(w.stage_json(&" ".repeat(MAX_JSON_BYTES + 1)).is_err());
        let oversized = "x".repeat(MAX_FRAGMENT_BYTES + 1);
        assert!(w.stage_json(&payload(&[("b.php", "10", &oversized)])).is_err());
        let mut old = "10".to_owned();
        for i in 0..MAX_EDITS {
            let new = format!("value_{i}");
            w.stage_json(&payload(&[("b.php", &old, &new)])).unwrap();
            old = new;
        }
        assert!(w.stage_json(&payload(&[("b.php", &old, "last")])).is_err());
        assert_eq!(w.preview().unwrap().edits, MAX_EDITS);
        assert!(w.virtual_source("b.php").unwrap().contains(&old));
    }

    #[test]
    fn virtual_file_and_diff_limits_are_atomic() {
        let dir = tempfile::tempdir().unwrap();
        let original = format!("start{}", "z".repeat(MAX_FILE_BYTES - 5));
        fs::write(dir.path().join("a.txt"), &original).unwrap();
        let p = Project::new(dir.path()).unwrap();
        let evidence = [p.read("a.txt").unwrap()];
        let mut w = VirtualWorkspace::new(&p, &evidence, &["a.txt".into()]).unwrap();
        assert!(w.stage_json(&payload(&[("a.txt", "start", "longer")])).is_err());
        // A single changed long line produces a diff above the review cap.
        assert!(w.stage_json(&payload(&[("a.txt", "start", "other")])).is_err());
        assert_eq!(w.virtual_source("a.txt").unwrap(), original);
        assert_eq!(w.edits, 0);
    }

    #[test]
    fn cumulative_fragment_bytes_are_enforced_across_batches() {
        let dir = tempfile::tempdir().unwrap();
        let mut old = "a".repeat(MAX_FRAGMENT_BYTES);
        fs::write(dir.path().join("a.txt"), &old).unwrap();
        let p = Project::new(dir.path()).unwrap();
        let reads = [p.read("a.txt").unwrap()];
        let mut w = VirtualWorkspace::new(&p, &reads, &["a.txt".into()]).unwrap();
        for ch in ["b", "c", "d", "e"] {
            let new = ch.repeat(MAX_FRAGMENT_BYTES);
            w.stage_json(&payload(&[("a.txt", &old, &new)])).unwrap();
            old = new;
        }
        assert_eq!(w.edit_bytes, MAX_EDIT_BYTES);
        let before = w.preview().unwrap().combined_diff;
        assert!(w.stage_json(&payload(&[("a.txt", &old, "x")])).is_err());
        assert_eq!(w.preview().unwrap().combined_diff, before);
        assert_eq!(w.edits, 4);
    }

    #[test]
    fn combined_source_budget_applies_to_evidence_and_virtual_growth() {
        let dir = tempfile::tempdir().unwrap();
        let p = Project::new(dir.path()).unwrap();
        let names = ["a.txt", "b.txt", "c.txt", "d.txt", "e.txt"];
        let large = "z".repeat(MAX_FILE_BYTES);
        for name in &names[..3] {
            fs::write(dir.path().join(name), &large).unwrap();
        }
        let half = format!("start{}", "z".repeat(MAX_FILE_BYTES / 2 - 5));
        for name in &names[3..] {
            fs::write(dir.path().join(name), &half).unwrap();
        }
        let reads: Vec<_> = names.iter().map(|name| p.read(name).unwrap()).collect();
        let mut w = VirtualWorkspace::new(&p, &reads, &["d.txt".into()]).unwrap();
        assert!(w.stage_json(&payload(&[("d.txt", "start", "longer")])).is_err());
        assert_eq!(w.virtual_source("d.txt").unwrap(), half);
        assert_eq!(w.edits, 0);
        fs::write(dir.path().join("e.txt"), &large).unwrap();
        let oversized: Vec<_> = names.iter().map(|name| p.read(name).unwrap()).collect();
        assert!(VirtualWorkspace::new(&p, &oversized, &["d.txt".into()]).is_err());
    }

    #[cfg(unix)]
    #[test]
    fn linked_source_is_rejected_even_with_fabricated_complete_evidence() {
        use std::os::unix::fs::symlink;
        let (dir, p, evidence, scope) = fixture();
        fs::remove_file(dir.path().join("a.php")).unwrap();
        symlink(dir.path().join("b.php"), dir.path().join("a.php")).unwrap();
        assert!(VirtualWorkspace::new(&p, &evidence, &scope).is_err());
        fs::remove_file(dir.path().join("a.php")).unwrap();
        fs::hard_link(dir.path().join("b.php"), dir.path().join("a.php")).unwrap();
        assert!(VirtualWorkspace::new(&p, &evidence, &scope).is_err());
    }
}
