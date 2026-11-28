# Portable Evaluator v1 — trusted controls only

Experimental standalone crate; not part of `rust/Cargo.toml`, the 0.1 product package, or the existing Linux PHP evaluator. Research direction accepted, security boundary **not qualified**. No generated-code entrypoint, dynamic module path, arbitrary Wasm bytes, shell, candidate scope or approval override exists. Do not use this crate as an outer sandbox. The same-user worker retains ordinary native authority if compromised.

## Build and run (reviewed controls only, authorized environment)

Use Rust 1.95.0 and a reviewed committed Cargo.lock. The initial remote CI may bootstrap a single lock, share it across all three platforms and retain it for maintainer review. Until that lock is committed and tested, do not call this a reproducible or fully pinned dependency closure.

```sh
cargo +1.95.0 test --manifest-path lab/portable-evaluator/Cargo.toml --locked --all-targets
cargo +1.95.0 build --manifest-path lab/portable-evaluator/Cargo.toml --locked --bins
cargo +1.95.0 run --manifest-path lab/portable-evaluator/Cargo.toml --locked --bin portable-evaluator-supervisor -- trusted-suite
```

The supervisor hashes the reviewed sibling worker, fixed control set and request contract; passes only a fixed enum request and exact limits over bounded JSON; clears the worker environment, runs from disposable scratch, bounds output, uses a deadline, kills/reaps the direct child and verifies scratch removal. The worker independently checks its identity and request and cannot accept candidate bytes. Only static WAT controls in `src/controls.rs` execute. Worker stdout is a bounded typed reply, not guest stdout; guest stdio is not inherited.

The record explicitly identifies **trusted_control_only**, **outer_isolation: unqualified**, **candidate_admission: denied**, even if all controls pass. The record is evidence, not signed attestation, freshness proof or authorization. Unexpected return, blocked policy, malformed transport, ambiguous exit, timeout and cleanup failures stop the suite; no model semantic scores exist. The timeout control needs an observed ready marker and successful direct-child reaping and scratch removal. No direct child result establishes process-tree or outer isolation.

## What the controls cover (not what they prove)

- Positive constant return; WASIp1 no preopens and invalid relative-path access; no inherited args/env; absent socket descriptor; missing custom host spawn import.
- Positive memory growth within a two-page ceiling and denied growth beyond it; fuel exhaustion; deterministic epoch interruption; native ready/sleep watchdog kill.
- Strict schema, unknown fields/candidate scope, identity mismatch, exact policy, message size, cleanup and suite accounting regression tests.

The filesystem probe has no preopen at all, not a Windows traversal or symlink qualification test. The socket probe checks descriptor denial, not real DNS/TCP/UDP or loopback containment. No filesystem quota, process-tree containment, whole-worker memory/CPU hard limit, host-handle audit, native exploit defense, output-flood/host-import accounting, signing or clean-account acceptance has been established. Guest linear memory is not total process RSS. Clocks/random remain WASI defaults; no determinism claim about arbitrary modules. Hash-before-exec is not race-proof against a malicious same-user process. The watchdog does not prove bounds on spawn, hashing, IPC writes or compilation and is not a hard outer watchdog. In case of uncertain cleanup, retain the directory and block; do not proceed.

## Initial dependency and license review

Direct Wasmtime and WASI pins: 48.0.10, LTS line; Rust 1.95.0 per [tagged workspace manifest](https://github.com/bytecodealliance/wasmtime/blob/v48.0.10/Cargo.toml). The [release notes](https://github.com/bytecodealliance/wasmtime/releases/tag/v48.0.10) list the Windows path escape fix [GHSA-f2pq-268w-886c](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-f2pq-268w-886c). Review [all upstream advisories](https://github.com/bytecodealliance/wasmtime/security/advisories), including the November 16 host memory growth advisory [GHSA-5m8g-xhq4-4h93](https://github.com/bytecodealliance/wasmtime/security/advisories/GHSA-5m8g-xhq4-4h93), no-GC/no-threads aborts and the earlier WASI permissions issues. Pin selection is not a comprehensive advisory clearance. The separate workflow resolves and inventories transitive crates/features and invokes the repository OSV scanner. Review exact resolved lock, feature graph, advisories and exceptions before promotion. Wasmtime/wasmtime-wasi are [Apache-2.0 WITH LLVM-exception](https://github.com/bytecodealliance/wasmtime/blob/v48.0.10/LICENSE); this crate is MIT, but transitive licenses/notices and redistribution remain unreviewed. No evaluator is bundled with native 0.1.

See [research draft PR #25](https://github.com/MrPunyapal/TinyBuilder/pull/25), [roadmap](https://github.com/MrPunyapal/TinyBuilder/blob/28668ad18da56f812448ad8b11c6177fa1d9e8ed/docs/research/2026-11-28-phase-3-sandbox-roadmap.md), and [current containment policy](../../docs/research/2026-11-27-contained-qualification.md). Do not use ordinary CI or this worker to score model-generated code. Existing approved Linux guest and behavioral oracles are unchanged.
