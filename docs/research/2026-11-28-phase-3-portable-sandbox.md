# TinyBuilder Deep Research Phase 3 — Portable Sandboxed Execution

Research date: 2026-11-27. Repository closeout: 2026-11-28.

Status: research and proposed decisions only; not evaluator qualification or authorization. The original report is preserved below with ordinary Markdown source links, followed by closeout clarifications.

## Executive assessment and repository baseline

TinyBuilder has reached the point where **execution isolation, not model intelligence or benchmark design, is the gating systems problem**. The verified merge commit `ce28337552933a671a95d1ad30baa07cfe7cc2b7` integrated Coding Intelligence v1 through PR #23 after seven successful workflows, while explicitly stating that the merge did **not** qualify a live evaluator or authorize generated-code execution. PR #23 records 12 public corpus bridges, two private trusted-control tasks, 87 public behavioral observations, a separate real-Laravel route bridge, and a contained evaluator that remains model-free until an isolated execution environment is qualified. [Merge commit][merge] · [PR #23][pr23]

The repository's safety posture is unusually clear. `AGENTS.md` says arbitrary generated code must never run on the owner's ordinary host and specifically suspends provisioning of the personal Windows machine for evaluator isolation; it prohibits installing or removing hypervisors, drivers, OS features, services, or machine-wide security controls as routine project work. [AGENTS.md][agents] · [Merge commit][merge] The benchmark guidance likewise says that if a separate qualified evaluator is unavailable, TinyBuilder must record a blocker rather than fall back to host execution, and ordinary CI must not be mistaken for a qualified outer sandbox. [Merge commit][merge]

The current native product direction should remain separate from this work. The repository describes the release target as a standalone Rust, offline, read-only assistant for Windows x64, macOS ARM64, and Linux x64; mutation and execution are explicitly excluded from the supported interface, and the release contract says the current product is not an OS sandbox. [Repository][repo] · [Release contract][release] The repository has also advanced substantially beyond the historical Python prototype: current `main` exposes a native Rust tree and 157 commits in the repository view. [Repository][repo] **Recommendation:** Phase 3 should therefore create a *separate evaluator security boundary and backend*, not add execution privileges to the normal product CLI.

The existing benchmark machinery is already structured well for that separation. PR #23 added `contained_php.py`, `contained_public.py`, `qualify_contained_php.py`, corpus controls, independent scoring and a trusted-framework workflow. That workflow builds a reviewed Laravel 13 dependency tree, pins Laravel application/framework versions, uses PHP 8.5 with SQLite-related extensions, performs Composer installation with plugins and scripts suppressed during dependency acquisition, and then runs only repository-authored bridge controls. [Merge commit][merge] The architectural task is therefore not to replace the oracle; it is to put a trustworthy execution backend behind it.

**Primary conclusion:** the best fit is a **Rust-native Wasmtime/WASI sandbox as TinyBuilder's portable security kernel, hosted in a separate evaluator worker process**, with language runtimes layered above it. This gives the project a common no-admin, no-system-install foundation on Windows, macOS, and Linux. PHP is the exception: current WordPress PHP.wasm is Emscripten/JavaScript-hosted rather than ordinary WASI, so real Laravel support requires a separate compatibility lane and cannot yet be claimed as solved. [Wasmtime security][wt-security] · [WASI security][wasi] · [PHP.wasm packages][php-packages] · [PHP overview][php-overview]

That recommendation is deliberately **not** a claim that Wasmtime is an unbreakable sandbox. Wasmtime treats sandbox integrity as a security-critical property, and its current advisory history demonstrates why TinyBuilder still needs version pinning and defense in depth: a High-severity Windows WASI filesystem escape involving drive-prefixed paths was published on November 19, 2026, alongside additional November advisories. [Security bug policy][wt-bugs] · [Wasmtime advisories][wt-advisories] · [RustSec advisory][rustsec]

## Threat model and required trust boundary

The adversary for Phase 3 must be modeled as **arbitrary hostile candidate code**, not merely buggy generated code. Candidate PHP, Python, JavaScript or Rust may intentionally attempt path traversal, symlink and reparse-point abuse, process creation, network access, resource exhaustion, terminal-control injection, benchmark-oracle tampering, dependency abuse and runtime exploitation. This is consistent with TinyBuilder's existing requirement that generated PHP remain blocked until containment is independently qualified. [PR #23][pr23] · [Merge commit][merge]

The assets requiring protection are: the user's files outside the evaluation workspace; credentials, SSH material and browser/application data; TinyBuilder's own configuration and model/runtime state; the host network and localhost services; benchmark hidden tests and expected answers; the trusted evaluator/oracle; and host availability. WASI is attractive precisely because its default model differs from a conventional host process: a WASI component begins without ambient authority and obtains only capabilities explicitly supplied by the host. A component without filesystem or network capabilities cannot exercise those facilities through WASI. [WASI security][wasi]

The proposed trust boundary should treat the **TinyBuilder orchestrator, evaluator worker executable, pinned Wasmtime version, host-side capability implementation and explicitly approved language-runtime artifacts** as trusted computing base. Generated source, generated binaries, stdout/stderr, dependency input originating from an untrusted project, model output and all candidate-controlled filesystem content remain untrusted. Wasmtime's own model reinforces the importance of keeping host imports minimal: Wasm code has no direct syscall surface and interacts with its environment only through imported interfaces supplied by the embedder. [Wasmtime security][wt-security] · [Embedding API][wt-api]

The key attack classes and corresponding design requirements are:

| Threat | Required boundary |
|---|---|
| Read/write host files | No host filesystem capability except a dedicated staging tree; read-only dependencies separate from writable workspace |
| Path traversal / symlink / Windows path alias | WASI preopens plus explicit adversarial tests for `..`, absolute paths, symlinks, junctions/reparse points, UNC/device paths and drive-prefixed components |
| Network exfiltration / localhost attack | Supply no network capability; never call Wasmtime's network-inheritance API |
| Process escape | No subprocess capability in the baseline; guest execution stays inside the Wasm runtime |
| CPU loop | Fuel plus epoch interruption plus an independent native wall-clock deadline |
| Memory exhaustion | Wasmtime guest-memory limits plus an outer worker-level memory ceiling |
| Disk/output exhaustion | Bounded writable workspace and hard stdout/stderr limits |
| Runtime exploit | Dedicated worker process, current security-supported runtime, advisory gate, optional OS containment |
| Oracle tampering | Hidden tests and scorer outside guest-visible writable tree |
| Terminal injection | Treat guest output as data and sanitize/control-escape it before display |
| Persistence | Disposable workspace; worker and all temporary artifacts removed after each run |
| Supply-chain attack | Pinned hashes, exact artifact inventories and no runtime package downloads |

Wasmtime's preopened-directory API is capability-oriented and explicitly prevents normal `..` traversal outside the granted root. [WASI context source][wt-ctx-src] · [WASI context builder][wt-ctx] This is a strong primitive, but the November 2026 Windows advisory proves TinyBuilder must test Windows-specific lexical and path-resolution edge cases independently rather than treating the abstract WASI guarantee as sufficient evidence. [Wasmtime advisories][wt-advisories] · [RustSec advisory][rustsec]

Network policy should be simpler: **grant none**. Wasmtime exposes an API that can inherit all host-accessible network addresses, which is exactly what TinyBuilder should avoid; WASI networking is capability-controlled and can be omitted completely. [Network interface][wt-net] · [WASI C API][wt-capi] For benchmark execution there is no security justification for DNS, localhost or Internet access.

Resource exhaustion needs two layers because Wasmtime's `ResourceLimiter` does **not** account for all host allocations; it covers guest instances, memories and tables, while Wasmtime metadata and embedder allocations remain outside that accounting. [ResourceLimiter][wt-limiter] Likewise, fuel gives deterministic bounded WebAssembly execution, while epoch interruption is a lighter-weight mechanism for external interruption; neither should be the sole watchdog for a security-sensitive evaluator. [Config][wt-config] · [Store][wt-store] The worker process therefore needs an independent wall-clock kill path and, where available, an OS-level memory/process limit.

A final threat often missed in local-agent sandboxes is **host-terminal attack via output**. Wasmtime's security guidance has historically treated untrusted guest output as potentially hostile host input. TinyBuilder should never directly relay arbitrary terminal escape sequences from candidate stdout/stderr; the evaluator should capture bounded bytes and convert them to sanitized structured result fields before the normal CLI renders them. This is a host-interface rule, not a guest-language rule. [Wasmtime security][wt-security]

## Technology findings

### WebAssembly, WASI and Wasmtime

WebAssembly provides the strongest portable baseline found in this research. Wasmtime documents bounds-checked linear memory, structured and type-checked control flow, inaccessible native call-stack details and an import/export-only interface to the host. Its WASI implementation then adds capability-based filesystem access on top. [Wasmtime security][wt-security] WASI itself explicitly defines the no-ambient-authority model TinyBuilder needs: filesystem, network, environment, clock and other interfaces are granted by the host rather than inherited from the user's account. [WASI security][wasi]

Wasmtime also integrates naturally with TinyBuilder's native Rust direction. Its official Rust crate is an embedding API, while `wasmtime-wasi` supplies WASI interfaces, so TinyBuilder does not need a separately installed Wasmtime executable. Compile-time features allow the embedded footprint to be reduced by excluding capabilities the evaluator does not need. [Embedding API][wt-api] The project is Apache-2.0 licensed. [License][wt-license]

Maintenance is active and predictable but nontrivial. Wasmtime publishes a major release roughly monthly; versions divisible by 12 are LTS for 24 months, while ordinary releases are supported for two months, and security fixes are backported to supported versions. [Release process][wt-release-policy] The current major release found during this research is Wasmtime 51.0.0, released November 20, 2026. [Releases][wt-releases] TinyBuilder should **not** simply depend on "latest"; it should select either an LTS or a specifically security-cleared current patch and maintain an advisory gate.

This caution is material, not theoretical. The Wasmtime advisory page currently includes the November 19 Windows drive-prefixed-path WASI sandbox escape and several other November issues. [Wasmtime advisories][wt-advisories] RustSec lists affected version ranges for that filesystem vulnerability, showing that security qualification must be done against an exact patch, feature set and OS. [RustSec advisory][rustsec] **Verified capability:** Wasmtime supplies the primitives necessary for a strong portable evaluator. **Unverified hypothesis:** a particular Wasmtime release/configuration is sufficient for TinyBuilder until the project's own adversarial suite has qualified that exact build.

### PHP.wasm, WordPress Playground, Laravel and Composer

WordPress Playground proves that substantial PHP workloads can run inside WebAssembly. Its PHP runtime is built with Emscripten and has platform-specific browser and Node.js adapters; `@php-wasm/node` supplies Node-specific networking, file-locking and filesystem helpers. [PHP.wasm packages][php-packages] · [Compiling PHP][php-compiling] The Node-targeted build can support web requests, Composer package installation and even MySQL connectivity when the required proxy/integration is supplied. [PHP overview][php-overview] It starts with an in-memory filesystem, and host paths can be mounted explicitly through Node-specific helpers. [Node development][php-node]

Playground also demonstrates important compatibility building blocks: its PHP build includes SQLite/PDO SQLite, OpenSSL, cURL and optional mbstring-related configuration in its official build pipeline. [Build pipeline][php-build] Its CLI can execute Composer-installed PHPUnit suites inside WebAssembly-backed PHP. [PHPUnit guide][phpunit] WordPress Playground uses native SQLite support for its PHP runtime, although its WordPress database layer includes WordPress-specific SQL translation and therefore should not be confused with evidence for Laravel. [WordPress support][wp-support]

Laravel 13 requires PHP 8.3+ and extensions including cURL, DOM, Fileinfo, Mbstring, OpenSSL, PDO, Session and Tokenizer. [Laravel deployment][laravel-deploy] TinyBuilder's trusted workflow already creates a real Laravel 13 tree and runs repository-authored PHP controls with PHP 8.5 and SQLite. [Merge commit][merge] Laravel itself officially supports running its tests via `vendor/bin/phpunit`, Pest or `php artisan test`. [Laravel testing][laravel-test]

The blocker is architectural: **WordPress Playground's PHP.wasm is not a normal WASI PHP runtime that can simply be instantiated inside Wasmtime.** It is an Emscripten PHP build whose runtime API depends on JavaScript/Emscripten glue and, for Node functionality, Node-specific adapters. [PHP.wasm packages][php-packages] · [PHP overview][php-overview] · [Compiling PHP][php-compiling] Therefore the security boundary for a Playground-based evaluator would include a JavaScript engine/Node runtime and Playground's host adapters, not merely Wasmtime's capability surface.

There is currently **no primary-source evidence found that unmodified Laravel 13.42 plus TinyBuilder's exact Composer dependency tree and PHPUnit suite runs successfully under WordPress PHP.wasm**. Playground's successful PHPUnit story is WordPress-oriented and does not establish Laravel compatibility. [PHPUnit guide][phpunit] · [WordPress support][wp-support] This must remain labeled **HYPOTHESIS** until a later, authorized PoC measures it.

A promising alternative is Wasmer/WASIX. Current Wasmer documentation provides prebuilt Python, PHP and JavaScript runtimes, says networking is disabled unless enabled, and supports local sandbox execution without Docker or a VM. [Wasmer Python SDK][wasmer-python] · [WASIX][wasix] WASIX extends WASI with POSIX-like threads, processes and sockets, which improves application compatibility. [WASIX][wasix] However, Wasmer's sandbox SDK is currently described by the project as alpha. [Wasmer repository][wasmer] **Hypothesis:** Wasmer's PHP/WASIX package may reach Laravel compatibility sooner than Playground-on-Node while preserving a Wasm-based boundary; that has not been verified against TinyBuilder's Laravel fixture.

Composer should not be permitted to fetch arbitrary packages during candidate evaluation. TinyBuilder's existing trusted workflow already separates dependency preparation from candidate execution and invokes Composer with plugins/scripts constrained during the reviewed setup. [Merge commit][merge] The safest Phase 3 design is to make `composer.lock` plus an exact, trusted `vendor/` snapshot part of the evaluator fixture and then run PHPUnit against that frozen tree with network disabled. Composer itself can execute plugins and scripts in ordinary workflows, so network resolution and arbitrary install hooks unnecessarily enlarge the candidate attack surface; TinyBuilder does not need them merely to evaluate a patch.

### Python, JavaScript and Rust

Python has a credible WASI lane. CPython's current documentation supports `wasm32-wasi`, but explicitly warns that WebAssembly builds expose only a subset of POSIX: process-related APIs do not work, threading support is unavailable in standard WASI builds, sockets are constrained and filesystem semantics differ from ordinary Unix. [Python platform notes][python] · [Threading][python-thread] Those limitations are security advantages for code-evaluation tasks that need files and pure computation, but compatibility disadvantages for packages expecting subprocesses, native extensions or normal sockets.

JavaScript has an especially lightweight path through QuickJS. QuickJS-ng's November 1, 2026 release publishes a `qjs-wasi.wasm` asset of about 1.5 MB and a WASI reactor build of about 1.49 MB. [QuickJS-ng releases][quickjs] Vercel's `quickjs-wasi` similarly targets WASI preview 1, imports only a narrow WASI surface plus a host callback, and exposes explicit memory and interruption controls; its dynamic extension ABI is documented as experimental. [QuickJS WASI][quickjs-wasi] This makes QuickJS a good evaluator for algorithmic and module-level JavaScript tasks, but **not** a drop-in Node.js compatibility environment.

Rust is the cleanest language fit when code is already compiled to Wasm. Rust currently ships `wasm32-wasip1`, `wasm32-wasip2` and `wasm32-wasip3` targets; `wasm32-wasip2` is Tier 2, supports `std`, emits WebAssembly components and can be run by Wasmtime. [Rust platform support][rust-targets] · [wasm32-wasip2][rust-p2] The problem is compilation: evaluating arbitrary generated Rust *source* requires `rustc`, Cargo and potentially crates, so the compiler itself becomes a large and resource-intensive untrusted-workload substrate. The Phase 3 portable sandbox should therefore support **precompiled Rust Wasm first**; sandboxed source compilation is a later problem, not something that should delay qualification of the execution kernel.

## Architecture comparison

The following ratings separate verified security properties from compatibility assumptions.

| Architecture | No-admin / portable | Security boundary | Laravel/PHP compatibility | Resource control | Size / performance | License & maintenance | Complexity / escape risk | Verdict |
|---|---|---|---|---|---|---|---|---|
| **Wasmtime + WASI in Rust worker** | **Yes**, embedded library across target OSes | Strong Wasm memory isolation + capability-based WASI; no ambient filesystem/network by default ([security][wt-security], [WASI][wasi]) | **Low today for PHP**; excellent for WASI-native guests | Fuel, epoch, guest resource limiter; outer worker still needed for total RSS/wall-clock ([Config][wt-config], [limiter][wt-limiter]) | Native-grade JIT/AOT; exact embedded size is **unmeasured** | Apache-2.0; monthly release/LTS program ([policy][wt-release-policy], [license][wt-license]) | Moderate implementation complexity; runtime CVEs remain possible, including recent Windows path escape ([advisories][wt-advisories]) | **Recommended security kernel** |
| **PHP.wasm + Playground Node adapter** | Portable if all assets/runtime are bundled; no system PHP required | Wasm plus Emscripten/JS/Node host surface; broader TCB than WASI-only ([packages][php-packages], [overview][php-overview]) | **Potentially high**, but Laravel 13 is **unverified** | Must be implemented around JS/Node worker; Playground alone is not the policy kernel | Likely substantially larger than pure Wasmtime; **not measured** | Playground repo GPL-2.0-or-later ([package metadata][wp-package], [license][wp-license]) | Higher host-API attack surface; Node adapters require careful restriction | **Experimental PHP lane only** |
| **Wasmer / WASIX** | Cross-platform runtime; embedded/local sandbox model | Wasm sandbox with explicit file/network controls according to Wasmer docs ([docs][wasmer-docs], [SDK][wasmer-python]) | Prebuilt PHP/Python/JS and POSIX-like extensions improve compatibility ([WASIX][wasix]) | Sandbox SDK exposes process/files/network controls | **Not measured** for TinyBuilder | MIT; sandbox SDK currently alpha ([license][wasmer-license], [repository][wasmer]) | More POSIX capability means larger surface; maturity lower for this use | **Best fallback PHP experiment** |
| **Windows AppContainer + Job Object** | Windows only; AppContainer profiles are per-user ([launch][win-launch], [profile][win-profile]) | Strong OS token/capability boundary; network denied without capability ([launch][win-launch]) | Native PHP compatibility potentially excellent | Job Objects can constrain processes, committed memory and CPU/time ([limits][win-limits], [jobs][win-jobs]) | Native process overhead | OS feature; no third-party license issue | **No-admin behavior must still be qualified on TinyBuilder targets**; Windows-only | **Optional defense-in-depth / native fallback** |
| **macOS App Sandbox helper** | macOS only; supported via signed entitlements | OS-enforced entitlement sandbox ([App Sandbox][apple-sandbox], [protecting data][apple-data]) | Native PHP possible if bundled | OS controls; evaluator-specific limits still needed | Native overhead | Apple platform facility | Requires packaging/signing design; arbitrary custom SBPL profiles unsupported ([forum discussion][apple-forum1], [DTS guidance][apple-forum2]) | **Optional packaged defense-in-depth** |
| **bubblewrap / nsjail** | Linux only; depends on user namespaces | Namespaces + mounts + seccomp/rlimits/cgroups depending tool ([bubblewrap][bwrap], [nsjail][nsjail]) | Native PHP excellent | Strong when kernel features/config available | Low overhead | FOSS | Unprivileged user namespaces may be disabled; not portable | **Linux fallback, never universal baseline** |
| **WAMR** | Very broad platform support, small-footprint orientation ([README][wamr]) | Wasm sandbox, but project docs explicitly warn it is not secure on every platform/configuration ([build documentation][wamr-build]) | Limited PHP story | Configurable | Potentially very small | Open source | Recent advisory list includes critical sandbox-relevant issues; security depends heavily on build configuration ([security][wamr-security]) | **Not recommended for TinyBuilder's primary boundary** |
| **Docker / VM** | Fails stated priority: normally requires system/container/hypervisor provisioning | Stronger compatibility/isolation when correctly configured | Excellent | Mature | Largest footprint/operational cost | FOSS options exist | Violates TinyBuilder host-protection constraints | **Out of scope as primary solution** |

Two observations dominate this comparison.

First, **there is no single native-process sandbox with the same supported, no-admin semantics on Windows, macOS and Linux**. Windows AppContainer is capable but Windows-specific; Apple's supported product sandbox is entitlement-based rather than an arbitrary per-command sandbox; Linux user-namespace tools depend on kernel policy. [AppContainer][win-launch] · [Apple forum][apple-forum1] · [bubblewrap][bwrap] · [nsjail][nsjail] This makes native isolation a valuable *second layer*, but a poor universal first layer.

Second, Wasm is not automatically safe merely because the bytecode format is sandboxed. The runtime and host imports are part of the security boundary, and current advisory histories for Wasmtime and WAMR show that sandbox escapes and host-memory defects do occur. [Wasmtime advisories][wt-advisories] · [WAMR security][wamr-security] The design should therefore assume a possible Wasm-runtime compromise and minimize what the evaluator worker can see even after such a compromise.

## Recommended architecture for TinyBuilder

The recommended design is a **two-tier evaluator architecture**:

```text
TinyBuilder normal Rust CLI
        │
        │ typed evaluation request
        ▼
Evaluator supervisor
  - creates disposable staging tree
  - injects candidate + trusted fixture
  - keeps hidden oracle outside candidate-visible tree
  - launches one evaluator worker
  - enforces wall clock / whole-process cleanup
        │
        ▼
Evaluator worker process
  - embeds pinned Wasmtime
  - minimal feature set
  - no inherited network
  - no inherited environment/secrets
  - bounded stdio
  - WASI workspace capability only
  - fuel + epoch + guest memory limits
        │
        ├── Rust/WASI guest
        ├── CPython/WASI guest
        ├── QuickJS/WASI guest
        └── future WASI-compatible language runtimes

Separate experimental lane:
Evaluator worker
        └── PHP compatibility backend
              ├── PHP.wasm + tightly restricted JS host, or
              └── Wasmer/WASIX PHP
```

**The worker should be a separate process, even though Wasmtime embeds cleanly in Rust.** This is a defense-in-depth decision: an in-process Wasmtime escape would land directly inside TinyBuilder's main process and its credentials/state; a worker escape lands first in a short-lived process that should receive only staging-directory state. Wasmtime's own architecture makes guest isolation strong, but its active security advisory history justifies reducing the blast radius of runtime compromise. [Wasmtime security][wt-security] · [Advisories][wt-advisories]

The supervisor should construct the workspace rather than expose the real project directory. Candidate code receives an ephemeral `/workspace`, plus an optional read-only `/deps` or equivalent dependency tree. The home directory, TinyBuilder config, model path, SSH directories, repository `.git`, benchmark scorer and hidden expected outputs should never be preopened. WASI already defaults to no filesystem access until preopens are configured. [WASI context source][wt-ctx-src] · [WASI context builder][wt-ctx]

Networking should have **no configuration switch in the first qualified evaluator**. Do not call `inherit_network`, do not supply socket capabilities, do not expose localhost and do not pass host proxy environment variables. Wasmtime's API makes host-wide networking an explicit grant; omitting it is simpler and safer. [Network interface][wt-net] · [WASI C API][wt-capi] If a later benchmark genuinely requires networking, it should be a new evaluator profile with explicit destination capabilities rather than a widening of the baseline.

For execution limits, use all of the following: Wasmtime fuel to bound guest instructions; epoch interruption as a secondary asynchronous interruption mechanism; a `ResourceLimiter` for guest memories/tables/instances; bounded captured output; a supervisor wall-clock timer; and OS-level whole-worker limits where they are available without weakening portability. [Config][wt-config] · [ResourceLimiter][wt-limiter] The outer timer is essential because Wasmtime's guest resource limiter is explicitly not a total host-memory accounting mechanism. [ResourceLimiter][wt-limiter]

The API between TinyBuilder and the evaluator should be **typed and narrow**, not shell-shaped. A request might contain a task identifier, runtime identifier, immutable fixture manifest, input file digests, candidate patch/source and a fixed entrypoint enum such as `PhpUnit`, `PythonModule`, `QuickJsScript` or `WasiCommand`. The evaluator should not accept arbitrary host argv from the model. This aligns with the existing TinyBuilder philosophy that command allowlists are not an OS sandbox and with PR #23's explicit containment gate. [Repository][repo] · [PR #23][pr23]

For Laravel, preserve the existing independent oracle. Build or otherwise obtain a **trusted, pinned fixture containing `composer.lock`, `vendor/`, application files and SQLite state before candidate execution**. Candidate code runs only after that fixture is copied into the isolated workspace. Hidden tests should either be inserted read-only immediately before the test run or executed by a trusted wrapper whose source is inaccessible to the candidate. TinyBuilder's existing workflow already demonstrates a reviewed dependency-preparation phase and repository-authored controls; Phase 3 should reuse that semantic boundary. [Merge commit][merge]

The PHP lane should be treated as a **compatibility backend, not the common security abstraction**. WordPress PHP.wasm is valuable because it demonstrates real PHP, SQLite, Composer-related capability and PHPUnit, but its Emscripten/Node architecture means its host API must be audited independently. [PHP packages][php-packages] · [PHP overview][php-overview] · [PHPUnit guide][phpunit] If a restricted Playground backend cannot run TinyBuilder's exact Laravel 13 fixture without opening dangerous host APIs, the fallback should be Wasmer/WASIX PHP research, followed only then by platform-native PHP sandboxes. Wasmer documents a local PHP runtime and disabled-by-default networking, but its SDK maturity remains alpha and therefore it should not outrank Wasmtime for the generic evaluator kernel. [Wasmer SDK][wasmer-python] · [Wasmer repository][wasmer]

For optional host defense in depth, the worker can later be placed inside a **Windows AppContainer plus Job Object**, a **macOS App-Sandboxed helper** in a signed package, or a **Linux bubblewrap/nsjail layer** where unprivileged user namespaces are available. [AppContainer][win-launch] · [Job limits][win-limits] · [Apple developer forum][apple-process] · [bubblewrap][bwrap] · [nsjail][nsjail] The portable evaluator must still remain safe when those extra layers are unavailable; otherwise TinyBuilder would recreate the machine-provisioning problem Phase 3 is intended to avoid.

## Fallbacks and proof-of-concept roadmap

The PoC should proceed in ascending compatibility order rather than beginning with Laravel. This is important because each stage isolates a different security property and keeps failures attributable.

**Stage A — evaluator contract, model-free.** Define the conceptual `EvaluatorBackend` boundary and a manifest format for immutable inputs, writable paths, runtime, memory, fuel, wall timeout, output ceiling and expected result channel. No model-generated source is involved. The existing repository already distinguishes infrastructure qualification from semantic/model qualification and requires blocked/remaining counts when containment is unavailable. [PR #23][pr23] · [Merge commit][merge]

**Stage B — Wasmtime security micro-suite.** In a future authorized implementation, use only hand-authored benign/adversarial fixtures to verify filesystem denial, network absence, environment minimization, stdout bounding, fuel exhaustion, memory denial and timeout cleanup. The Windows suite must specifically include drive-prefix and path-component cases implicated by the November 2026 advisory. [Wasmtime advisories][wt-advisories] · [RustSec advisory][rustsec] No benchmark candidate code should execute until these probes pass on all supported OS targets.

**Stage C — language runtimes.** Start with Rust `wasm32-wasip2`, because the Rust target has direct Wasmtime support; then add a CPython WASI runtime for scripts that do not require subprocesses/threads; then QuickJS WASI for JavaScript. [Rust WASIp2][rust-p2] · [Python platform notes][python] · [QuickJS releases][quickjs] These lanes establish that the evaluator can support multiple languages without changing its capability model.

**Stage D — PHP compatibility comparison.** Test two isolated candidates using the same frozen Laravel fixture: (a) Playground PHP.wasm with its Node/Emscripten integration stripped to the minimum required filesystem interface and no network proxy, and (b) Wasmer/WASIX PHP. Playground has verified PHP/SQLite/PHPUnit building blocks; Wasmer has a prebuilt PHP package and WASIX POSIX extensions, but neither has been verified here against TinyBuilder's Laravel 13 benchmark. [PHPUnit guide][phpunit] · [PHP build pipeline][php-build] · [WASIX][wasix] The outcome should be evidence, not an architectural commitment made in advance.

**Stage E — real Laravel trusted control.** Only after PHP runtime qualification, run TinyBuilder's existing *repository-authored trusted control*, not generated code, inside the sandbox and compare its behavior with the existing trusted baseline. The current CI setup already proves the control against real Laravel/PHP outside the proposed new runtime, making it a useful compatibility oracle. [Merge commit][merge] If the Wasm PHP lane cannot reproduce the trusted baseline, that is a compatibility failure—not a reason to relax isolation.

**Stage F — optional OS hardening.** Add Windows AppContainer/Job Object, macOS App Sandbox helper and Linux user-namespace containment as platform-specific wrappers. AppContainer capabilities can deny network and restrict resource access; Windows jobs provide process/memory/time limits. [AppContainer][win-launch] · [Job limits][win-limits] Apple's supported sandbox is entitlement-driven, while arbitrary `sandbox-exec`/SBPL profiles are not a supported third-party product API, so TinyBuilder should not build its macOS backend around `sandbox-exec`. [Apple forum][apple-forum1] · [DTS guidance][apple-forum2] Linux bubblewrap/nsjail should be conditional because unprivileged user namespaces may be unavailable under host policy. [bubblewrap][bwrap] · [nsjail][nsjail]

**Stage G — generated candidate admission.** Only after all acceptance criteria below pass should the existing contained public scorer be allowed to hand candidate source to the evaluator. This preserves PR #23's explicit rule that infrastructure/preflight failure leaves candidate trials blocked rather than reclassified as candidate failures. [PR #23][pr23] · [Merge commit][merge]

If PHP-on-Wasm fails, the fallback order should be: **Wasmer/WASIX PHP → platform-native sandboxed PHP worker → retain generated PHP as blocked**. Native PHP should never be run merely because it is compatible. On Linux, bubblewrap/nsjail may supply acceptable native isolation; on Windows an AppContainer/Job Object combination is plausible; on macOS an appropriately packaged App Sandbox helper may be viable. [AppContainer][win-launch] · [App Sandbox forum][apple-tag] · [nsjail][nsjail] Because these do not provide one common cross-platform implementation, they are fallbacks rather than the principal architecture.

Docker and full VMs remain useful external validation environments, but they should not become TinyBuilder runtime dependencies under the stated Phase 3 constraints. The repository explicitly forbids routine hypervisor/system provisioning on the owner's ordinary machine. [AGENTS.md][agents]

## Security acceptance criteria, blockers and unresolved decisions

Promotion from "experimental evaluator" to "qualified isolated evaluator" should require **measurable negative guarantees**, not merely successful PHPUnit output. The following gates are recommended. Numeric resource limits marked **provisional** are architectural decisions made here because the repository does not specify them; they must be calibrated against measured Laravel behavior before becoming permanent policy.

- **Filesystem:** Across Windows x64, macOS ARM64 and Linux x64, all adversarial probes must produce **zero successful reads, writes, creates, renames or metadata-changing operations outside the assigned workspace**. The suite must cover absolute paths, `..`, symlinks, hard links where applicable, Windows drive-relative/drive-prefixed names, UNC/device paths and reparse/junction behavior. The Windows drive-prefix class is mandatory because Wasmtime disclosed a WASI escape in that area on November 19, 2026. [Advisories][wt-advisories] · [RustSec][rustsec] Hidden benchmark material and the scorer must never appear in the guest-visible filesystem.
- **Network:** **Zero successful DNS resolutions or TCP/UDP connections** to loopback, LAN or Internet addresses in the baseline evaluator. No network inheritance API may be configured. WASI permits network capabilities only when the host grants them. [WASI security][wasi] · [C API][wt-capi]
- **Processes:** The WASI baseline must expose **no subprocess capability**. CPython's WASI process APIs already fail by design, and the evaluator contract should preserve that restriction rather than emulate host process spawning. [Python notes][python] After timeout or completion, the supervisor must find **zero surviving evaluator-owned worker/child processes**.
- **Memory:** Guest linear memory must have a hard configured ceiling; **512 MiB guest memory and 1 GiB whole-worker memory are provisional starting values, not measured requirements**. Qualification must prove that adversarial allocation cannot push the worker above the selected whole-process threshold. This outer gate is necessary because Wasmtime's `ResourceLimiter` does not cover all runtime/embedder allocations. [ResourceLimiter][wt-limiter]
- **CPU and wall time:** Every infinite-loop fixture must terminate through fuel or interruption; a second independent supervisor deadline must terminate the worker even if guest-level interruption fails. **Thirty seconds per task plus a five-second forced-cleanup margin is a provisional policy**, chosen without benchmark timing evidence and subject to later measurement. Wasmtime provides fuel and epoch mechanisms but neither substitutes for the supervisor watchdog. [Config][wt-config] · [Store][wt-store]
- **Output:** stdout and stderr must be bounded before storage/display; **4 MiB per stream is a provisional ceiling**. Raw ANSI/control sequences from candidate output must never be written directly to the user's terminal.
- **Writable storage:** Only the staging workspace may be writable. A separate read-only dependency tree is preferable. A **128 MiB writable-delta quota is a provisional initial target** and should exclude the trusted read-only `vendor/` snapshot so ordinary Laravel dependencies do not consume the candidate-write budget.
- **Environment:** Guest-visible environment variables must be an explicit allowlist. Qualification should assert absence of home paths, authentication tokens, proxy variables, model paths, SSH state and TinyBuilder persistent-memory locations.
- **Oracle integrity:** Deliberate attempts to modify, delete, shadow or infer hidden tests must produce zero oracle changes. Candidate-visible state should contain only the public task surface and trusted runtime dependencies. PR #23 already requires private fixture/source material to remain outside candidate-facing roots. [PR #23][pr23]
- **Runtime failure attribution:** A worker crash, timeout, runtime trap, failed cleanup or policy ambiguity must be classified as **infrastructure blocked/failure**, not silently scored as a candidate semantic failure. This matches TinyBuilder's current contained-evaluator accounting model. [Merge commit][merge]
- **Version security:** The exact Wasmtime/alternative runtime patch and enabled Cargo features must have **no known unmitigated High or Critical advisory affecting the selected configuration** at qualification time. Wasmtime's supported-release policy makes security patching practical, but the November advisory set shows this gate must be continuous rather than one-time. [Release policy][wt-release-policy] · [Advisories][wt-advisories]
- **Cross-platform repeatability:** Every security probe must pass against the exact packaged evaluator bits on all three supported targets, and hashes of the evaluator/runtime artifacts must be recorded. TinyBuilder already uses exact artifact/hash provenance for native release work, so the evaluator should adopt the same evidentiary standard. [Release audit][release-audit]
- **Laravel compatibility:** Before generated PHP is admitted, the existing trusted Laravel control must produce equivalent semantic outcomes inside the selected PHP sandbox and the ordinary trusted baseline. Laravel 13's PHP/extension requirements must all be present in the selected runtime. [Laravel deployment][laravel-deploy] · [Merge commit][merge]
- **No host prerequisites:** A clean user account must be able to launch the packaged evaluator without admin rights, enabling OS features, installing Docker/PHP/Node/Rust, configuring a hypervisor or changing machine-wide policy. This is a TinyBuilder project requirement, not yet a verified property of any proposed implementation. [AGENTS.md][agents]

Several important claims remain **unmeasured or blocked**.

**Laravel-on-PHP.wasm is unverified.** WordPress Playground proves impressive PHP-on-Wasm compatibility and PHPUnit operation, but no current primary source found in this research demonstrates TinyBuilder's exact Laravel 13.42 stack running under that runtime. [PHPUnit guide][phpunit] · [Laravel deployment][laravel-deploy]

**Wasmer/WASIX PHP is promising but unqualified.** Its current documentation explicitly lists PHP and disabled-by-default networking, but the sandbox SDK is alpha and TinyBuilder's fixture has not been tested there. [Wasmer SDK][wasmer-python] · [Wasmer repository][wasmer]

**No-admin AppContainer creation needs TinyBuilder-specific verification.** Microsoft documents `CreateAppContainerProfile` as creating a per-user profile and AppContainer launch as a supported Win32 mechanism, but this research did not execute it under TinyBuilder's targeted standard-user environments. [Launch][win-launch] · [Profile][win-profile] It should therefore be treated as a likely optional hardening layer, not a verified portable prerequisite.

**Embedded binary-size impact is not measured.** Wasmtime's current release and QuickJS assets give useful upstream reference points, but TinyBuilder's final Rust binary size depends strongly on Wasmtime feature selection, LTO, target, runtime assets and whether language interpreters are bundled. Wasmtime exposes feature flags precisely for this kind of tailoring. [Embedding API][wt-api] · [QuickJS releases][quickjs] Any fixed "added MB" claim before compiling the actual evaluator would be speculative.

**Performance is not measured.** No benchmark was executed as part of this research, in accordance with the request. Consequently there is no justified TinyBuilder-specific cold-start, PHP throughput or PHPUnit slowdown claim. Wasmtime's architecture supports JIT/AOT execution, but Phase 3 should collect p50/p95 startup, peak RSS and test-suite duration only after a security-qualified PoC exists. [Embedding API][wt-api]

**Licensing needs an artifact-level redistribution review.** Wasmtime itself is Apache-2.0 and Wasmer is MIT. [Wasmtime license][wt-license] · [Wasmer license][wasmer-license] WordPress Playground's repository identifies GPL-2.0-or-later, so directly redistributing Playground packages inside TinyBuilder requires deliberate license/notice analysis rather than treating PHP.wasm as an implementation detail. [Playground package metadata][wp-package] · [Playground license][wp-license] PHP, Composer dependencies and every bundled native/Wasm library would also need exact notices and license inventory before shipping.

The principal architectural decision made without explicit prior guidance is therefore: **standardize the TinyBuilder evaluator API around capability-restricted Wasm, not around native shell execution; isolate the Wasm runtime in a short-lived worker; and allow PHP to remain a separate experimental backend until real Laravel parity is proved.** That choice maximizes portability and host protection while preserving the project's existing independent benchmark semantics. It also gives TinyBuilder a useful execution substrate immediately for Rust/WASI, constrained Python and JavaScript even if PHP compatibility takes longer. WASI's no-ambient-authority model, Wasmtime's Rust embedding API and TinyBuilder's current native/read-only product boundary all support this direction. [WASI security][wasi] · [Embedding API][wt-api] · [Release contract][release]

The go/no-go result of this research is therefore **GO for a model-free Wasmtime/WASI evaluator PoC; CONDITIONAL GO for PHP.wasm and Wasmer/WASIX compatibility experiments; NO-GO for arbitrary generated PHP execution, native-host fallback, Docker/VM provisioning, or any relaxation of TinyBuilder's current host-protection rule until the measurable security gates above pass.** [PR #23][pr23] · [AGENTS.md][agents]

## Closeout addendum — 2026-11-28

### Repository verification and evidence classes

Direct GitHub verification at closeout: main is still [ce28337552933a671a95d1ad30baa07cfe7cc2b7][merge], the original research baseline. No open PRs were returned before this documentation branch was created. The exact-main workflow query returned six completed successful runs: [Python](https://github.com/MrPunyapal/TinyBuilder/actions/runs/46005037101), [native deterministic](https://github.com/MrPunyapal/TinyBuilder/actions/runs/46005037196), [native rewrite](https://github.com/MrPunyapal/TinyBuilder/actions/runs/46005037207), [native packages](https://github.com/MrPunyapal/TinyBuilder/actions/runs/46005037152), [candidate security](https://github.com/MrPunyapal/TinyBuilder/actions/runs/46005037200), [agent guidance](https://github.com/MrPunyapal/TinyBuilder/actions/runs/46005037231). These six are distinct from the seven integrated PR workflows reported at merge; neither group qualifies a live sandbox. The original report's upstream version/date observations are historical, not freshly revalidated at closeout. The upstream capabilities are documentation-based, not independently executed; ratings, resource budgets and design recommendations are proposals. The historical 157-commit count is not a promotion criterion.

Reviewed [agent guide](../AGENT_GUIDE.md), [project status](../PROJECT_STATUS.md), [release contract](../RELEASE_0_1.md), [contained evaluator](2026-11-27-contained-php-evaluator.md), [qualification checkpoint](2026-11-27-contained-qualification.md), and all seven existing skills. The status snapshot retains stale pre-merge wording; live GitHub supersedes it as evidence, but only the lead maintainer should edit the canonical snapshot under this task's scope.

The checkpoint records the abandoned Windows VM provisioning attempt and explicitly supersedes that approach; rollback/restart remains outside this assignment. The existing adapter is a Docker-in-approved-Linux-guest implementation, with exact image identity, trusted fresh preflight, bounded observation protocol and separate scorer. Keep it as the current qualified-path *design*, not a qualified runtime. Do not remove it or run the existing low-level observe API to bypass its gate. Its legacy host scoring paths were deliberately disabled. The four framework tasks require Laravel 13.42.0 and exact reviewed lock identity; the eight dependency-free tasks have 72 planned observations; together all 12 have 87. The separate route bridge adds nine observations and must not replace the original PHPUnit oracle. Historical private trusted controls do not authorize private candidate transfer. Ordinary CI can run reviewed trusted public controls only.

### Clarifications and stronger fail-closed interpretation

- A same-user child process is **not** a separate OS security boundary. A compromised native Wasmtime worker can retain its account's ambient OS authority even with an empty guest WASI context. The original worker separation and optional hardening proposal reduces ordinary failure impact, not guaranteed escape impact. If the threat model includes runtime compromise, a separately verified outer boundary is mandatory before hostile execution; absence of that boundary means blocked, not fallback to an ordinary host. Platform optionality in the design means the worker can be built/tested model-free without those wrappers, not that hostile execution is safe without them. Existing AGENTS.md and approved-guest policy govern until explicitly revised by the owner.
- Hidden tests mounted read-only are still readable and may be observable to a candidate in the same PHP interpreter. The original report's read-only insertion option is rejected for hidden oracle material. Reuse the existing black-box typed observation bridge: candidate receives only the individual input needed for execution; expected values, hidden test source, scoring and reference repairs stay outside the candidate process and model root. Do not trust self-reported PHPUnit success or guest output as authority. This resolves an ambiguity in the original architecture.
- For disk exhaustion, read-only mounts alone do not impose aggregate byte, inode or metadata budgets; enforce quota or equivalent bounded storage and qualify it. RSS sampling alone is not an enforceable memory ceiling. Record what the OS actually limits (e.g., commit versus RSS), account for host compilation, caches, all guest instances and processes, and block if whole-worker containment cannot be established. Reject untrusted precompiled native artifacts; use verified runtime artifacts or validated Wasm bytes. Ensure staging and cleanup do not follow hostile filesystem links. Limits above are proposed, not measurements.
- The original claim that execution is the gating problem refers to *semantic evaluation*, not proof that retrieval and multi-file reasoning are solved. Keep inference-only research and release clean-host work independent. No new model evaluation was run. No local checkout or uncommitted work was inspected.
- Windows AppContainer profile creation, macOS entitlements/signing and Linux namespace policy are still unqualified. Do not provision the personal Windows PC or change kernel, security, or machine-wide settings. CI results, a passing security probe suite and an advisory scan are necessary evidence, never a proof of impossibility of escape.
- Wasmtime upstream licensing shorthand in the original report does not replace exact artifact review, including LLVM exception notices where applicable. GPL package-level terms and compatibility require review before bundling. Wasmer's documented historical [filesystem sandbox advisory](https://github.com/wasmerio/wasmer/security/advisories/GHSA-4mq4-7rw3-vm5j) is a further reason to qualify exact configurations of both PHP lanes.
- Native 0.1 stays read-only; no evaluator worker, bundled interpreter or dependencies should enter that product package. The diagram's CLI-to-supervisor arrow is conceptual future lab integration; implement an independent lab entry point first.

No implementation files, guidelines, model weights, infrastructure, generated-code execution or release artifacts are changed by this closeout. No new security experiments were run. See [executive summary](2026-11-28-phase-3-sandbox-summary.md) and [roadmap](2026-11-28-phase-3-sandbox-roadmap.md) for recommended sequencing, owners, explicit approval gates and skill review.

## Source links

The following ordinary Markdown references preserve the original report's cited sources without ChatGPT-specific citation tokens. Repository evidence uses the original baseline where possible; upstream documentation may evolve.

[merge]: https://github.com/MrPunyapal/TinyBuilder/commit/ce28337552933a671a95d1ad30baa07cfe7cc2b7
[pr23]: https://github.com/MrPunyapal/TinyBuilder/pull/23
[repo]: https://github.com/MrPunyapal/TinyBuilder
[agents]: https://github.com/MrPunyapal/TinyBuilder/blob/main/AGENTS.md
[release]: https://github.com/MrPunyapal/TinyBuilder/blob/main/docs/RELEASE_0_1.md
[release-audit]: https://github.com/MrPunyapal/TinyBuilder/blob/main/docs/research/2026-11-26-release-audit.md
[wt-security]: https://docs.wasmtime.dev/security.html
[wasi]: https://wasi.dev/security
[wt-bugs]: https://docs.wasmtime.dev/security-what-is-considered-a-security-vulnerability.html
[wt-advisories]: https://github.com/bytecodealliance/wasmtime/security/advisories
[rustsec]: https://rustsec.org/advisories/RUSTSEC-2026-0587
[wt-api]: https://docs.wasmtime.dev/api/wasmtime/
[wt-ctx-src]: https://docs.wasmtime.dev/api/src/wasmtime_wasi/ctx.rs.html
[wt-ctx]: https://docs.wasmtime.dev/api/wasmtime_wasi/struct.WasiCtxBuilder.html
[wt-net]: https://docs.wasmtime.dev/api/wasmtime_wasi/p2/bindings/sync/sockets/network/struct.Network.html
[wt-capi]: https://docs.wasmtime.dev/c-api/wasi_8h_source.html
[wt-limiter]: https://docs.wasmtime.dev/api/wasmtime/trait.ResourceLimiter.html
[wt-config]: https://docs.wasmtime.dev/api/wasmtime/struct.Config.html
[wt-store]: https://docs.wasmtime.dev/api/wasmtime/struct.Store.html
[wt-license]: https://github.com/bytecodealliance/wasmtime/blob/main/LICENSE
[wt-release-policy]: https://docs.wasmtime.dev/stability-release.html
[wt-releases]: https://github.com/bytecodealliance/wasmtime/releases?after=list
[php-packages]: https://wordpress.github.io/wordpress-playground/developers/architecture/php-wasm-packages/
[php-overview]: https://wordpress.github.io/wordpress-playground/gu/developers/architecture/wasm-php-overview/
[php-compiling]: https://wordpress.github.io/wordpress-playground/developers/architecture/wasm-php-compiling/
[php-node]: https://wordpress.github.io/wordpress-playground/developers/local-development/php-wasm-node/
[php-build]: https://github.com/WordPress/wordpress-playground/blob/trunk/packages/php-wasm/compile/php/Dockerfile
[phpunit]: https://wordpress.github.io/wordpress-playground/ja/guides/phpunit-testing/
[wp-support]: https://wordpress.github.io/wordpress-playground/bn/developers/architecture/wordpress/
[laravel-deploy]: https://laravel.com/framework/docs/13.x/deployment
[laravel-test]: https://github.com/laravel/docs/blob/13.x/testing.md
[wasmer-python]: https://docs.wasmer.io/runtime/python/
[wasix]: https://docs.wasmer.io/runtime/wasix/
[wasmer]: https://github.com/wasmerio/wasmer
[wasmer-docs]: https://docs.wasmer.io/
[wasmer-license]: https://github.com/wasmerio/wasmer/blob/main/LICENSE
[python]: https://docs.python.org/3/library/intro.html?highlight=socket
[python-thread]: https://docs.python.org/3.15/library/threading.html
[quickjs]: https://github.com/quickjs-ng/quickjs/releases
[quickjs-wasi]: https://github.com/vercel-labs/quickjs-wasi/blob/main/README.md
[rust-targets]: https://doc.rust-lang.org/rustc/platform-support.html
[rust-p2]: https://doc.rust-lang.org/rustc/platform-support/wasm32-wasip2.html
[wp-package]: https://github.com/WordPress/wordpress-playground/blob/trunk/package.json
[wp-license]: https://github.com/WordPress/wordpress-playground/blob/trunk/LICENSE
[win-launch]: https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer
[win-profile]: https://learn.microsoft.com/en-us/windows/win32/api/userenv/nf-userenv-createappcontainerprofile
[win-limits]: https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_limit_information
[win-jobs]: https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
[apple-sandbox]: https://developer.apple.com/documentation/security/app-sandbox/
[apple-data]: https://developer.apple.com/documentation/security/protecting-user-data-with-app-sandbox
[apple-forum1]: https://developer.apple.com/forums/thread/661939
[apple-forum2]: https://developer.apple.com/forums/thread/793310
[apple-process]: https://developer.apple.com/forums/topics/app-and-system-services/processes-and-concurrency
[apple-tag]: https://developer.apple.com/forums/tags/app-sandbox
[bwrap]: https://github.com/containers/bubblewrap/blob/main/NEWS.md
[nsjail]: https://github.com/google/nsjail/blob/master/README.md?plain=1
[wamr]: https://github.com/wasm-micro-runtime/wasm-micro-runtime/blob/main/README.md
[wamr-build]: https://github.com/wasm-micro-runtime/wasm-micro-runtime/blob/main/doc/build_wamr.md
[wamr-security]: https://github.com/wasm-micro-runtime/wasm-micro-runtime/security
