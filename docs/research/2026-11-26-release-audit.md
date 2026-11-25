# TinyBuilder 0.1.0 — research knowledge base and handoff

Date: 2026-11-26. Source-linked digest of Deep Research's 0.1.0 release
re-audit and subsequent GitHub connector verification. Original full report
is in the project conversation; research itself had read-only web access.

## Decision
NO-GO for public release; GO for focused RC preparation. Free experimental
native Rust standalone offline **read-only** codebase assistant for Windows
x64, macOS ARM64, Linux x64. Choose project and existing compatible GGUF,
start pinned CPU llama.cpp, search/read actual files, ask grounded questions.
No Python, Git, Ollama or Rust required at runtime. Python is reference only.

Defer mutation, creation, command execution, MCP, autonomous repair, automatic
model downloads, persistent conversation, training, streamed tool actions
and in-session cancellation. Preserve PR #14's lab work. No new model downloads,
paid APIs, training, local unpublished file access, public release/tag or merge
without authorization. Keep unchanged exact model oracle.

## Evidence
- [Main](https://github.com/MrPunyapal/TinyBuilder/commit/414c2705c7d47333e68e875da28a39fa71b85dce):
  all 13 original PR histories retained. [Python](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45703664363),
  [native](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45703664443),
  [Rust](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45703664566) CI passed.
- [PR #14](https://github.com/MrPunyapal/TinyBuilder/pull/14) draft, head
  9467f503764b0b337ffc358c8dc46048c26a96dd, five commits.
  [Rust](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45705493911),
  [native](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45705493962),
  [Python](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45705493832)
  PR runs plus push Rust and Python passed, verified through connector after
  research. CodeRabbit skipped; CI is not independent review.
- Connector enumerated 14 pre-RC branches and one open PR, filling the research
  web-access enumeration gap. No GitHub release; external package registry
  history not established. Rust crate internal 0.2.0-alpha.1, Python reference
  0.1.0, exact Cargo.lock and Rust 1.88 minimum. Canonical product RC version
  should be separate until external registry lineage checked; no public downgrade.
- Previous Windows developer-machine report (not independently reproduced):
  CPU b12359 + Qwen2.5-Coder 3B GGUF; startup 27 vs 291 ms Python, search
  115 vs 524 ms; two guided single-fact reads passed. **Exact two-fact gate
  0/10; live edit proposals 0/3.** Clean Windows install unverified. Unpublished
  local fixes inaccessible, not integrated. Research-license 3B not public default.
- Apache-2.0 Qwen2.5-Coder-1.5B Q4_K_M provisional only: revision
  2ab9f8f42af02fc212effaef7c4850c885e965f4, size 1117320768 bytes,
  SHA256 cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046.
  No default model qualified; Qwen3-4B is research candidate. Genuine tool
  calls, loading, mocks and direct controls are not model accuracy evidence.
- [Release checklist](../RELEASE_CHECKLIST.md), [security](../SECURITY.md),
  [developer guidance](../../AGENTS.md), [qualification](../../benchmarks/QUALIFICATION.md)
  and [catalog](../../tinybuilder/models/catalog.py) are primary references.
- Runtime manifest consistency is not authenticity; socket ownership before
  bearer token, Windows spawn/assignment race, filesystem containment and
  metadata limitations, dependency security and notices need review. Not an
  OS sandbox. Existing Python packaging not a qualified native installer.

## Work order
1. Freeze read-only scope on release/0.1 from accepted main; selectively
   port PR #14 context improvements, not mutation and streaming.
2. Canonical product 0.1.0-rc.1, no tag or release. Default CLI cannot
   expose writes/create/exec. Add version and read-only safety tests.
3. Trigger exact-head cross-platform locked builds; adapt runtime provenance
   workflow to release branch and chosen pinned runtime. Address Node action
   deprecation using verified pins. Python wheel evidence is reference, not Rust.
4. Native candidate packages on each target: product version, Git SHA,
   target, executable bytes/hash, runtime revision/archive hash, license
   notices, signing/notarization status, no model weights.
5. Clean-machine install/unpack, launch offline, existing GGUF, authenticated
   loopback and cleanup on normal/forced exit, uninstall preserves user files.
   Record OS/CPU/RAM, artifact, runtime and model digests, tests and reviewer.
6. Preselect legally usable model/engine, run unchanged exact 10/10 hidden-fact
   trials through genuine native reads on actual release workflow; no weaker
   scorer or selective retries. Stop if no model qualifies.
7. Independent security/dependency/redistribution and documentation review;
   explicit maintainer approval before release.

## New chat handoff
Read this file and [release contract](../RELEASE_0_1.md) first. Fetch fresh
release/0.1 head, PR and CI; never assume another commit's tests apply.
Update this knowledge base with dated evidence as gates clear. Preserve main,
PR #14 and local unpublished work. Prioritize a working first release over
new agent features. Original full research remains in the project conversation.

## Continuation — 2026-11-26

- PR #15 verified open, draft, mergeable, targeting main from release/0.1. Initial head `76ae0c414d5233084b28c1d909bb507387642b45`: [Python](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45707609817), [native](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45707609806), [Rust](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45707609860) all in progress when inspected; no pass claimed.
- [11aa834](https://github.com/MrPunyapal/TinyBuilder/commit/11aa8343b2b2e77e1c1e20b1606f36019c53a405) extends pinned b6500 runtime archive inspection to release/0.1 and relevant PRs, retaining per-platform JSON inventory artifacts. This is input provenance only, not staged runtime authenticity or qualification. CI execution not yet verified.
- Runtime review confirms an unresolved bind/drop/spawn race: readiness sends the bearer key before proving listener ownership. Windows job assignment still occurs after spawn. Both remain release blockers. Native CI currently stages lab binaries, not standalone product packages. No model weights downloaded, no oracle changes, no release or merge, no PR #14 changes.

## Second continuation — 2026-11-26

- All four PR workflows for the previous head af272fcd passed:
  [Rust](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45707840918),
  [archive evidence](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45707840748),
  [native](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45707840687),
  [Python](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45707840757).
  Actual archive logs confirmed b6500 Windows 13,992,302 bytes,
  macOS 10,699,243 bytes, Linux 12,754,315 bytes. Windows archive lacked
  the main LICENSE; pinned upstream commit a7a98e0fffed794396b3fbad4dcdbbc184963645
  and LICENSE blob acb96ce78e0486e9dc7602cdcdd2f491c34f335a supplied it.
  These results do not establish the new head's correctness.
- Native packaging implemented: [8dbd4cc](https://github.com/MrPunyapal/TinyBuilder/commit/8dbd4cc1377947ba8d49e86b7fb64db7423a011b),
  [ca28abc](https://github.com/MrPunyapal/TinyBuilder/commit/ca28abcc526e152fa5777db683b754a933327b68),
  [63d6b31](https://github.com/MrPunyapal/TinyBuilder/commit/63d6b3104ca5cfb9b73028e335b4d1400d9c8653),
  [69b8f84](https://github.com/MrPunyapal/TinyBuilder/commit/69b8f8454585b022a1bd44e5f138bf5ed4971e7a).
  ZIP/tar.gz candidate archives with selected verified runtime files, embedded
  manifest digest, locked Rust build, notices and SHA-256 inventories;
  model-free smoke, tamper rejection, runtime --version, unpack/launch/remove
  and unchanged project checks. No product package pass claimed until CI
  completes. No model downloads. Portable archives are not signed installers.
- [45d5040](https://github.com/MrPunyapal/TinyBuilder/commit/45d50406fc810101ef63610250d066c6c7028985),
  [ea1bdb6](https://github.com/MrPunyapal/TinyBuilder/commit/ea1bdb6b61b113c41383551944645a0006aff266),
  [58e98a2](https://github.com/MrPunyapal/TinyBuilder/commit/58e98a2f35af79d3c3050f203f07da24a5850771):
  Windows suspended spawn/job assignment/resume; Windows TCP owner table,
  Linux procfs and macOS system lsof listener checks before credentials/context;
  genuine owned/foreign loopback regression tests. Point-in-time checks do
  not cryptographically bind an HTTP connection to a process; residual race,
  native API behavior and independent security review still need evidence.
- [10143ea](https://github.com/MrPunyapal/TinyBuilder/commit/10143eab28ed60c74ab98cbd1116bb61c23f873e)
  and [995d3a4](https://github.com/MrPunyapal/TinyBuilder/commit/995d3a47d9bc7f9b68db368cad17b7096d3ea75b)
  implement and test model-free interactive startup and later existing GGUF
  selection. Packaging regression tests include selected-member symlink denial.
- Latest runs observed queued/in progress or superseded by newer commits.
  Exact-head CI and artifact sizes/hashes not yet verified. Local environment
  has no Rust compiler or GitHub DNS access; GitHub connector writes worked,
  atomic tree lookup returned 404 so sequential file commits were used.
- Next: inspect fresh exact-head push and PR runs; fix failures before
  accepting any package. Check clean Windows/macOS/Linux hosts offline,
  loader/system dependencies and full notices, actual model/runtime startup,
  authentication and normal/forced cleanup. Preselect permissible model and
  engine and execute unchanged exact 10/10 qualification only with existing
  approved model or explicit approval to download. Public release remains
  NO-GO; PR #14 and main unchanged, no tag, release or merge.
