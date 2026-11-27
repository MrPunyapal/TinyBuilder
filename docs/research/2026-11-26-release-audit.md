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

## Third continuation — 2026-11-26

- Verified exact baseline `4f04c503cbbdfc3e828192a9edb73566150925b1` PR #15: all five PR workflows passed ([Rust](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45710179195), [native](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45710179228), [Python](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45710179362), [archive evidence](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45710179184), [package](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45710179185)). [Push artifacts](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45710172114): outer CI artifact bytes Windows 10318784, macOS 5666624, Linux 8496423; digests recorded by GitHub; not independently unpacked here. No review threads. No model inference established.
- New independent security review: b6500 affected by [GHSA-96jg-mvhq-q7q7](https://github.com/ggml-org/llama.cpp/security/advisories/GHSA-96jg-mvhq-q7q7) (affected < b7437, patch b7824) and [GHSA-3p4r-fq3f-q74v](https://github.com/ggml-org/llama.cpp/security/advisories/GHSA-3p4r-fq3f-q74v) (affected <= b8145, patch >= b8146). Do not load models with old packages. [44a3efd](https://github.com/MrPunyapal/TinyBuilder/commit/44a3efd545419acdb1a126d9ac1329bf20bc68c7) rejects b6500 at new Rust inference startup, adds post-response listener checks, preserves model-free mode. This is a stopgap, not an atomic transport fix or public release.
- [e7c54ca](https://github.com/MrPunyapal/TinyBuilder/commit/e7c54ca81c0184f06de6b9c727ab5e5418466d3f) adds fail-closed OSV lockfile audit and model-free pinned b12359 archive inspection on three platforms. Release API confirmed b12359 asset digests and target commit metadata b1b770d90d94cad9e9ea5b993bdbc383a522fb28. CI queued; no advisory clearance or upgraded package claimed. Runtime staging still b6500; port to the inspected ZIP/tar layout after successful input evidence. Audit exact crate notices and linked native libraries, not just lockfile names. Same-user malicious process and check/connect race remain unresolved.
- Model research kept independent: [PR #16](https://github.com/MrPunyapal/TinyBuilder/pull/16) on research/specialized-model, head daf6cc8fa5104377ebb103208c56bf67f1b3b. [Candidate model research and pilot](https://github.com/MrPunyapal/TinyBuilder/blob/research/specialized-model/docs/research/2026-11-26-specialized-model.md), including original data generation, disjoint task families and model-free CI. No weights, training or paid compute. Real model 10/10 and clean-machine offline gates remain blocked. PR #14 and main unchanged.

## Fourth continuation — 2026-11-26

- [Security evidence run](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45796775203): Windows, macOS and Linux b12359 archives verified against pinned official SHA-256, exact member inventories captured. OSV identified anyhow 1.0.98 (RUSTSEC-2026-0190) and rand 0.8.5 (RUSTSEC-2026-0097, GHSA-cq8v-f236-94qc; aliases of same issue). [a0c4ae3](https://github.com/MrPunyapal/TinyBuilder/commit/a0c4ae3c4f8cc6f5c04c89d3839cefb128c082d9) pins patched anyhow 1.0.103 and rand 0.8.6 with registry-index checksums, unchanged active dependency edges; minimum-Rust locked builds still require fresh CI. [Security evidence](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45797085981) at a0c4ae3 passed; no known OSV matches at that point. This is not full vulnerability/redistribution clearance.
- [5082282](https://github.com/MrPunyapal/TinyBuilder/commit/5082282e9c8b0ce0bad7681692164e9e256e46e5) and [8f7a82a](https://github.com/MrPunyapal/TinyBuilder/commit/8f7a82a57c2b77751310ed91250b564afcc1fb51) migrate native packaging to b12359 (Windows ZIP, macOS/Linux tar.gz). Observed official Unix archives have versioned library symlink chains; stage verified aliases as ordinary byte-identical files, reject traversal, cycles, hardlinks, unresolved/nonselected targets and unexpected prefixes, exclude unrelated executable tools. Include upstream MIT, jsonhpp and httplib notice blobs from pinned source plus Windows OpenMP notice. Complete redistribution and native loader audit still required. New packaging tests added; CI not yet verified. Older b6500 packages must not load GGUF.
- [b3b889c](https://github.com/MrPunyapal/TinyBuilder/commit/b3b889cb8e3e728c3be74a4f7a1141f6bf198771) adds actual packaged-CLI qualification with trusted CI archive identity, exact unpacked inventory, fresh randomized fixtures, strict output and real read-event checks, denied-write event, before/after model and package hashes and sanitized report. Original ten-trial task/oracle unchanged. Prompt no longer mandates citations that conflict with explicit exact-answer formatting; no result parsing repair or retries. Model-free regression tests only. Real inference remains NOT RUN.
- [PR #16](https://github.com/MrPunyapal/TinyBuilder/pull/16) at daf6cc8 passed [model pilot](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45796592476), [Python](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45796592356) and [native](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45796592336) PR CI. Synthetic public pilot 60 train/20 dev/40 eval, disjoint template families; not training-quality certification or held-out secret evaluation. No training, weight download or paid compute.

## Fifth continuation — 2026-11-26

- [2a5c248](https://github.com/MrPunyapal/TinyBuilder/commit/2a5c248fc81b9ca2d18d9f9b47c5132151fd7d58) implements the same-connection authenticated loopback transport, replacing the preflight-check-then-connect pattern for bearer credentials and project context. Linux procfs, Windows established TCP owner table and macOS lsof check the exact reversed client/server tuple before transmitting. HTTP framing is bounded, requires explicit content length and JSON on success, and rejects redirects, chunked encoding, ambiguous headers and compression. Added ownership and framing regression tests, including a foreign listener test requiring zero request bytes. Unauthenticated health and deliberately invalid-key probes carry no real secret or project data. This mitigates the original listener replacement race but is not a cryptographic peer identity or protection against malicious same-user/privileged process manipulation. Actual b12359 inference compatibility remains untested; unsupported framing fails closed. Transport failures are categorized as startup/transport failures, not intelligence failures.
- Exact-head CI for 2a5c248: archive evidence passed; remaining jobs queued/in progress at inspection. Earlier runs superseded/cancelled; do not use them as acceptance. No upgraded package claimed before completed exact-head package CI. Continue with actual clean-host and permissively licensed GGUF qualification per [acceptance instructions](../CLEAN_MACHINE_ACCEPTANCE.md). No weights, training, paid compute, merge or publication.

## Windows packaged acceptance — 2026-11-26

- PR #15 baseline `97a4a7a03479a6f5890475813da916dc2fe9c006` passed
  [native checks](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45798269138),
  [Rust](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45798269239),
  [Python](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45798268911),
  [archive evidence](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45798269071),
  [security evidence](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45798269076)
  and [packaging](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45798257192).
  The downloaded Windows archive verified at 21,932,992 bytes and SHA-256
  `7f5c60576f59f036362e4d242fc5ce5ebe20f748289fffb3ae9a7274e7a52c38`.
  Local Windows packaging also succeeded at that source. The hosted package
  failed the first packaged qualification trial in the transport/startup
  category after 129 seconds, with zero verified reads. The evaluator stopped
  with nine trials unattempted. Separately, the package reached authenticated
  readiness and cleaned up on both normal and forced exit.
- Paired diagnostics on one fresh fixture per model separated tool selection
  from answering. With the pinned Apache-2.0 Qwen2.5-Coder 1.5B Q4_K_M, the
  original agent spent eight rounds without a verified read. The 3B research
  model read the file and returned both facts in the wrong format. Both
  models answered exactly in the two direct controls and the two split-stage
  arms, with genuine model-selected reads in both split-stage arms. The
  controls are diagnostics. PR #16's two synthetic-pilot tests passed locally
  and its model-free CI passed. Existing weights are sufficient for the
  tested release task with the split-stage engine. Defer fine-tuning and use
  fresh held-out codebase tasks for broader capability questions.
- `0d39e39c820f5a958a73266a638d542a95cd9446` uses the existing split-stage
  reader for explicit strict file reads in the product CLI. The first request
  lets the model select a real project file. Its validated tool action must
  succeed before a bounded answer-only request receives the file evidence.
  Native and general multi-tool operation retain their existing path. The
  runtime now explicitly uses b12359's offline mode and disables its built-in
  agent and web MCP proxy. Local locked Rust tests passed 30/30, acceptance
  tests 35/35, and Python tests 232 passed with one skipped. Compile check
  and doctor succeeded.
- The independently rebuilt Windows package at that code commit was
  21,887,703 bytes, SHA-256
  `15dac13cae728a43c349900b92fe45f889083c8751c624c395783d55ce213115`.
  Its b12359 CPU archive SHA-256 was
  `837c1655e87df3b66989f4be33a792a1399c785bf259038dc75c900096683e69`
  and its bound runtime manifest SHA-256 was
  `14e4d644a3ea6a082171bbe707bb705e3bfee1e01988943741a880fa89242693`.
  The unchanged packaged gate passed **10/10** on Windows 11 x64 with the
  preselected 1.5B artifact (1,117,320,768 bytes, SHA-256
  `cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046`).
  All ten trials verified real reads and returned both facts exactly. All
  fixture, model and package hashes were unchanged, with zero write attempts.
  Total per-trial latency was 6.33–10.01 s, median 8.88 s, including fresh
  process startup. This evidence applies to the recorded local build and
  installed host configuration.
- On the same i7-12700H Windows development PC, the fixed package reached
  authenticated readiness in 2.41 s and 4.88 s. The sum of the app and
  server startup peak working sets was about 2.45 GiB. Both an explicit quit
  and a forced parent exit removed the exact child and its loopback listener.
  Owned/foreign established-socket regression tests passed, including zero
  bytes reaching a foreign socket. A separate direct CPU streaming control
  returned HTTP 401/401/200 for absent/invalid/valid credentials, produced
  26.2–26.8 tokens/s, and emitted its first text after 465 ms on the first
  request and 44–46 ms on repeated requests. The product's buffered HTTP path
  was used for qualification. Model-free first launch, read/search/inspect,
  write-flag denial and removal of a disposable copy preserved the fixture
  with only System32 on PATH.
- Public release stays on hold pending clean-machine evidence on every
  target, exact hosted candidate acceptance, and independent security,
  signing and redistribution review. Windows host networking stayed enabled
  during the developer checks. PR #14 was preserved separately. No new
  weights, training, publication or merges.

## Post-merge maintainer review

See [maintainer handoff](2026-11-26-maintainer-handoff.md) and [updated model research](2026-11-26-specialized-model.md). All three main post-merge workflows passed at d4ea614; native packaging and security evidence must be run against the actual new candidate commit. PR #14 is superseded by selective lab-only work; PR #16 pilot stays on its research branch. No training or release approval.

## Exact-main acceptance after PR #17 — 2026-11-26

- PR #17 at `08346b0aeafe3c5b21c9fa044ff480ab187f2269` passed 16
  checks with one skipped and merged as
  `04a2bb0571a5c67288e6fb018404d27abb34efff`. [Exact-main packages](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45822555193),
  [security evidence](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45822555110),
  [native checks](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45822554990)
  and [Python checks](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45822555330)
  succeeded. All three original archives were downloaded and hashed.
- Windows x64 ZIP, 21,950,331 bytes:
  `afc94f3ae043888847dbd77f89fd52cc4cd892d121e5ae96574afc40327192eb`.
  macOS ARM64 tar.gz, 27,937,941 bytes:
  `7cc5e1013d7c8d3664b54f1c34a83e01e7dfc65909f890882abaa380f8606fd1`.
  Linux x64 tar.gz, 31,005,245 bytes:
  `1413da65e1ff3884b9329d74909b686a8579ada9a47d6c0179f395037efb40d4`.
- The exact Windows ZIP passed the unchanged **10/10** read gate with
  Apache-2.0 Qwen2.5-Coder 1.5B Q4_K_M
  (`cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046`).
  All reads were genuine, both facts exact, and fixture, archive contents
  and model unchanged. Authenticated b12359 reached readiness in
  3.29–3.69 s, used about 2.44 GiB runtime peak working set, and its
  loopback listener and child exited after both normal and forced app exit.
  The packaged runtime uses offline mode, but the development host was
  elevated and had two active adapters. It supplies developer-host evidence
  only. No suitable clean Windows guest or macOS host was available.
- Exact Windows notice checks verified 206 crate notice files across 111
  inventoried crate records and four runtime notices, including LLVM OpenMP.
  No declared notice files were missing. macOS and Linux verified 200 and
  204 crate notice files respectively, with no missing declared notice files.
  The exact-main OSV scan covered 129
  lock entries with zero known matches. Independent redistribution and
  signing review remain pending.
- The Linux x64 archive failed to launch in the existing Ubuntu 22.04 WSL
  guest. The application requires `GLIBC_2.39` and the guest has 2.35. The packaged b12359 runtime itself could print its version in that guest.
  Decide and document the supported Linux baseline before publication or
  build and test the package against an older compatible toolchain. WSL
  does not stand in for a clean Linux host. This compatibility failure
  applies to the exact archive above.

## Rust patch-lab experiments — 2026-11-26

These proposal diagnostics are separate from the unchanged product read gate.
The baseline PR #18 head `696e6a6e37ffbdd5a1ef5c02ee50fe9b52539224`
passed 19 GitHub checks with one skipped. Windows offline locked Rust tests
passed 36/36 after adding the file and line selection controls. Tests cover
denied, stale, ambiguous, overlapping and hard-linked replacements, traversal
and rejection of a proposed file outside the selected evidence.

- On the original lab binary, the existing 1.5B returned 2/3 exact
  proposals (Python and Rust). The local 3B research-only control returned
  0/3, with wrong Python and Rust proposals and an invalid PHP proposal.
  After exact-copy prompt changes the 1.5B remained at 2/3, with a no-op
  PHP proposal. The evaluator retained all failures and applied nothing.
- On the explicitly disposable Laravel baseline
  `b8f1471d477b127cc62674e9f37110e2dc80d8c4`, independently fixed
  PHPUnit controls scored untouched suite 0, broken endpoint 1, correct
  reference repair 0 and incorrect presence-only email validation 1.
  The original general-context 1.5B proposal and the single-file retry
  both failed exact replacement matching before approval, with no file
  change. The older Python evaluator also stopped once at the reference
  control. An isolated rerun of that same reference and route listing
  passed, so that initial failure remains recorded separately.
- A selected-line 1.5B trial produced a reviewable, safe PHP diff but
  returned HTTP 422 for every request. The evaluator approved it on the
  disposable worktree only to test behavior independently. PHP lint and
  route registration passed, PHPUnit exited 1 and the project scope and
  model were preserved. A second selected-line trial on a standalone
  PHP boundary helper produced the wrong boolean expression and was
  explicitly declined. That source remained unchanged.
  The existing research-license 3B was also tested with a selected line.
  It explicitly returned HTTP 200 for every request. PHP lint and route
  registration passed, PHPUnit exited 1 and scope was preserved. No
  model repair passed across these four Laravel trials.
- The selected-line experiment removes model transcription of the old
  bytes while retaining exact uniqueness, snapshot and human approval
  checks. Both tested models still failed semantic Laravel repair.
  Use varied held-out Laravel repairs with the same independent controls
  before broadening editing or considering any training.

## Laravel v1 controlled pilot — 2026-11-27

See the [Laravel benchmark protocol and dated results](../LARAVEL_BENCHMARK_V1.md). Both local models passed 8/8 tightly bounded trials after independent PHPUnit controls. Four-arm evidence and previous failed open-ended repairs remain separate.
