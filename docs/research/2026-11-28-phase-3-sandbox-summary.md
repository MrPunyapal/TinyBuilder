# Phase 3 — Portable sandbox executive summary

Date: 2026-11-28. Status: proposed research direction, not an accepted architecture, qualified evaluator or release authorization.

Full findings and historical source citations: [Phase 3 report](2026-11-28-phase-3-portable-sandbox.md). Actionable sequence: [Phase 3 roadmap](2026-11-28-phase-3-sandbox-roadmap.md).

## Decision in brief

**GO** for a model-free, separately packaged Rust/Wasmtime/WASI evaluator proof of concept in authorized environments. **Conditional GO** for two independent PHP compatibility lanes. **NO-GO** for generated candidate execution, unqualified native fallback, provisioning the owner's personal Windows host, or expanding the 0.1 read-only product.

The primary goal is an independently verified execution substrate, not a new shell or agent runtime. Wasmtime provides capability-based guest interfaces across Windows, macOS and Linux; it is not a guarantee of host safety if the native runtime itself is compromised. A separate worker improves failure handling, but does not revoke the worker's ordinary OS permissions. Under the existing project policy, a separately approved and qualified outer boundary is still required before arbitrary generated code may run.

## Evidence and present status

| Claim | Evidence class | Status |
|---|---|---|
| Current main | Direct GitHub verification on 2026-11-28 | [ce28337552933a671a95d1ad30baa07cfe7cc2b7](https://github.com/MrPunyapal/TinyBuilder/commit/ce28337552933a671a95d1ad30baa07cfe7cc2b7) |
| Coding Intelligence v1 | Repository / PR evidence | [PR #23](https://github.com/MrPunyapal/TinyBuilder/pull/23) merged after seven successful integrated workflows |
| Post-merge CI | Direct GitHub query | Six exact-main workflows returned, all successful; not live sandbox qualification |
| Public semantic corpus | Repository-reported trusted controls | 12 tasks, 87 planned observations: eight dependency-free (72), four real Laravel (15) |
| Additional real Laravel route bridge | Repository-reported trusted controls | Nine separate observations; original PHPUnit oracle unchanged |
| Live generated-code evaluator | Repository policy and checkpoint | Blocked; approved isolated Linux guest is not available/qualified |
| Portable runtime support | Upstream documentation | Wasmtime has Rust embedding and capability-oriented WASI; PHP.wasm has Emscripten host adapters |
| Exact Laravel-on-Wasm parity and security | Hypothesis | Not measured |
| Package size, latency and peak memory | Unknown | No TinyBuilder evaluator measurements |
| Model capability and training | Outside Phase 3 experiment | No new inference, downloads or training; semantic claims remain blocked |

The [project status snapshot](../PROJECT_STATUS.md) retains pre-merge descriptions; actual GitHub main and PR state take precedence for factual status. The lead maintainer should reconcile it independently. No local changes or hardware were inspected.

## Proposed architecture

```text
Experimental lab caller (not supported 0.1 CLI)
  -> typed evaluator request / supervisor
       -> immutable staged fixture + bounded writable scratch
       -> isolated worker with pinned backend, no ambient guest authority
       -> bounded, untrusted observations
  -> independent trusted scorer outside the candidate-visible environment
```

The supervisor and worker must not accept arbitrary host commands or expose the real project directory. Candidate bytes and any output remain untrusted. The worker uses minimal host imports, no inherited environment, no sockets or subprocess privileges, fuel/epoch interruption, resource limits and independent timeout/cleanup. Whole-worker and disk limits require separate enforcement. A runtime or policy mismatch must fail closed.

Hidden assertions, expected results, reference patches and private fixture source remain outside the model root and candidate process; a read-only test mount is not secrecy. Use the existing typed observation approach rather than trusting candidate-reported PHPUnit success.

## Proposed decisions

| Option | Recommendation | Reason / evidence that could change it |
|---|---|---|
| Rust Wasmtime + WASI worker | Adopt for experimental PoC | [Security model](https://docs.wasmtime.dev/security.html), [WASI capabilities](https://wasi.dev/security), [Rust embedding API](https://docs.wasmtime.dev/api/wasmtime/). Must measure actual packages and qualify each exact build. |
| WordPress Playground PHP.wasm | Adapt experimentally | [PHP.wasm architecture](https://wordpress.github.io/wordpress-playground/developers/architecture/php-wasm-packages/) and [PHPUnit guide](https://wordpress.github.io/wordpress-playground/ja/guides/phpunit-testing/) show PHP building blocks, not Laravel 13.42.0 parity. Emscripten/Node host adapters expand the trusted computing base; no network proxy or host filesystem passthrough. |
| Wasmer/WASIX PHP | Conditional alternate PoC | [WASIX](https://docs.wasmer.io/runtime/wasix/) offers broader POSIX compatibility; [SDK](https://docs.wasmer.io/runtime/python/) maturity and exact policy are unqualified. |
| Windows AppContainer + Job Object | Conditional outer layer/native fallback | [AppContainer](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer), [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects). Platform-only; standard-user behavior and outer boundary need qualification elsewhere. |
| macOS signed sandboxed helper | Conditional outer layer/native fallback | [App Sandbox](https://developer.apple.com/documentation/security/app-sandbox/); signed entitlements and hardened-runtime/JIT interactions need testing. Reject unsupported sandbox-exec/custom SBPL as production foundation. |
| Linux bubblewrap/nsjail | Conditional outer layer/native fallback | [bubblewrap](https://github.com/containers/bubblewrap), [nsjail](https://github.com/google/nsjail); depends on allowed namespaces and kernel policy. No enabling system features to force compatibility. |
| WAMR primary boundary | Reject for now | [Configuration limitations](https://github.com/wasm-micro-runtime/wasm-micro-runtime/blob/main/doc/build_wamr.md) and [security history](https://github.com/wasm-micro-runtime/wasm-micro-runtime/security); smaller size alone cannot outweigh assurance requirements. |
| In-process runtime inside normal CLI; plain subprocess/worktree/allowlist | Reject | Shared process or ordinary user privileges, no independent containment. |
| Docker/VM required on end-user or personal development machine | Reject | Violates portability and host-protection constraints; existing approved isolated Linux design remains a possible separately authorized benchmark path, not a shipped prerequisite. |

Runtime advisories must be checked on every selected patch/configuration: [Wasmtime advisories](https://github.com/bytecodealliance/wasmtime/security/advisories), including [RUSTSEC-2026-0587](https://rustsec.org/advisories/RUSTSEC-2026-0587), and [historical Wasmer filesystem advisory](https://github.com/wasmerio/wasmer/security/advisories/GHSA-4mq4-7rw3-vm5j). No runtime is declared escape-proof. Security probes and advisory review are necessary but not sufficient.

## Impact on TinyBuilder

- **Native Rust:** isolate evaluator dependency and capability growth in experimental tooling. Retain existing release entrypoint, GGUF/llama.cpp integration and read oracle. Do not add evaluator executables or interpreters to the 0.1 package.
- **Laravel:** keep `benchmarks/contained_public.py` and the separate trusted scorer/bridge semantics; introduce a backend contract only after maintainer review. Keep exact Laravel 13.42.0, reviewed Composer lock and dependency digests, real SQLite and typed observations. No stubbed framework, weakened tests or candidate-time package downloads. Existing adapter and fresh qualification gate stay intact.
- **Cross-platform distribution:** evaluate a distinct optional user-space artifact, reproducible per target, with exact hashes and notice inventories. No system-installed PHP, Node, Rust or Docker on clean users' machines. This is a future packaging goal, not proven support. Review [Wasmtime license](https://github.com/bytecodealliance/wasmtime/blob/main/LICENSE) (including exceptions/notices), [Wasmer license](https://github.com/wasmerio/wasmer/blob/main/LICENSE) and [Playground GPL metadata](https://github.com/WordPress/wordpress-playground/blob/trunk/package.json) at artifact level before redistribution.
- **Intelligence research:** inference-only proposal/retrieval improvements can proceed independently under current policy. No new claim about model correctness or training need follows from Phase 3.

## Next actions and owner decisions

1. Lead maintainer reviews this research and assigns one active implementation owner for model-free evaluator contract/prototype. Remote repository work and reviewed trusted public controls may proceed only within current authorizations.
2. Pin candidate runtime/version/features and inventory advisories/license; build the worker with trusted precompiled Wasm fixtures; establish explicit limits and a cross-platform negative test matrix. No execution of generated code.
3. Run the two PHP compatibility experiments with the same frozen, reviewed fixture and controls in authorized environments. Compare all 87 public observations and the separate nine-observation route bridge, while preserving the original PHPUnit oracle.
4. Obtain a separately approved, disposable, credential-free outer environment and verify its actual security and resource policy. Cross-platform clean-machine and native sandbox behavior require appropriate non-personal hardware or explicitly approved infrastructure. Ordinary hosted CI is not such approval.
5. Before candidate admission, independently review the exact runtime/backend and policy, pass every relevant security and trusted semantic gate, approve the scope/host/data transfer, and perform fresh preflight. If no suitable environment exists, leave candidates blocked.

Owner approval is needed for any separately provisioned evaluator, private fixture/candidate transfer, change to existing containment policy, new shipped execution capability or redistribution decision, and final candidate execution. Numeric limits (512 MiB guest, 1 GiB whole worker, 30-second deadline + 5-second cleanup, 4 MiB per output stream, 128 MiB writable delta) are provisional PoC hypotheses, not accepted defaults. No personal Windows changes or paid compute authorized.

## Agent knowledge maintenance

The existing benchmark, implementation, maintainer, onboarding, release, model research and knowledge-maintenance skills were reviewed, as were the canonical guidance and containment checkpoint. Recommend adapting the existing benchmark skill to backend-specific qualification once evidence and decisions exist; update the implementation skill with worker/TCB and fail-closed rules, release skill with lab/package separation and artifact qualification, and status with actual merge and blocker. A new sandbox-specific skill is justified only after a repeatable procedure exists. Do not relax AGENTS.md or promote research to policy. All guidance edits are deferred to lead maintainer, as instructed.
