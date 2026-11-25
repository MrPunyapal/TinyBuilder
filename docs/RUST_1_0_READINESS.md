# Native TinyBuilder 1.0 readiness contract

Status: development, not a release candidate. Version stays pre-1.0 until the
evidence below is obtained. All targets are first-class: Windows x64, macOS
ARM64, Linux x64. The Python implementation is retained as a reference.
No public preview, model download, training or installer publication is implied.

| Gate | Required evidence |
| --- | --- |
| Deterministic build | Locked minimum Rust version, native tests and CLI smoke on all three platforms |
| Model accuracy | Existing exact two-fact read gate 10/10 on fresh fixtures, real verified reads; separately qualified permissive model |
| Coding | Independent positive and negative controls; real bug fixes, creation and edits in disposable worktrees, language parser and actual test outcomes |
| Tool permissions | Read-only default, per-action approval, exact evidence-bound patches, no-clobber creation, denied writes leave bytes unchanged |
| Security | Runtime provenance and socket ownership, atomic process containment, project path/metadata safety, dependency audit and notices |
| Responsiveness | First-token latency, sustained generation, bounded memory, cancel in-flight without losing session; measured per platform |
| Context | Bounded relevance, incomplete evidence clearly reported, incremental index correctness and invalidation |
| Product | Guided onboarding, explicit model reuse/download choice, size and destination, cancellation and recovery, settings and privacy |
| Installation | Native installers on clean supported systems, launch with no developer tooling, offline inference, upgrade/uninstall preserve user projects and models |
| Release | Signed/checksummed artifacts, redistribution review, rollback instructions, maintained documentation and explicit release approval |

## Evidence available so far

Consolidated main passed all three deterministic CI workflows before this sprint.
The Windows development-machine report described offline inference and fast Rust
file operations, but the two-fact gate was 0/10 and live edit proposals 0/3.
The local fixes were not pushed; do not claim they are integrated. A research
license model is lab evidence only. Direct controls and mocked tests never count
as model qualification.

## This PR

Relevant source excerpts, context-first CLI, proposal-only diagnostics, duplicate
observation reduction, evidence-bound native edits, bounded read-only streaming,
explicit file creation. These are implementation milestones, not proof of
general coding intelligence or secure production distribution.

## Next proof

Run paired read diagnostics and proposal diagnostics on the existing offline
runtime/model, choose the candidate before ten fresh qualification trials,
then run independent semantic coding controls. Do not adjust or select the
oracle to turn failures into passes. Stop and report capability limits if the
model cannot reliably perform the tasks. Real inference, immediate cancellation,
incremental indexing, approved command execution, model management, security
and installer gates remain open.
