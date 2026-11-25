//! Model-free in-process latency measurement on a disposable fixture.
use anyhow::{ensure, Context, Result};
use serde_json::json;
use std::{path::PathBuf, time::Instant};
use tinybuilder::project::Project;

fn measure<T>(count: usize, mut operation: impl FnMut() -> Result<T>) -> Result<(u64,u64)> {
    let mut values = Vec::with_capacity(count);
    for _ in 0..count {
        let start = Instant::now();
        std::hint::black_box(operation()?);
        values.push(start.elapsed().as_nanos().min(u64::MAX as u128) as u64);
    }
    values.sort_unstable();
    Ok((values[(count - 1) / 2], values[(count * 95).div_ceil(100) - 1]))
}
fn main() -> Result<()> {
    let root = PathBuf::from(std::env::args_os().nth(1).context("Disposable fixture root required")?);
    let p = Project::new(&root)?;
    ensure!(p.read("probe.txt")?.text == "tinybuilder-bench-marker\n", "Unexpected fixture");
    // The fixture generator places only one occurrence of the marker.
    ensure!(p.search("tinybuilder-bench-marker")? == "probe.txt:1: tinybuilder-bench-marker", "Search result mismatch");
    let read = measure(1000, || p.read("probe.txt"))?;
    let search = measure(20, || p.search("tinybuilder-bench-marker"))?;
    let patch = measure(100, || {
        let change = p.propose("patch.txt", "original", "updated")?;
        p.apply(change, true)?;
        ensure!(p.read("patch.txt")?.text == "updated\n", "Patch verification failed");
        let revert = p.propose("patch.txt", "updated", "original")?;
        p.apply(revert, true)
    })?;
    ensure!(p.read("patch.txt")?.text == "original\n", "Fixture restoration failed");
    println!("{}", json!({"unit":"ns","cache":"warm; OS cache not controlled",
        "read":{"trials":1000,"p50":read.0,"p95":read.1},
        "search":{"trials":20,"p50":search.0,"p95":search.1},
        "patch_and_restore":{"trials":100,"p50":patch.0,"p95":patch.1}}));
    Ok(())
}
