use std::{io::Write, path::Path, process::{Command, Stdio}};
use tinybuilder_portable_evaluator::{BackendIdentity, CandidateAdmission, Cleanup, Failure,
    OuterIsolation, Probe, Request, ResultKind, supervisor::{run_control, run_suite}};

fn worker() -> &'static Path { Path::new(env!("CARGO_BIN_EXE_portable-evaluator-worker")) }

#[test]
fn complete_fixed_control_suite() {
    let report = run_suite(worker()).unwrap();
    eprintln!("{}", serde_json::to_string_pretty(&report).unwrap());
    assert_eq!(report.planned, Probe::ALL.len());
    assert!(report.all_controls_passed, "trusted control suite stopped");
    assert_eq!(report.passed, report.planned);
    assert_eq!(report.blocked, 0);
    assert_eq!(report.remaining, 0);
    assert_eq!(report.candidate_admission, CandidateAdmission::Denied);
    assert_eq!(report.outer_isolation, OuterIsolation::Unqualified);
    assert!(report.controls.iter().all(|r| r.cleanup == Cleanup::DirectChildReapedAndScratchRemoved));
}

#[test]
fn supervisor_rejects_mismatched_identity_before_spawn() {
    let mut req = Request::new(Probe::Return42, BackendIdentity::for_worker(worker()).unwrap());
    req.backend.worker_sha256 = "0".repeat(64);
    let record = run_control(worker(), req);
    assert_eq!(record.result, ResultKind::Blocked(Failure::IdentityMismatch));
    assert_eq!(record.cleanup, Cleanup::NotStarted);
    assert!(!record.passed);
}

#[test]
fn worker_independently_rejects_candidate_and_policy_mismatch() {
    let mut req = serde_json::to_value(Request::new(Probe::Return42,
        BackendIdentity::for_worker(worker()).unwrap())).unwrap();
    req["scope"] = "candidate".into();
    let mut policy = serde_json::to_value(Request::new(Probe::Return42,
        BackendIdentity::for_worker(worker()).unwrap())).unwrap();
    policy["limits"]["fuel"] = 1_000_000.into();
    for bad in [req, policy] {
        let mut child = Command::new(worker()).env_clear()
            .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::null()).spawn().unwrap();
        child.stdin.take().unwrap().write_all(&serde_json::to_vec(&bad).unwrap()).unwrap();
        let output = child.wait_with_output().unwrap();
        assert!(!output.status.success());
        assert!(output.stdout.is_empty());
    }
}
