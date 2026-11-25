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
