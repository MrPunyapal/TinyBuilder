//! Portable Evaluator v1: a deliberately non-promotable trusted-control lab.
//! No public candidate submission or qualification override exists.
pub mod controls;
pub mod supervisor;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::io::{self, Read};
use std::path::Path;

pub const SCHEMA: u32 = 1;
pub const PROFILE: &str = "wasi-p1-no-grants-trusted-controls-v1";
pub const RUNTIME: &str = "wasmtime-48.0.10/wasmtime-wasi-48.0.10";
pub const FEATURES: &str = "wasmtime:anyhow,cranelift,runtime,std,wat;wasi:p1";
pub const MAX_MESSAGE: usize = 8192;
pub const WATCHDOG_READY: &[u8] = b"watchdog-ready\n";

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Probe {
    Return42, NoPreopen, NoPath, NoEnvironment, NoArguments, NoSocket,
    NoHostSpawn, MemoryAllowed, MemoryDenied, Fuel, Epoch, Watchdog,
}
impl Probe {
    pub const ALL: [Self; 12] = [
        Self::Return42, Self::NoPreopen, Self::NoPath, Self::NoEnvironment,
        Self::NoArguments, Self::NoSocket, Self::NoHostSpawn, Self::MemoryAllowed,
        Self::MemoryDenied, Self::Fuel, Self::Epoch, Self::Watchdog,
    ];
    pub const fn name(self) -> &'static str {
        match self {
            Self::Return42 => "return_42", Self::NoPreopen => "no_preopen",
            Self::NoPath => "no_path", Self::NoEnvironment => "no_environment",
            Self::NoArguments => "no_arguments", Self::NoSocket => "no_socket",
            Self::NoHostSpawn => "no_host_spawn", Self::MemoryAllowed => "memory_allowed",
            Self::MemoryDenied => "memory_denied", Self::Fuel => "fuel",
            Self::Epoch => "epoch", Self::Watchdog => "watchdog",
        }
    }
    pub fn matches(self, observation: &Observation) -> bool {
        match (self, observation) {
            (Self::Return42, Observation::Returned(42))
            | (Self::NoEnvironment | Self::NoArguments, Observation::Returned(0))
            | (Self::MemoryAllowed, Observation::Returned(1))
            | (Self::MemoryDenied, Observation::Returned(-1))
            | (Self::NoHostSpawn, Observation::ImportDenied)
            | (Self::Fuel, Observation::FuelExhausted)
            | (Self::Epoch, Observation::EpochInterrupted)
            | (Self::Watchdog, Observation::WatchdogKilled) => true,
            (Self::NoPreopen | Self::NoPath | Self::NoSocket, Observation::Returned(n)) => *n > 0,
            _ => false,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Scope { TrustedControlOnly }
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OuterIsolation { Unqualified }
#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum CandidateAdmission { Denied }

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BackendIdentity {
    pub profile: String,
    pub runtime: String,
    pub features: String,
    pub os: String,
    pub arch: String,
    pub worker_sha256: String,
    pub controls_sha256: String,
    pub contract_sha256: String,
}

fn hash(data: &[u8]) -> String { format!("{:x}", Sha256::digest(data)) }

fn hash_file(path: &Path) -> io::Result<String> {
    let mut file = std::fs::File::open(path)?;
    let mut digest = Sha256::new();
    let mut buf = [0; 65536];
    loop {
        let n = file.read(&mut buf)?;
        if n == 0 { break; }
        digest.update(&buf[..n]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

impl BackendIdentity {
    // Caller supplies only the reviewed sibling worker, never a guest-selected path.
    pub fn for_worker(path: &Path) -> io::Result<Self> {
        let mut digest = Sha256::new();
        for probe in Probe::ALL {
            let bytes = controls::source(probe).as_bytes();
            digest.update((bytes.len() as u64).to_le_bytes());
            digest.update(bytes);
        }
        Ok(Self {
            profile: PROFILE.into(), runtime: RUNTIME.into(), features: FEATURES.into(),
            os: std::env::consts::OS.into(), arch: std::env::consts::ARCH.into(),
            worker_sha256: hash_file(path)?,
            controls_sha256: format!("{:x}", digest.finalize()),
            contract_sha256: hash(include_bytes!("lib.rs")),
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Limits {
    pub fuel: u64,
    pub memory_bytes: usize,
    pub table_elements: usize,
    pub instances: usize,
    pub memories: usize,
    pub tables: usize,
    pub wall_ms: u64,
    pub message_bytes: usize,
}
impl Limits {
    pub fn for_probe(probe: Probe) -> Self {
        Self {
            fuel: 100_000, memory_bytes: 2 * 65_536, table_elements: 16,
            instances: 1, memories: 1, tables: 1,
            wall_ms: if probe == Probe::Watchdog { 5_000 } else { 30_000 },
            message_bytes: MAX_MESSAGE,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Request {
    pub schema: u32,
    pub scope: Scope,
    pub probe: Probe,
    pub backend: BackendIdentity,
    pub limits: Limits,
}
impl Request {
    pub fn new(probe: Probe, backend: BackendIdentity) -> Self {
        Self { schema: SCHEMA, scope: Scope::TrustedControlOnly, probe, backend,
               limits: Limits::for_probe(probe) }
    }
    pub fn validate(&self, observed: &BackendIdentity) -> Result<(), Failure> {
        if self.schema != SCHEMA { return Err(Failure::SchemaMismatch); }
        if &self.backend != observed { return Err(Failure::IdentityMismatch); }
        if self.limits != Limits::for_probe(self.probe) { return Err(Failure::PolicyMismatch); }
        Ok(())
    }
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", content = "value", rename_all = "snake_case", deny_unknown_fields)]
pub enum Observation { Returned(i32), ImportDenied, FuelExhausted, EpochInterrupted, WatchdogKilled }

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Failure {
    SchemaMismatch, IdentityMismatch, PolicyMismatch, WorkerStart, WorkerProtocol,
    WorkerExit, InfrastructureTimeout, CleanupUnverified, ScratchUnavailable,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct WorkerReply { pub request: Request, pub observation: Observation }

#[derive(Clone, Copy, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Cleanup { NotStarted, DirectChildReapedAndScratchRemoved, Unverified }

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", content = "value", rename_all = "snake_case", deny_unknown_fields)]
pub enum ResultKind { Observed(Observation), Blocked(Failure) }

#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ControlRecord {
    pub request: Request,
    pub result: ResultKind,
    pub cleanup: Cleanup,
    pub passed: bool,
    pub wall_ms: u64,
}
impl ControlRecord {
    pub fn new(request: Request, result: ResultKind, cleanup: Cleanup, wall_ms: u64) -> Self {
        let passed = cleanup == Cleanup::DirectChildReapedAndScratchRemoved
            && matches!(&result, ResultKind::Observed(o) if request.probe.matches(o));
        Self { request, result, cleanup, passed, wall_ms }
    }
}

// Evidence, never an admission token. There is deliberately no "qualified" variant.
#[derive(Clone, Debug, Eq, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct QualificationRecord {
    pub schema: u32,
    pub backend: BackendIdentity,
    pub scope: Scope,
    pub outer_isolation: OuterIsolation,
    pub candidate_admission: CandidateAdmission,
    pub planned: usize,
    pub attempted: usize,
    pub passed: usize,
    pub failed: usize,
    pub blocked: usize,
    pub remaining: usize,
    pub all_controls_passed: bool,
    pub controls: Vec<ControlRecord>,
}
impl QualificationRecord {
    pub fn from_controls(backend: BackendIdentity, controls: Vec<ControlRecord>) -> Self {
        let planned = Probe::ALL.len();
        // Recompute, not trust a worker's pass flag. The supervisor emits a fixed prefix.
        let coherent = controls.len() <= planned && controls.iter().enumerate().all(|(i, r)|
            r.request.probe == Probe::ALL[i] && r.request.validate(&backend).is_ok()
            && r.passed == ControlRecord::new(r.request.clone(), r.result.clone(), r.cleanup, r.wall_ms).passed);
        let attempted = controls.iter().filter(|r| r.cleanup != Cleanup::NotStarted).count();
        let passed = if coherent { controls.iter().filter(|r| r.passed).count() } else { 0 };
        let failed = if coherent { controls.iter().filter(|r| !r.passed &&
            matches!(&r.result, ResultKind::Observed(_))).count() } else { 0 };
        let blocked = controls.len().saturating_sub(passed + failed);
        Self {
            schema: SCHEMA, backend, scope: Scope::TrustedControlOnly,
            outer_isolation: OuterIsolation::Unqualified, candidate_admission: CandidateAdmission::Denied,
            planned, attempted, passed, failed, blocked,
            remaining: planned.saturating_sub(controls.len()),
            all_controls_passed: coherent && passed == planned, controls,
        }
    }
}

pub fn bounded_read(reader: impl Read) -> io::Result<Vec<u8>> {
    let mut bytes = Vec::new();
    reader.take((MAX_MESSAGE + 1) as u64).read_to_end(&mut bytes)?;
    if bytes.len() > MAX_MESSAGE {
        return Err(io::Error::new(io::ErrorKind::InvalidData, "message limit"));
    }
    Ok(bytes)
}

#[cfg(test)]
mod tests {
    use super::*;
    fn identity() -> BackendIdentity {
        BackendIdentity { profile: PROFILE.into(), runtime: RUNTIME.into(), features: FEATURES.into(),
            os: "test".into(), arch: "test".into(), worker_sha256: "0".repeat(64),
            controls_sha256: "1".repeat(64), contract_sha256: "2".repeat(64) }
    }
    #[test]
    fn strict_contract_denies_candidate_and_unknown_fields() {
        let request = Request::new(Probe::Return42, identity());
        let mut json = serde_json::to_value(&request).unwrap();
        json["scope"] = "candidate".into();
        assert!(serde_json::from_value::<Request>(json).is_err());
        let mut json = serde_json::to_value(&request).unwrap();
        json["module_path"] = "untrusted.wasm".into();
        assert!(serde_json::from_value::<Request>(json).is_err());
        let serialized = serde_json::to_string(&request).unwrap();
        assert!(serde_json::from_str::<Request>(&serialized.replace("\"schema\":1", "\"schema\":1,\"schema\":1")).is_err());
    }
    #[test]
    fn exact_identity_and_policy() {
        let actual = identity();
        let mut request = Request::new(Probe::Return42, actual.clone());
        assert_eq!(request.validate(&actual), Ok(()));
        request.schema = 2;
        assert_eq!(request.validate(&actual), Err(Failure::SchemaMismatch));
        request.schema = SCHEMA;
        request.backend.worker_sha256 = "f".repeat(64);
        assert_eq!(request.validate(&actual), Err(Failure::IdentityMismatch));
        request.backend = actual.clone();
        request.limits.fuel += 1;
        assert_eq!(request.validate(&actual), Err(Failure::PolicyMismatch));
    }
    #[test]
    fn output_bound_and_cleanup_gate() {
        assert_eq!(bounded_read(&vec![0; MAX_MESSAGE][..]).unwrap().len(), MAX_MESSAGE);
        assert!(bounded_read(&vec![0; MAX_MESSAGE + 1][..]).is_err());
        let request = Request::new(Probe::Return42, identity());
        let record = ControlRecord::new(request, ResultKind::Observed(Observation::Returned(42)), Cleanup::Unverified, 0);
        assert!(!record.passed);
        let report = QualificationRecord::from_controls(identity(), vec![record]);
        assert_eq!(report.candidate_admission, CandidateAdmission::Denied);
        assert_eq!(report.outer_isolation, OuterIsolation::Unqualified);
        assert!(!report.all_controls_passed);
    }
    #[test]
    fn empty_suite_never_passes() {
        let report = QualificationRecord::from_controls(identity(), vec![]);
        assert_eq!(report.remaining, Probe::ALL.len());
        assert_eq!(report.attempted, 0);
        assert!(!report.all_controls_passed);
    }
}
