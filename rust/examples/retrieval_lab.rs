//! Model-free lab retrieval probe. No target paths, fixture answers or runtime.
use anyhow::{ensure, Result};
use clap::Parser;
use serde_json::json;
use std::{path::PathBuf, time::Instant};
use tinybuilder::{context::{retrieve_lab, retrieve_lab_aligned, LabRetrieval}, project::Project};

#[derive(Parser)]
struct Args {
    #[arg(long)]
    project: PathBuf,
    #[arg(long, value_enum)]
    strategy: LabRetrieval,
    /// Compare identifier-aligned excerpts with the same normalized ranking.
    #[arg(long)]
    align_excerpts: bool,
    /// Give identifier matches on code lines more weight than line comments.
    #[arg(long, requires = "align_excerpts")]
    prefer_code_anchors: bool,
    task: String,
}

fn main() -> Result<()> {
    let args = Args::parse();
    ensure!(!args.align_excerpts || args.strategy == LabRetrieval::Normalized,
        "Excerpt alignment requires the normalized strategy");
    let project = Project::new(&args.project)?;
    let mut rows = Vec::new();
    for _ in 0..3 {
        let start = Instant::now();
        let result = if args.align_excerpts {
            retrieve_lab_aligned(&project, &args.task, args.prefer_code_anchors)
        } else {
            retrieve_lab(&project, &args.task, args.strategy)
        };
        let elapsed_us = start.elapsed().as_micros() as u64;
        let mut observation = match result {
            Ok(context) => json!({
                "status": "selected", "elapsed_us": elapsed_us, "incomplete": context.incomplete,
                "files": context.files.iter().zip(&context.ranges).map(|(file, (first, last))| json!({
                    "path": file.path, "complete": !file.truncated, "bytes": file.text.len(),
                    "first_line": first, "last_line": last
                })).collect::<Vec<_>>()
            }),
            Err(_) => json!({"status": "no_context", "elapsed_us": elapsed_us, "files": []}),
        };
        observation["peak_rss_bytes"] = json!(peak_rss_bytes());
        rows.push(observation);
    }
    println!("{}", json!(rows));
    Ok(())
}

#[cfg(windows)]
fn peak_rss_bytes() -> Option<usize> {
    use std::ffi::c_void;
    use std::mem::size_of;

    #[repr(C)]
    #[derive(Default)]
    struct ProcessMemoryCounters {
        size: u32,
        page_fault_count: u32,
        peak_working_set: usize,
        working_set: usize,
        peak_paged_pool: usize,
        paged_pool: usize,
        peak_nonpaged_pool: usize,
        nonpaged_pool: usize,
        pagefile_usage: usize,
        peak_pagefile_usage: usize,
    }
    #[link(name = "kernel32")]
    extern "system" {
        fn GetCurrentProcess() -> *mut c_void;
        fn K32GetProcessMemoryInfo(
            process: *mut c_void,
            counters: *mut ProcessMemoryCounters,
            size: u32,
        ) -> i32;
    }

    let size = size_of::<ProcessMemoryCounters>() as u32;
    let mut counters = ProcessMemoryCounters { size, ..Default::default() };
    // Use the current process pseudo-handle and a writable ABI-sized buffer.
    let available = unsafe { K32GetProcessMemoryInfo(GetCurrentProcess(), &mut counters, size) };
    (available != 0).then_some(counters.peak_working_set)
}

#[cfg(target_os = "linux")]
fn peak_rss_bytes() -> Option<usize> {
    let status = std::fs::read_to_string("/proc/self/status").ok()?;
    let peak = status.lines().find_map(|line| line.strip_prefix("VmHWM:"))?;
    Some(peak.split_whitespace().next()?.parse::<usize>().ok()? * 1024)
}

#[cfg(not(any(windows, target_os = "linux")))]
fn peak_rss_bytes() -> Option<usize> {
    None
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn frozen_strategies_do_not_surface_parent_restricted_or_linked_sources() {
        let temp = tempfile::tempdir().unwrap();
        let root = temp.path().join("source");
        fs::create_dir(&root).unwrap();
        let outside = temp.path().join("outside.rs");
        fs::write(&outside, "pub fn canary_token() {}").unwrap();
        fs::write(root.join(".env"), "canary_token=outside").unwrap();
        fs::hard_link(&outside, root.join("linked.rs")).unwrap();
        let project = Project::new(&root).unwrap();
        for arm in <LabRetrieval as clap::ValueEnum>::value_variants() {
            assert!(retrieve_lab(&project, "Find canary_token in ../outside.rs or .env", *arm).is_err());
        }
        for prefer_code in [false, true] {
            assert!(retrieve_lab_aligned(&project, "Find canary_token in ../outside.rs or .env", prefer_code).is_err());
        }
    }
}
