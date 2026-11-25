//! Bounded, ignore-aware local tools. No shell or implicit writes.
use anyhow::{bail, ensure, Context, Result};
use ignore::WalkBuilder;
use rayon::prelude::*;
use sha2::{Digest, Sha256};
use similar::TextDiff;
use std::{
    fs::{self, File, Metadata},
    io::{Read, Write},
    path::{Component, Path, PathBuf},
};
use tempfile::NamedTempFile;

const READ_MAX: usize = 32 * 1024;
const PATCH_MAX: usize = 256 * 1024;
const SEARCH_MAX: usize = 256 * 1024;
const SCAN_MAX: usize = 4096;
const LIST_MAX: usize = 150;
const MATCH_MAX: usize = 30;

#[derive(Debug)]
pub struct Project {
    root: PathBuf,
}
pub struct ReadResult {
    pub path: String,
    pub text: String,
    pub truncated: bool,
}
pub struct Patch {
    path: String,
    original_hash: [u8; 32],
    replacement: String,
    pub diff: String,
}
fn link_like(meta: &Metadata) -> bool {
    if meta.file_type().is_symlink() {
        return true;
    }
    #[cfg(windows)]
    {
        use std::os::windows::fs::MetadataExt;
        if meta.file_attributes() & 0x400 != 0 {
            return true;
        }
    }
    false
}

fn forbidden_name(name: &str) -> bool {
    let lower = name.to_ascii_lowercase();
    let stem = lower.split('.').next().unwrap_or("");
    lower == ".git" || lower == ".env" || lower.starts_with(".env.")
        || lower.ends_with(".gguf") || lower.ends_with(".safetensors")
        || lower.ends_with(".pem") || lower.ends_with(".key")
        || lower.ends_with(".pfx") || lower.ends_with(".p12")
        || name.contains(':') || name.contains('\\') || name.ends_with('.') || name.ends_with(' ')
        || name.chars().any(char::is_control)
        || matches!(stem, "con" | "prn" | "aux" | "nul")
        || (stem.len() == 4 && (stem.starts_with("com") || stem.starts_with("lpt"))
            && matches!(stem.as_bytes()[3], b'1'..=b'9'))
}

fn read_bounded(path: &Path, max: usize) -> Result<(Vec<u8>, bool)> {
    let mut bytes = Vec::new();
    let file = File::open(path)?;
    ensure!(file.metadata()?.is_file(), "Not a regular file");
    // A hard link can expose a file outside the selected project without
    // traversing a symlink. Conservatively reject it for reads and edits.
    ensure_single_link(&file)?;
    file.take(max as u64 + 1).read_to_end(&mut bytes)?;
    let truncated = bytes.len() > max;
    bytes.truncate(max);
    Ok((bytes, truncated))
}
fn utf8(bytes: &[u8], truncated: bool) -> Result<String> {
    ensure!(!bytes.contains(&0), "Binary file rejected");
    match std::str::from_utf8(bytes) {
        Ok(s) => Ok(s.to_owned()),
        Err(e) if truncated && e.error_len().is_none() => {
            Ok(std::str::from_utf8(&bytes[..e.valid_up_to()])?.to_owned())
        }
        Err(_) => bail!("Not UTF-8 text"),
    }
}
#[cfg(unix)]
fn ensure_single_link(file: &File) -> Result<()> {
    use std::os::unix::fs::MetadataExt;
    ensure!(file.metadata()?.nlink() == 1, "Hard-linked file rejected");
    Ok(())
}

#[cfg(windows)]
fn ensure_single_link(file: &File) -> Result<()> {
    use std::{ffi::c_void, os::windows::io::AsRawHandle};
    // BY_HANDLE_FILE_INFORMATION consists of 13 DWORDs (FILETIMEs are
    // pairs of DWORDs). nNumberOfLinks is DWORD index 10.
    #[link(name = "kernel32")]
    extern "system" {
        fn GetFileInformationByHandle(handle: *mut c_void, info: *mut u32) -> i32;
    }
    let mut info = [0u32; 13];
    let ok = unsafe { GetFileInformationByHandle(file.as_raw_handle(), info.as_mut_ptr()) };
    ensure!(ok != 0 && info[10] == 1, "Cannot verify single-link file");
    Ok(())
}

fn hash(bytes: &[u8]) -> [u8; 32] {
    Sha256::digest(bytes).into()
}

impl Project {
    pub fn new(root: &Path) -> Result<Self> {
        let root = root.canonicalize().context("Project unavailable")?;
        ensure!(root.is_dir(), "Project must be a directory");
        Ok(Self { root })
    }
    pub fn root(&self) -> &Path {
        &self.root
    }
    // Reject traversal, alternate streams, links and Windows reparse points.
    // This is a local permission boundary, not an OS sandbox or race-proof
    // openat implementation. Do not use against a hostile concurrent writer.
    fn resolve(&self, relative: &str) -> Result<PathBuf> {
        ensure!(!relative.trim().is_empty() && relative.len() <= 4096, "Invalid path");
        let mut path = self.root.clone();
        for part in Path::new(relative).components() {
            match part {
                Component::CurDir => continue,
                Component::Normal(name) => {
                    let name = name.to_str().context("Non-UTF-8 path")?;
                    ensure!(!forbidden_name(name), "Restricted path");
                    path.push(name);
                    ensure!(!link_like(&fs::symlink_metadata(&path)?), "Link rejected");
                }
                _ => bail!("Only project-relative paths are allowed"),
            }
        }
        let path = path.canonicalize()?;
        ensure!(path.starts_with(&self.root), "Path escapes project");
        // Check canonical names too, including Windows short-name aliases.
        for part in path.strip_prefix(&self.root)?.components() {
            if let Component::Normal(name) = part {
                ensure!(!forbidden_name(name.to_str().context("Non-UTF-8 path")?), "Restricted canonical path");
            }
        }
        Ok(path)
    }
    fn relative(&self, path: &Path) -> Result<String> {
        Ok(path.strip_prefix(&self.root)?.to_str().context("Non-UTF-8 path")?
            .replace('\\', "/"))
    }
    pub fn read(&self, relative: &str) -> Result<ReadResult> {
        let path = self.resolve(relative)?;
        ensure!(path.is_file(), "Not a regular file");
        let (bytes, truncated) = read_bounded(&path, READ_MAX)?;
        Ok(ReadResult { path: self.relative(&path)?, text: utf8(&bytes, truncated)?, truncated })
    }

    fn candidates(&self, relative: &str) -> Result<(Vec<String>, bool)> {
        let dir = self.resolve(relative)?;
        ensure!(dir.is_dir(), "Not a directory");
        let root = dir.clone();
        let mut walk = WalkBuilder::new(&dir);
        walk.hidden(true).follow_links(false).git_ignore(true).git_global(false)
            .git_exclude(true).require_git(false).parents(false).sort_by_file_path(|a, b| a.cmp(b))
            .filter_entry(move |entry| {
                if entry.path() == root { return true; }
                let name = entry.file_name().to_str().unwrap_or("");
                !name.is_empty() && !forbidden_name(name)
                    && !matches!(name, "node_modules" | "vendor" | "target" | "__pycache__" | "dist" | "build")
                    && entry.path().symlink_metadata().map(|m| !link_like(&m)).unwrap_or(false)
            });
        let mut result = Vec::new();
        let mut visited = 0;
        let mut limited = false;
        for entry in walk.build() {
            visited += 1;
            if visited > SCAN_MAX { limited = true; break; }
            let entry = match entry {
                Ok(entry) => entry,
                Err(_) => { limited = true; continue; }
            };
            if entry.file_type().is_some_and(|t| t.is_file()) {
                if let Ok(rel) = self.relative(entry.path()) { result.push(rel); }
            }
        }
        Ok((result, limited))
    }
    pub fn list(&self, relative: &str) -> Result<String> {
        let (mut files, limited) = self.candidates(relative)?;
        let truncated = limited || files.len() > LIST_MAX;
        files.truncate(LIST_MAX);
        let mut out = files.join("\n");
        if truncated { out.push_str("\n[Listing incomplete: scan or output limit]"); }
        Ok(out)
    }
    pub fn search(&self, query: &str) -> Result<String> {
        ensure!(!query.trim().is_empty() && query.len() <= 200, "Invalid search query");
        let (files, limited) = self.candidates(".")?;
        let rows: Vec<(Vec<String>, bool)> = files.par_iter().map(|rel| {
            let result = (|| -> Result<(Vec<String>, bool)> {
                let path = self.resolve(rel)?;
                ensure!(path.is_file(), "Not a file");
                let (bytes, truncated) = read_bounded(&path, SEARCH_MAX)?;
                let text = utf8(&bytes, truncated)?;
                let mut hits = Vec::new();
                for (i, line) in text.lines().enumerate() {
                    if line.contains(query) {
                        hits.push(format!("{}:{}: {}", rel, i + 1, line.chars().take(200).collect::<String>()));
                        if hits.len() > MATCH_MAX { break; }
                    }
                }
                Ok((hits, truncated))
            })();
            result.unwrap_or_else(|_| (Vec::new(), true))
        }).collect();
        let mut out = Vec::new();
        let mut incomplete = limited;
        for (hits, partial) in rows {
            incomplete |= partial;
            for hit in hits {
                if out.len() == MATCH_MAX { incomplete = true; break; }
                out.push(hit);
            }
        }
        if incomplete { out.push("[Search incomplete: skipped file, scan or output limit]".into()); }
        Ok(out.join("\n"))
    }

    /// Typed lexical ranking for context retrieval; scan each candidate once.
    /// Unlike parsing formatted search output, paths and scores stay separate.
    pub(crate) fn ranked_candidates(&self, terms: &[String], task: &str) -> Result<(Vec<(String,u32)>, bool)> {
        ensure!(terms.len()<=4 && terms.iter().all(|t|!t.is_empty() && t.len()<=80), "Invalid ranking terms");
        let (files, limited) = self.candidates(".")?;
        let lower_task = task.to_ascii_lowercase();
        let rows: Vec<(String,u32,bool)> = files.par_iter().map(|rel| {
            let lower = rel.to_ascii_lowercase();
            let basename = lower.rsplit('/').next().unwrap_or(&lower);
            let mut score = if lower_task.contains(&lower) {100} else {0};
            for term in terms {
                if lower.contains(&term.to_ascii_lowercase()) {score+=10;}
            }
            if matches!(basename,"readme.md"|"cargo.toml"|"pyproject.toml"|"composer.json"|"package.json"|"go.mod") {score+=2;}
            let scan = (|| -> Result<(u32,bool)> {
                if terms.is_empty() {return Ok((0,false));}
                let path=self.resolve(rel)?;
                ensure!(path.is_file(),"Not a file");
                let (bytes,truncated)=read_bounded(&path,SEARCH_MAX)?;
                let text=utf8(&bytes,truncated)?;
                let hits=terms.iter().filter(|t|text.contains(t.as_str())).count();
                Ok((hits as u32*5,truncated))
            })();
            let (hits,partial)=scan.unwrap_or((0,true));
            (rel.clone(),score+hits,partial)
        }).collect();
        let incomplete = limited || rows.iter().any(|r|r.2);
        Ok((rows.into_iter().filter(|r|r.1>0).map(|(path,score,_)|(path,score)).collect(),incomplete))
    }

    // Existing text files only; exact unique replacement avoids model-generated
    // whole-file rewrites. Review is separate from commit.
    pub fn propose(&self, path: &str, old: &str, new: &str) -> Result<Patch> {
        self.propose_checked(path, old, new, None)
    }
    /// Bind the proposal to the exact complete evidence supplied to the model.
    pub fn propose_from_read(&self, read: &ReadResult, old: &str, new: &str) -> Result<Patch> {
        ensure!(!read.truncated,"Cannot patch truncated evidence");
        self.propose_checked(&read.path,old,new,Some(hash(read.text.as_bytes())))
    }
    fn propose_checked(&self,path: &str, old: &str, new: &str, expected: Option<[u8;32]>) -> Result<Patch> {
        ensure!(!old.is_empty() && old.len() <= PATCH_MAX && new.len() <= PATCH_MAX && !new.contains('\0'), "Invalid replacement");
        let resolved = self.resolve(path)?;
        ensure!(resolved.is_file(), "Not a regular file");
        let (bytes, truncated) = read_bounded(&resolved, PATCH_MAX)?;
        ensure!(!truncated, "File too large for patch");
        ensure!(expected.is_none_or(|value|value==hash(&bytes)), "File changed since context selection");
        let content = utf8(&bytes, false)?;
        ensure!(old != new, "No change");
        // Count overlapping occurrences as ambiguous too.
        ensure!(content.char_indices().filter(|(i, _)| content[*i..].starts_with(old)).take(2).count() == 1,
            "Replacement must match exactly once");
        let replacement = content.replacen(old, new, 1);
        ensure!(replacement.len() <= PATCH_MAX, "Replacement too large");
        let diff = TextDiff::from_lines(&content, &replacement).unified_diff()
            .header("before", "after").to_string();
        ensure!(!diff.is_empty(), "No change");
        ensure!(diff.len() <= 64 * 1024, "Diff too large to review");
        Ok(Patch { path: self.relative(&resolved)?, original_hash: hash(&bytes), replacement, diff })
    }
    pub fn apply(&self, patch: Patch, approved: bool) -> Result<()> {
        ensure!(approved, "Permission denied");
        let path = self.resolve(&patch.path)?;
        ensure!(path.is_file(), "Not a regular file");
        let (bytes, truncated) = read_bounded(&path, PATCH_MAX)?;
        ensure!(!truncated && hash(&bytes) == patch.original_hash, "File changed after review");
        let original = File::open(&path)?;
        ensure_single_link(&original)?;
        let metadata = original.metadata()?;
        let permissions = metadata.permissions();
        ensure!(!permissions.readonly(), "File is read-only");
        let mut tmp = NamedTempFile::new_in(path.parent().context("Missing parent")?)?;
        tmp.write_all(patch.replacement.as_bytes())?;
        #[cfg(unix)]
        {
            use std::os::unix::fs::MetadataExt;
            let staged = tmp.as_file().metadata()?;
            ensure!(metadata.uid() == staged.uid() && metadata.gid() == staged.gid(),
                "Ownership would change");
            ensure!(metadata.mode() & 0o7000 == 0, "Special mode bits rejected");
        }
        tmp.as_file().set_permissions(permissions)?;
        tmp.as_file().sync_all()?;
        let current = self.resolve(&patch.path)?;
        let (bytes, truncated) = read_bounded(&current, PATCH_MAX)?;
        ensure!(current == path && !truncated && hash(&bytes) == patch.original_hash, "File changed before commit");
        ensure_single_link(&File::open(&current)?)?;
        drop(original);
        tmp.persist(&path).map_err(|_| anyhow::anyhow!("Atomic replacement failed"))?;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn exact_read_search_patch_and_denial() {
        let dir = tempfile::tempdir().unwrap();
        fs::write(dir.path().join("a.txt"), "alpha\nbeta\n").unwrap();
        fs::write(dir.path().join(".gitignore"), "ignored.txt\n").unwrap();
        fs::write(dir.path().join("ignored.txt"), "alpha").unwrap();
        let p = Project::new(dir.path()).unwrap();
        assert_eq!(p.read("a.txt").unwrap().text, "alpha\nbeta\n");
        assert!(p.search("alpha").unwrap().contains("a.txt:1"));
        assert!(!p.search("alpha").unwrap().contains("ignored.txt"));
        assert!(p.read("../a.txt").is_err());
        assert!(p.propose("a.txt", "missing", "new").is_err());
        assert!(p.apply(p.propose("a.txt", "alpha", "gamma").unwrap(), false).is_err());
        assert_eq!(p.read("a.txt").unwrap().text, "alpha\nbeta\n");
        p.apply(p.propose("a.txt", "alpha", "gamma").unwrap(), true).unwrap();
        assert_eq!(p.read("a.txt").unwrap().text, "gamma\nbeta\n");
    }
    #[test]
    fn stale_patch_denied_and_secret_rejected() {
        let dir = tempfile::tempdir().unwrap();
        fs::write(dir.path().join("a.txt"), "old").unwrap();
        fs::write(dir.path().join(".env"), "secret").unwrap();
        let p = Project::new(dir.path()).unwrap();
        let patch = p.propose("a.txt", "old", "new").unwrap();
        fs::write(dir.path().join("a.txt"), "changed").unwrap();
        assert!(p.apply(patch, true).is_err());
        assert!(p.read(".env").is_err());
        assert_eq!(p.read("a.txt").unwrap().text, "changed");
    }
    #[test]
    fn rejects_hardlink_and_overlapping_replacements() {
        let dir = tempfile::tempdir().unwrap();
        let a = dir.path().join("a.txt");
        let b = dir.path().join("b.txt");
        fs::write(&a, "aaa").unwrap();
        fs::hard_link(&a, &b).unwrap();
        let p = Project::new(dir.path()).unwrap();
        assert!(p.propose("a.txt", "aa", "x").is_err());
        assert!(p.read("a.txt").is_err());
        assert!(p.propose("a.txt", "aaa", "b").is_err());
        assert_eq!(fs::read_to_string(&a).unwrap(), "aaa");
        assert_eq!(fs::read_to_string(&b).unwrap(), "aaa");
    }
    #[test]
    fn proposal_is_bound_to_original_evidence_and_text_only() {
        let dir=tempfile::tempdir().unwrap();
        fs::write(dir.path().join("a.txt"),"old").unwrap();
        let p=Project::new(dir.path()).unwrap();
        let source=p.read("a.txt").unwrap();
        assert!(p.propose("a.txt","old","\0").is_err());
        fs::write(dir.path().join("a.txt"),"old plus another change").unwrap();
        assert!(p.propose_from_read(&source,"old","new").is_err());
        assert_eq!(p.read("a.txt").unwrap().text,"old plus another change");
    }
    #[cfg(unix)]
    #[test]
    fn rejects_symlinks() {
        let root = tempfile::tempdir().unwrap();
        let outside = tempfile::tempdir().unwrap();
        fs::write(outside.path().join("a.txt"), "secret").unwrap();
        std::os::unix::fs::symlink(outside.path(), root.path().join("link")).unwrap();
        assert!(Project::new(root.path()).unwrap().read("link/a.txt").is_err());
    }
}
