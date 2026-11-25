# TinyBuilder 0.1.0 experimental release contract

**NOT QUALIFIED.** Candidate preparation only. See [research handoff](research/2026-11-26-release-audit.md).
Target: native offline read-only assistant on Windows x64, macOS ARM64,
Linux x64. Deterministic read/search/inspect, grounded Q&A, guided existing GGUF
reuse and trusted pinned bundled CPU runtime. No mutation, execution, MCP,
automatic downloads, training or persisted transcripts in supported interface.
Python and write-capable examples remain reference/lab only.

| Gate | Status | Required evidence |
| --- | --- | --- |
| Scope and version | IMPLEMENTED; CI PENDING | Read-only normal CLI, canonical product version and regression tests |
| Exact candidate CI | PENDING | Locked native tests/build/smoke all three targets |
| Runtime provenance | PARTIAL; SECURITY REVIEW BLOCKED | Actual staged runtime hashes and source asset, notices, socket ownership/authentication, forced exit cleanup |
| Clean-machine lifecycle | CI SMOKE IMPLEMENTED; CLEAN HOST BLOCKED | Each target installs/unpacks and runs offline without developer tools, exit/remove preserve user files |
| Model quality and license | BLOCKED | Permissively licensed model, preselected shipped engine, unchanged 10/10 exact two-fact genuine-read trials |
| Read-only safety | REGRESSION TESTS; REVIEW PENDING | Denial of mutation/exec options, no project mutation, traversal/hardlink/symlink/reparse protection and containment review |
| Artifacts | PACKAGING IMPLEMENTED; CI PENDING | Exact sizes/hashes, source commit, runtime identity, notices, signing status, no weights |
| Docs and publication | BLOCKED | Accurate onboarding, independent review and explicit approval |

Do not substitute mock or direct controls for actual model qualification, or
native unit tests for clean-machine lifecycle. Preserve failures and denominators.
Do not automatically transfer historical checklist passes to the RC.

Product version is distinct from Rust 0.2.0-alpha.1 and Python 0.1.0 package
metadata. External registry history is unverified; preserve internal semver.
Final 0.1.0 needs explicit authorization and completed gates. Keep PR #14
separate, and do not distribute lab executables with supported artifacts.

## Candidate packaging

The native-package workflow builds unsigned portable ZIP (Windows) or tar.gz
(macOS/Linux) archives from a locked Rust build and the pinned b6500 archive.
It retains exact source SHA, file and archive hashes, runtime and crate notice
inventories, and exercises unpacked model-free launch and removal. The build
binds the runtime manifest to the executable. No weights or lab executables
are staged. Hosted CI is not clean-machine qualification; system dependency,
redistribution, signing and security review remain outstanding. Point-in-time
listener ownership checks are not an atomic authenticated transport boundary.
See [candidate quickstart](CANDIDATE_QUICKSTART.md).
