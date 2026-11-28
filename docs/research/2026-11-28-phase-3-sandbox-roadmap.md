# Phase 3 — Portable sandbox implementation roadmap

Date: 2026-11-28. Status: proposed, not authorization to execute generated code or provision infrastructure.

Read the [complete Phase 3 report](2026-11-28-phase-3-portable-sandbox.md), [executive summary](2026-11-28-phase-3-sandbox-summary.md), [AGENTS.md](../../AGENTS.md), [agent guide](../AGENT_GUIDE.md), [release contract](../RELEASE_0_1.md), [contained evaluator](2026-11-27-contained-php-evaluator.md) and [qualification checkpoint](2026-11-27-contained-qualification.md). Closeout reviewed main [ce28337552933a671a95d1ad30baa07cfe7cc2b7](https://github.com/MrPunyapal/TinyBuilder/commit/ce28337552933a671a95d1ad30baa07cfe7cc2b7). Recheck main, active owners and policy before implementation. Every stage is model-free until explicit candidate admission. All thresholds below are proposals unless otherwise labeled.

## 1. Scope and non-goals

Build a separate lab evaluator with a typed request/observation contract and capability-restricted Wasm backend. Preserve the existing Docker-in-approved-Linux-guest design, fresh qualification gate, public scorer, private isolation, exact read oracle and normal native read-only product. Do not change semantic task definitions, reference repairs, acceptance thresholds or failure denominators to accommodate a runtime. Do not add a shell or evaluator executable to release 0.1.

A separate same-user worker is not an OS sandbox. Any experiment must respect the existing prohibition on arbitrary generated code on the owner's ordinary host. A separately approved and qualified outer boundary remains required for hostile candidates; this research proposes no policy exception. No personal Windows provisioning, hypervisor, driver, security settings, restart, system-wide install, unrelated workload changes, paid compute, model downloads or training. No private fixture or candidate transfer without separate approval.

## 2. Threat model

Assume candidate source, module bytes, runtime outputs, inputs from untrusted repositories and candidate-controlled file trees are hostile. Protect the user's data, credentials, network, system resources, other processes, project/model state, trusted fixture, evaluator and hidden oracle. Trust only reviewed supervisor, scorer, exact pinned backend/runtime, selected host imports, immutable reviewed dependencies and qualified outer environment. A native runtime compromise crosses the Wasm boundary; assume worker account privileges are available after that compromise unless a verified OS/outer boundary denies them.

| Threat | Boundary / control | Evidence required |
|---|---|---|
| Filesystem escape, links, path aliases, races | Explicit copied staging tree; no real project mounts; immutable dependency tree; safe descriptor-based staging and cleanup | Zero unauthorized reads or modifications; external canaries and tree identities unchanged |
| Network or local services | No guest networking or proxy imports; independently restricted outer environment | Zero DNS, TCP, UDP or local service access in tested profiles; positive harness controls demonstrate probes work |
| Ambient authority, inherited handles, secrets | Explicit env/handle allowlists, no host shell, no privileged APIs; outer account isolated | Zero credential or forbidden handle access; inspect actual worker authority |
| Child process abuse | No subprocess host import; outer process tree/PID policy | Zero unauthorized processes and survivors |
| CPU, memory, compilation, disk, inode and output exhaustion | Guest fuel/epoch/limits; bounded input and output; hard outer budgets, watchdog, bounded filesystem | Every exhaustion probe stops within frozen budget, no impact on unrelated workloads |
| Runtime exploit or backend mismatch | Exact runtime hashes/features/advisory review; independently qualified outer boundary | Fail closed on stale/mismatched runtime, unsupported host policy or failed preflight |
| Oracle manipulation or leakage | External typed observation scoring, one input per isolated invocation; hidden source/expected answers never mounted even read-only | Seeded/wrong/narrow controls fail; reference passes; no access to scorer, gold repair or other hidden inputs |
| Untrusted output, protocol confusion | Strict bounded schema and sanitized output; no terminal-control interpretation; no raw exceptions persisted | Reject malformed/oversized/duplicate or unexpected fields and control sequences |
| Persistence or contamination | Fresh fixture/worker for each observation; cleanup verified independently | Zero residue or running processes; subsequent clean run reproducible |
| Dependency/supply chain | Reviewed lock, exact artifact digests, license inventory, offline candidate stage | No downloads, plugins/scripts or unexpected mutable dependencies at candidate execution |

Sources: [WASI security](https://wasi.dev/security), [Wasmtime security](https://docs.wasmtime.dev/security.html), [Wasmtime ResourceLimiter](https://docs.wasmtime.dev/api/wasmtime/trait.ResourceLimiter.html), [Wasmtime advisories](https://github.com/bytecodealliance/wasmtime/security/advisories), [Windows path advisory](https://rustsec.org/advisories/RUSTSEC-2026-0587). Adversarial checks are not a proof of absence of vulnerabilities; independent review and explicit scope approval remain necessary.

## 3. Staged work packages

| Stage | Proposed owner / execution location | Dependencies | Deliverables and exit criterion |
|---|---|---|---|
| A — Contract and baseline | Lead maintainer + remote implementation agent | Reviewed research; existing scorer and release boundary | Backend request/result contract, immutable manifests, fault taxonomy, mock regression tests, no product change. Existing read oracles and CI remain unchanged. |
| B — Wasmtime kernel and trusted probes | Remote code authoring; reviewed trusted tests on ordinary CI only where policy allows; approved environment for outer tests | A; exact runtime pin, feature and advisory review | Separate experimental Rust worker and supervisor; hand-authored Wasm controls, capability denial and resource/cleanup evidence. No candidate bytes. |
| C — Language lanes | Remote engineering and trusted CI | B; approved artifact inventory | Precompiled Rust WASI control first, CPython/WASI then QuickJS/WASI. Explicit unsupported APIs and fixture parity. No arbitrary generated Rust compilation. |
| D — PHP compatibility comparison | Remote research/code; authorized disposable execution environment | A/B; approved trusted runtime artifacts, frozen Laravel fixture | Compare restricted Playground and Wasmer/WASIX PHP using identical trusted controls; measure compatibility and resources separately; retain negative findings. |
| E — Laravel parity | Benchmark owner in authorized environment | D successful for chosen lane; frozen fixture and scorer | All 12 public task bridges/87 planned observations and separate route bridge/9 observations meet existing trusted control outcomes; independent original PHPUnit oracle preserved. |
| F — Outer hardening and packaged qualification | Platform/security reviewer on separately approved infrastructure or non-personal hardware | B and chosen backend; exact package hashes | Verify actual outer permissions, process/disk/CPU/memory limits and clean standard-user lifecycle on Windows x64, macOS ARM64 and Linux x64. Unsupported host is blocked. |
| G — Candidate admission | Lead maintainer + independent evaluator reviewer; explicit owner approval | A–F relevant gates; fresh preflight, exact artifact identity, approved host and data scope | Only then allow reviewed candidate bytes in the selected qualified profile; start with existing public development campaign, record all attempts and blocks. No automatic admission. |

A and B are the critical immediate work. D can be designed in parallel by an assigned independent owner, but avoid duplicating an active agent's work. Existing approved Linux evaluator design may be pursued separately if owner approves suitable infrastructure; it is not a product runtime prerequisite. A result for one language/backend/OS does not qualify others. F may run in parallel with C–E and is mandatory before admitting hostile candidates, not a cosmetic final task.

### A — Narrow evaluator contract

Reuse existing observation/scoring boundary rather than rewriting benchmarks. Proposed contract fields (names subject to code review): schema version, run/task identifier, backend/profile identifier, exact artifact and policy digests, fixture and candidate hashes, approved relative paths, fixed entrypoint enum, explicit bounded input, limits and qualification record. Candidate cannot supply arbitrary native argv, host paths, network destination or runtime location.

Return only bounded typed observations, provenance, measurements, and explicit categories: completed candidate result; attributable candidate failure; policy/preflight blocked; infrastructure failure/unknown; cleanup failure. Maintain attempted/passed/failed/blocked/remaining denominators, with a failed preflight yielding zero attempts and all planned probes remaining. A trap or exit alone does not establish candidate fault. Use existing attribution rules and trusted controls; do not turn mocks into semantic passes.

Remote unit tests: unknown schema/profile, invalid path/manifest, artifact/qualification mismatch, unauthorized runtime, budget mismatch, ambiguous exit, malformed/oversized observations, stale preflight and failed cleanup. Every invalid request is denied before candidate handoff.

### B — Wasmtime proof of concept

Choose a security-supported version/patch after reviewing [release policy](https://docs.wasmtime.dev/stability-release.html), [advisories](https://github.com/bytecodealliance/wasmtime/security/advisories) and [embedding API](https://docs.wasmtime.dev/api/wasmtime/). Do not pin the historical research version blindly. Record exact Cargo.lock, enabled features, compiler and target, and all upstream artifact SHA-256 digests. Keep dependencies confined to the experimental lab package.

Create the supervisor before adding interpreter runtimes. Stage only reviewed fixture bytes; no host project mount. Start one worker per run with a minimal explicit guest context and no ambient network/env inheritance. Enforce fuel, epoch, aggregate guest-memory/table/instance limits, bounded host imports and independent wall deadline. ResourceLimiter does not cap all runtime/host allocations. Inspect whole-worker constraints and compile-time resource use separately. No untrusted native serialized/precompiled code admission. Use trusted authored minimal Wasm fixtures first; report denied capabilities explicitly. Review [WASI context builder](https://docs.wasmtime.dev/api/wasmtime_wasi/struct.WasiCtxBuilder.html) and [Config](https://docs.wasmtime.dev/api/wasmtime/struct.Config.html).

### C — Language proof of concept

- Rust: reviewed precompiled wasm32-wasip2 fixture with deterministic typed output; [target documentation](https://doc.rust-lang.org/rustc/platform-support/wasm32-wasip2.html). Cargo/rustc/build-script and dependency execution is a separate future qualification problem.
- Python: exact CPython/WASI artifact; [platform limitations](https://docs.python.org/3/library/intro.html?highlight=socket). Test standard-library pure computation and bounded filesystem use; reject unsupported native extensions, threading/process APIs or network rather than emulate unsafe host calls.
- JavaScript: exact QuickJS WASI artifact; [QuickJS releases](https://github.com/quickjs-ng/quickjs/releases). Verify deterministic module-level behavior and absence of Node host APIs. Do not equate QuickJS compatibility with Node compatibility.

For each language collect a successful trusted control, denied-capability controls, resource enforcement, exact artifact identity, failures and unsupported capabilities. No generated code; no language claims beyond tested features.

### D/E — PHP and Laravel proof of concept

Use identical reviewed fixture bytes, composer.lock digest, vendor tree hashes, PHP version and extension inventory as far as runtime compatibility permits. If versions or dependencies differ, record the mismatch rather than calling the result parity. Start with the eight dependency-free task bridges before the four framework-dependent tasks, then the separate HTTP route control. Verify actual PHP and Laravel bootstrap, SQLite PDO behavior, validation, responses, Composer autoload and filesystem semantics. No stubs. Keep a frozen, read-only trusted dependency snapshot and separate writable temporary app paths. Prepare dependencies only in a trusted reviewed preparation stage, never with candidate source or hidden oracle material present; candidate execution must remain offline.

| PHP candidate | Specific experiment | Rejection rule |
|---|---|---|
| Playground PHP.wasm | Verify Emscripten ABI and exact Node/JS adapters; remove network proxy, host filesystem passthrough and other unnecessary grants; inspect PHP extensions and PHPUnit building blocks | Cannot run required trusted controls without adding unqualified host access or missing required runtime semantics |
| Wasmer/WASIX PHP | Compare exact PHP package and SDK maturity; explicitly restrict network, filesystem and process interface; same fixture and controls | Required POSIX compatibility cannot be obtained under the frozen policy, or runtime/SDK cannot be qualified |
| Native PHP under platform sandbox | Only if Wasm lanes fail; separate OS-specific profile and outer qualification | Unsupported or unverified host policy; cannot preserve oracle or resource limits |
| Existing approved Linux guest + Docker | Retain existing design and gates; separately authorized infrastructure only | No approved isolated guest or failed exact-image/preflight; do not execute locally |

References: [Playground package architecture](https://wordpress.github.io/wordpress-playground/developers/architecture/php-wasm-packages/), [Node filesystem/runtime](https://wordpress.github.io/wordpress-playground/developers/local-development/php-wasm-node/), [PHPUnit guide](https://wordpress.github.io/wordpress-playground/ja/guides/phpunit-testing/), [build pipeline](https://github.com/WordPress/wordpress-playground/blob/trunk/packages/php-wasm/compile/php/Dockerfile), [Laravel requirements](https://laravel.com/framework/docs/13.x/deployment), [WASIX](https://docs.wasmer.io/runtime/wasix/), [Wasmer SDK](https://docs.wasmer.io/runtime/python/).

For semantic parity, use existing independently scored observations; reference repairs must pass, seeded baseline and known-wrong alternatives must fail, and regressions must behave identically to native trusted controls. Record counts for each task/control/observation and platform. Keep the separate nine-observation route bridge and original historical PHPUnit/read qualification oracles intact. Hidden test source and expected values stay outside guest-visible state, not merely read-only. Successful framework boot or PHPUnit startup is not parity.

### F — Platform packaging and outer isolation

Windows x64: inspect standard-user AppContainer profile/ACL and Job Object policies, actual process/resource limits, denial of loopback/network, reparse points and cleanup; no changes to the owner's PC. [AppContainer](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer), [Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).

macOS ARM64: supported entitlement-based helper and signing/hardened-runtime compatibility, minimum filesystem grants, independent supervisor and resource-limit evidence. Do not rely on unsupported custom SBPL or deprecated sandbox-exec. [App Sandbox](https://developer.apple.com/documentation/security/app-sandbox/), [Apple guidance](https://developer.apple.com/forums/thread/661939).

Linux x64: inspect whether unprivileged user namespaces and required limits are available under existing host policy; evaluate bubblewrap/nsjail or another approved outer environment. No changing host kernel policy to force success. [bubblewrap](https://github.com/containers/bubblewrap), [nsjail](https://github.com/google/nsjail).

Build separate locked packages; record inner artifact SHA-256, source SHA, build target, runtime versions/digests, exact policy, complete notices, signing status, installed/unpacked bytes and all dependencies. Review [Wasmtime license](https://github.com/bytecodealliance/wasmtime/blob/main/LICENSE), [Wasmer license](https://github.com/wasmerio/wasmer/blob/main/LICENSE), and [Playground GPL license](https://github.com/WordPress/wordpress-playground/blob/trunk/LICENSE) at artifact level, including exceptions, package-specific terms and transitive notices. No redistribution approval implied by upstream open-source status.

Clean standard-user acceptance: unpack/launch/remove offline without installing developer tools, PHP, Node, Docker, Wasmtime, hypervisor or changing machine-wide controls. Run only reviewed trusted probes at this stage. Exact packaged bits must pass the relevant security matrix, on separately authorized environments, before any candidate use. Ordinary CI smoke is not clean-machine or hostile-code qualification. Keep the 0.1 release acceptance separate.

## 4. Measurable security acceptance matrix

All tests below are **proposed**. Freeze per-backend/profile/platform thresholds before testing; every required probe must have an executed outcome, not skip or mock. Where a limit has no agreed value, record it as unmeasured and block promotion. Positive controls should demonstrate that permitted operations and the test harness work; negative tests must verify denial and independent canaries rather than trusting guest assertions.

| Gate | Proposed acceptance criterion |
|---|---|
| Identity / approval | Exact executable/runtime/fixture/policy manifest and hashes; fresh qualification record bound to environment and profile; zero candidate attempts for any mismatch or missing owner approval |
| Filesystem | Zero successful outside-root reads/writes/creates/renames/metadata changes in all negative probes; immutable dependency tree, oracle and canaries unchanged. Include absolute/parent paths, symlinks/hardlinks, Windows drive/UNC/device paths and junctions/reparse points, staging and cleanup races. |
| Network | Zero successful DNS lookups or TCP/UDP connections to loopback, LAN or Internet; no proxy host import, no inherited network; outer policy verified separately |
| Secrets / environment | Zero inherited non-allowlisted variables, handles, credential files, home/model/config paths; no candidate access to private source or scorer |
| Process | No candidate-created host process in baseline; zero surviving worker/child processes after normal completion, timeout, cancellation and crash |
| Guest memory | Hard 512 MiB aggregate starting ceiling (provisional); reject or terminate exhaustion without bypass through multiple instances/tables |
| Whole-worker memory | Provisional 1 GiB whole-worker ceiling; record enforced metric (commit, RSS or other OS definition), compilation and child accounting; no unlimited configuration; zero pressure on unrelated processes. A sampled peak alone is insufficient. |
| CPU / deadline | Every infinite-loop or blocking fixture terminates; fuel/epoch plus independent 30-second deadline and 5-second cleanup margin (provisional). Record actual CPU and wall duration. |
| Output | Hard 4 MiB each stdout/stderr (provisional); no unbounded allocation, no raw control sequences or unsafe terminal interpretation; bounded typed result schema |
| Storage | Hard 128 MiB writable delta (provisional) excluding immutable reviewed vendor; also enforce frozen inode/metadata/count budget; zero writes outside staging; no uncontrolled growth during compile/cache |
| Oracle | Expected outputs/hidden test source/gold repairs never visible to candidate; zero modifications of external scorer/fixtures; all existing positive and negative trusted controls reproduce |
| Cleanup / fault classification | Zero surviving process or staging residue, or explicit failed-cleanup block with quarantine; ambiguous exits/traps/transport/infra failure never silently become semantic failures |
| Advisory / supply chain | Zero known unmitigated High/Critical advisory affecting selected version/configuration at review time; full dependency and artifact review; unsupported version/profile fails closed |
| Cross-platform | Every required probe passes on exact qualified packaged bits for all three supported targets before claiming portable qualification; a missing platform remains unsupported/unqualified |
| Laravel | Reference/control outcomes for all 87 observations plus separate 9 route observations match trusted baseline; existing negative controls still reject; exact lock/version/extension evidence |
| Clean account | No admin rights, host system changes or external system runtime prerequisites; actual clean-user lifecycle evidence, not CI proxy |

The original research proposed 512 MiB guest memory, 1 GiB whole-worker, 30 + 5 seconds, 4 MiB/stream and 128 MiB writable delta without measurements. Calibrate these using reviewed trusted fixtures, report every changed threshold and rationale, and require maintainer review before freezing. Inode count, CPU quota, input size and other host-side compilation limits still need explicit values. Fail closed if a required limit cannot be enforced. Do not substitute polling for a hard resource boundary.

## 5. Measurement and evidence schema

Record one entry per backend/profile/target and per probe: source SHA, exact artifact and fixture hashes, runtime version, enabled features, OS/kernel, outer policy identity, owner-approved environment classification, command/config, expected behavior, actual bounded observation, attribution, attempted/passed/failed/blocked/remaining counts, cleanup status, start/end time and limits. Preserve negative and incomplete outcomes. No private paths, credentials or raw model/guest output in persistent evidence.

For trusted compatibility runs record cold/warm startup p50/p95, peak RSS and enforced memory metric, wall time, CPU, writable delta, package/archive/install size, dependency payload size and fixture-control results. Compare native trusted baseline with same fixture and frozen workload; define repetition count before runs (proposed at least 10 startup samples and 3 complete trusted suites per profile, subject to resources). Record missing metrics as null with reason. No measured latency, package size or runtime resource claim exists today. Account for combined model/evaluator memory later only after separately authorized candidate evaluation, not by assuming guest limit equals total process RSS.

## 6. Work-location and approvals

| Work | Remote repository/ordinary trusted CI | Local hardware or approved infrastructure |
|---|---|---|
| Architecture, threat model, code review, backend contract, mock tests, dependency/license review | Yes, as authorized | Not required |
| Reviewed model-free Rust/Wasm, PHP trusted fixtures and deterministic CI package tests | Yes, only existing trusted-control policy and reviewed scope; do not treat hosted CI as outer qualification | If test needs host capabilities, use authorized environment |
| PHP ABI/extension compatibility and full trusted fixture parity | Code and static preparation remote | Runtime testing in approved environment; no candidate code |
| Exact outer boundary probes including native worker compromise assumptions, host quotas and cleanup | Prepare tests remotely | Separately approved disposable environment per supported target |
| Clean-machine/standard-user packaging | Build artifacts and inspect metadata remotely | Appropriate clean Windows/macOS/Linux systems or separately approved infrastructure, not owner's everyday PC provisioning |
| Existing local inference-only proposals | Remote review of sanitized evidence | Local model/runtime measurement by active local agent under existing authorization, no generated execution |
| Generated-code/private holdout evaluation | No ordinary CI/remote host fallback | Only explicit approval for host, backend, exact artifacts, transfer scope and fresh passed containment; private transfer separately approved |

Owner decisions required: approve architectural direction and implementation owner; select/authorize separate evaluator environment and cost/resource/privacy boundary; approve any data transfer, runtime artifact redistribution and new product capability; approve change to existing containment policy if proposed later; authorize candidate evaluation only after independent review and passed gates. No standing authorization from historical provisioning or earlier research. If the owner declines or no environment exists, record blocked and continue safe model-free work.

## 7. Stop criteria and fallback decisions

- If Wasmtime kernel fails capability denial, identity, watchdog or limit tests, stop; do not widen grants. Fix or replace runtime under review.
- If PHP.wasm cannot reproduce trusted controls, test Wasmer/WASIX under the same requirements. Compare failure classes rather than lowering semantic gates. Historical [Wasmer filesystem advisory](https://github.com/wasmerio/wasmer/security/advisories/GHSA-4mq4-7rw3-vm5j) reinforces independent qualification.
- If both PHP lanes fail, consider only a separately approved native sandboxed profile or the existing approved Linux guest design. Otherwise leave PHP generated evaluation blocked. Rust/WASI, Python and QuickJS research can proceed independently.
- Reject ordinary native subprocess/working-directory/command-allowlist as containment; reject in-process runtime in supported CLI, WAMR as primary boundary for now ([configuration caveats](https://github.com/wasm-micro-runtime/wasm-micro-runtime/blob/main/doc/build_wamr.md)), mandatory Docker/VM end-user provisioning and unsupported macOS private sandbox APIs. Revisit only with evidence addressing the original rejection.
- Never convert unavailable host controls into an opt-out. Failed preflight, cleanup, advisory or oracle gate means blocked. Keep the current approved-guest mechanism intact until replacement is explicitly accepted.

## 8. Knowledge-maintenance recommendations (lead maintainer only)

Reviewed [AGENTS.md](../../AGENTS.md), [agent guide](../AGENT_GUIDE.md), [project status](../PROJECT_STATUS.md), release contract and all seven skills at the recorded main SHA. No guidance file is changed by this research PR.

| Existing guidance | Proposed reusable update |
|---|---|
| [Benchmark](../../.agents/skills/tinybuilder-benchmark/SKILL.md) | After architecture approval, add per-backend/profile/environment qualification manifests, fresh preflight, external oracle and bounded observations. Preserve outer guest gate and failure denominators until explicitly replaced. |
| [Implementation](../../.agents/skills/tinybuilder-implementation/SKILL.md) | Add TCB/host import review, same-user worker limitation, exact dependency identities, cross-platform fail-closed tests; keep lab separate. |
| [Maintainer](../../.agents/skills/tinybuilder-maintainer/SKILL.md) | Require explicit portable backend adoption and security review before candidate admission; preserve rejected alternatives and evidence. |
| [Release](../../.agents/skills/tinybuilder-release/SKILL.md) | Keep optional evaluator package separate; require per-target clean-account and signing/license evidence before any future distribution; no 0.1 scope widening. |
| [Onboard](../../.agents/skills/tinybuilder-onboard/SKILL.md) / [Project status](../PROJECT_STATUS.md) | Reconcile stale #23 pre-merge language with actual main; link Phase 3 only after maintainer acceptance and record separate implementation owner and blockers. |
| [Model research](../../.agents/skills/tinybuilder-model-research/SKILL.md) | No immediate procedure change; retain inference/semantic separation and no model downloads/training without evidence. |
| [Knowledge maintenance](../../.agents/skills/tinybuilder-knowledge-maintenance/SKILL.md) | Existing closeout procedure suffices. Record exact security evidence and failures when PoC exists. |

Do not create a new skill until repeated sandbox-specific workflows justify it. Existing guidance covers current constraints; owner requested recommendations only. Lead maintainer should run `python .agents/check_guidance.py` when changing guidance in a subsequent authorized PR.

## 9. Review checklist and next action

- [ ] Review original report and closeout clarifications; accept, adapt or reject each proposed architecture decision.
- [ ] Confirm no overlap with active local Codex work; assign one implementation owner for A/B.
- [ ] Freeze model-free contract, runtime security review and planned tests before writing implementation.
- [ ] Approve infrastructure only separately, with host/data/cost/rollback risks explicitly stated.
- [ ] Preserve current native release and existing semantic oracles; review exact diffs.
- [ ] Record all failed or skipped probes and remaining blockers; do not claim qualification from mocks, source review or CI alone.
- [ ] Only after required evidence, independent review and explicit approval, consider generated-code admission in the exact qualified profile.

**Recommended next work:** lead maintainer review followed by a narrowly scoped model-free evaluator contract and Wasmtime trusted-control PoC. PHP compatibility lanes remain conditional. Live generated execution, release qualification, model training and new downloads are not authorized by Phase 3. No implementation or experiments were performed in this documentation closeout.
