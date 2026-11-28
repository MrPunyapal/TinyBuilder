//! Supervisor of fixed, reviewed controls. This is NOT an outer security boundary.
use crate::{bounded_read, BackendIdentity, Cleanup, ControlRecord, Failure, Observation,
    Probe, QualificationRecord, Request, ResultKind, WorkerReply, WATCHDOG_READY};
use std::{io::Write, path::{Path, PathBuf}, process::{Child, Command, ExitStatus, Stdio},
    sync::mpsc, thread, time::{Duration, Instant}};

pub fn sibling_worker() -> std::io::Result<PathBuf> {
    let mut path = std::env::current_exe()?;
    path.set_file_name(format!("portable-evaluator-worker{}", std::env::consts::EXE_SUFFIX));
    Ok(path)
}

fn ms(start: Instant) -> u64 { start.elapsed().as_millis().min(u64::MAX as u128) as u64 }

fn wait_until(child: &mut Child, deadline: Instant) -> std::io::Result<Option<ExitStatus>> {
    loop {
        if let Some(status) = child.try_wait()? { return Ok(Some(status)); }
        if Instant::now() >= deadline { return Ok(None); }
        thread::sleep(Duration::from_millis(10));
    }
}

fn kill_and_reap(child: &mut Child) -> bool {
    // A race between exit and kill is harmless only if try_wait proves reaping.
    let _ = child.kill();
    matches!(wait_until(child, Instant::now() + Duration::from_secs(5)), Ok(Some(_)))
}

pub fn run_control(worker: &Path, request: Request) -> ControlRecord {
    let start = Instant::now();
    let blocked = |request, failure, cleanup| ControlRecord::new(request,
        ResultKind::Blocked(failure), cleanup, ms(start));
    let actual = match BackendIdentity::for_worker(worker) {
        Ok(id) => id,
        Err(_) => return blocked(request, Failure::IdentityMismatch, Cleanup::NotStarted),
    };
    if let Err(failure) = request.validate(&actual) {
        return blocked(request, failure, Cleanup::NotStarted);
    }
    let bytes = match serde_json::to_vec(&request) {
        Ok(bytes) if bytes.len() <= crate::MAX_MESSAGE => bytes,
        _ => return blocked(request, Failure::WorkerProtocol, Cleanup::NotStarted),
    };
    let scratch = match tempfile::tempdir() {
        Ok(dir) => dir,
        Err(_) => return blocked(request, Failure::ScratchUnavailable, Cleanup::NotStarted),
    };
    let worker = match worker.canonicalize() {
        Ok(path) => path,
        Err(_) => {
            let cleanup = if scratch.close().is_ok() { Cleanup::NotStarted } else { Cleanup::Unverified };
            return blocked(request, Failure::IdentityMismatch, cleanup);
        }
    };
    let mut child = match Command::new(worker).current_dir(scratch.path()).env_clear()
        .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn() {
        Ok(child) => child,
        Err(_) => {
            let cleanup = if scratch.close().is_ok() { Cleanup::NotStarted } else { Cleanup::Unverified };
            return blocked(request, Failure::WorkerStart, cleanup);
        }
    };

    let (tx, rx) = mpsc::sync_channel(1);
    if let Some(stdout) = child.stdout.take() {
        // Fixed output bound; closing the pipe on overflow prevents unbounded collection.
        thread::spawn(move || { let _ = tx.send(bounded_read(stdout)); });
    } else { drop(tx); }
    // Small fixed JSON, written once, then close stdin. Worker reads to EOF.
    let sent = child.stdin.take().is_some_and(|mut stdin| stdin.write_all(&bytes).is_ok());
    let deadline = start + Duration::from_millis(request.limits.wall_ms);
    let waited = if sent { wait_until(&mut child, deadline) } else { Ok(None) };
    let (status, timed_out, wait_error) = match waited {
        Ok(Some(status)) => (Some(status), false, false),
        Ok(None) => (None, sent, false),
        Err(_) => (None, false, true),
    };
    if status.is_none() && !kill_and_reap(&mut child) {
        // Do not erase a potentially active worker's directory. Stop the suite.
        let _ = scratch.keep();
        return blocked(request, Failure::CleanupUnverified, Cleanup::Unverified);
    }
    let output = rx.recv_timeout(Duration::from_secs(2)).ok().and_then(Result::ok);
    let cleanup = if scratch.close().is_ok() {
        Cleanup::DirectChildReapedAndScratchRemoved
    } else { Cleanup::Unverified };
    if cleanup == Cleanup::Unverified {
        return blocked(request, Failure::CleanupUnverified, cleanup);
    }
    if !sent || wait_error {
        return blocked(request, Failure::WorkerProtocol, cleanup);
    }
    if timed_out {
        if request.probe == Probe::Watchdog && output.as_deref() == Some(WATCHDOG_READY) {
            return ControlRecord::new(request, ResultKind::Observed(Observation::WatchdogKilled), cleanup, ms(start));
        }
        return blocked(request, Failure::InfrastructureTimeout, cleanup);
    }
    if !status.is_some_and(|s| s.success()) {
        return blocked(request, Failure::WorkerExit, cleanup);
    }
    let reply = match output.and_then(|bytes| serde_json::from_slice::<WorkerReply>(&bytes).ok()) {
        Some(reply) if reply.request == request && reply.observation != Observation::WatchdogKilled => reply,
        _ => return blocked(request, Failure::WorkerProtocol, cleanup),
    };
    ControlRecord::new(request, ResultKind::Observed(reply.observation), cleanup, ms(start))
}

pub fn run_suite(worker: &Path) -> std::io::Result<QualificationRecord> {
    let backend = BackendIdentity::for_worker(worker)?;
    let mut records = Vec::new();
    for probe in Probe::ALL {
        let record = run_control(worker, Request::new(probe, backend.clone()));
        let passed = record.passed;
        records.push(record);
        // Fail closed: never proceed after ambiguous execution, cleanup or a failed control.
        if !passed { break; }
    }
    Ok(QualificationRecord::from_controls(backend, records))
}
