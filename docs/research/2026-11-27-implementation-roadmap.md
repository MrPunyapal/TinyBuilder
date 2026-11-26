# TinyBuilder — proposed implementation roadmap

Date: 2026-11-27  
Status: Draft engineering plan for maintainer review; no implementation or training approval.  
Companion documents: [full research](2026-11-27-deep-research.md) · [executive summary](2026-11-27-research-summary.md).

## Operating rules and evidence

The native Rust 0.1 release, its unchanged read-only qualification oracle and clean-machine acceptance/release decisions are independent of this research. Follow [AGENTS.md](https://github.com/MrPunyapal/TinyBuilder/blob/main/AGENTS.md), [release requirements](https://github.com/MrPunyapal/TinyBuilder/blob/main/docs/RELEASE_0_1.md) and [release audit](2026-11-26-release-audit.md). Do not enable research mutation functionality in the production CLI. Python and mutation examples are reference/lab only.

Another local Codex agent is implementing research changes. Before each milestone, inspect the exact current main and relevant research heads, worktree status and changed files; reconcile with the existing agent's work rather than duplicating or overwriting it. The research report examined [PR #18](https://github.com/MrPunyapal/TinyBuilder/pull/18) at 8f1c45e2233d93ea0958449cb53728a4085ea071 and [PR #20](https://github.com/MrPunyapal/TinyBuilder/pull/20) at c7e6646288ec1a964c917366eb298b70036d7a5d. These are historical anchors, not assertions about their current state. Treat the lab as a source of evidence, not a new product foundation by default.

**Classification:** historical repository facts and reported experiments are in the full report. Every milestone, numerical target and go/no-go threshold in this document is a proposed decision, not an achieved result. Set final product thresholds using baseline and human-reviewed task difficulty *before* running final held-out evaluations; do not change the scoring oracle to improve outcomes.

## Dependency map

~~~text
M0 Reconcile work / freeze release boundaries
  ├─ M1 Independent benchmark + protocol fixtures
  │    ├─ M2 Retrieval + baseline model measurements
  │    └─ M3 Safe patches + adaptive verification
  │         └─ M4 Laravel plugin
  │              └─ M5 Optional knowledge/MCP + hostile-content tests
  ├──────────────── M6 Qualification / resource and quality decisions
  │                   └─ M7 Optional specialization, only if justified
  └──────────────── M8 TUI and distribution, after qualification
~~~

M2 and proposal-only parts of M3 may progress in parallel after M1's interfaces are agreed, but real execution needs containment review and explicit consent. M4 may start with pure detection fixtures; no external tools are invoked until its host capability checks exist. M6 runs throughout development; its exit gate precedes release-like UX. M7 is not a prerequisite if the unmodified model already meets agreed goals.

## Milestones and measurable gates

| Priority / milestone | Proposed deliverables | Dependencies | Proposed acceptance evidence |
|---|---|---|---|
| P0 / M0 — reconcile | Inventory actual Rust modules, research branches, qualification tests and concurrent work; identify gaps and ownership; preserve all failed evidence. | None | Exact SHAs and test commands documented; plan identifies reused vs new modules; no change to release CLI or oracle; no overlapping modifications without coordination. |
| P0 / M1 — benchmark | Task and result schema, isolated worktree lifecycle, public/hidden verifier separation, fake providers, failure taxonomy. Start with 30–50 curated executable tasks; target 60–100 before final qualification. | M0 | Every task reproduces a failing target check at the base and a passing check after a known valid solution; regression checks pass on valid solution; at least three distinct repositories and repository-disjoint evaluation splits; alternative valid patches accepted; no hidden tests or gold edits in model context; deterministic model-free CI passes. |
| P1 / M2 — retrieval | File inventory, lexical baseline, PHP Tree-sitter symbols, Composer/autoload graph hints, budgeted map, optional LSP interface, evidence revisions. | M1 manifest and snapshots | All fixture exclusions honored; identical inputs give identical ranking and map; no budget overflow; stale files invalidate evidence; supplied vs retrieved evidence recorded for each task; report evidence recall, tokens, time and task success under matched conditions. |
| P1 / M3 — safety + adaptive coding | Typed proposals and exact approvals, patch engine, bounded state, protocol qualification, verifier feedback, cancellable command runner in a contained environment. | M1; M2 evidence API; containment review before exec | Zero unauthorized executed actions in adversarial suite; 100% rejection of malformed/fenced/mixed prose, duplicate keys, unknown actions, stale revisions, traversal/symlink escapes and replay cases in deterministic fixtures; atomic rollback and cleanup verified; fake-model success, retry, denial and budget exhaustion cases pass; no production mutation wiring. |
| P1 / M4 — Laravel plugin | Generic plugin interface; package/version detection; Laravel graph edges and test/tool discovery; optional Boost adapter. | M2–M3 interfaces | Generic core has no Laravel-specific dependency; fixtures cover missing/installed Boost, Pest/PHPUnit, Pint, PHPStan/Larastan and Composer lock variations; command proposals pass through policy; absent tools cause explicit degradation rather than failure; real Laravel hidden tests execute only in approved isolated evaluation. |
| P2 / M5 — knowledge and trust | Local/versioned docs, optional search provider, MCP trust and provenance metadata, ephemeral memory. | M3–M4 policy and plugin API | Offline tasks remain usable; fake provider exercises timeout, malformed response, rate limit, stale version, denied network and malicious text; no unauthorized outbound data or writes; verify no remote content or session transcripts enter SQLite or telemetry; explicit preferences only. |
| P0 ongoing / M6 — qualify | Run controlled model/quantization/context/offload/protocol/retrieval ablations with existing or explicitly approved local models. | M1–M5 as relevant to each arm | Publish all attempts, raw aggregate metrics, failures, manifests and confidence intervals; compare adaptive agent against simple localization/repair/validation control; select a Pareto-efficient model only after satisfying predeclared correctness, security, RAM/VRAM and latency goals. |
| P2 conditional / M7 — specialize | Verified dataset pipeline, license manifest, base vs protocol SFT vs Laravel/repair adapters; optional QLoRA experiment. | M6 identifies model-specific weakness; explicit training approval | Every exported trajectory has executable and provenance validation; no held-out repository leakage; measured peak training memory/time; reproducible adapter and evaluation manifests; improvement on frozen held-out tasks with no unacceptable general-code or safety regression. |
| P3 / M8 — thin UI/distribution | Ratatui/Crossterm TUI and equivalent headless interface over existing events; explicit model management, CPU fallback, signed/checksummed platform builds. | M3 policy; M6 qualification; M7 optional | Same task events/verification outcomes in headless and TUI fake-provider tests; exact approval details visible; cancellation restores terminal and cleans disposable workspace; clean Windows x64, macOS ARM64, Linux x64 acceptance evidence; no implicit download, mandatory subscription or runtime developer-tool installation. |

## Benchmark protocol (M1/M6)

### Task manifest and validation

Each task must record base commit, immutable fixture/environment versions, task statement, allowed capabilities, setup commands, public verifier, independent hidden verifier, expected security outcome, resource/turn limits, repository license and split assignment. Keep hidden tests outside the agent-visible repository and apply them from the independent evaluator. A failed setup or missing tool is an environment failure, not a model success or a silently removed row. Re-run a known valid solution and the unmodified base to establish the test oracle. Preserve narrow PR #20 fixtures as smoke tests only; add actual multi-file changes and unfamiliar-repository tasks with no selected-line hint.

Use the report's task categories: generation, diagnosis, features, multi-file refactoring/repair, TDD, unknown codebases, Eloquent/Blade/Livewire/queues, tool use, docs and security/approval. Ensure every category is represented; report counts and pass rates by category. Split by repository lineage to avoid sibling-fork leakage. Start with the existing baseline and no newly downloaded weights.

### Experiment matrix

| Dimension | Proposed arms |
|---|---|
| Model | Existing Qwen2.5-Coder-1.5B; after approval, Granite 4.2-3B, Qwen3.5-4B, Phi-4-mini, 0.5B control, optional 7B ceiling. |
| Retrieval | Supplied relevant evidence (diagnostic control), full-file baseline, lexical, lexical+AST, +LSP, optional embeddings only after earlier arms. |
| Protocol | Qualified native calls; strict opt-in local JSON envelope; constrained schema where supported. Prompt-only invalid responses can be scored offline; never execute arbitrary extracted prose. |
| Controller | Simple localization/repair/validate baseline vs adaptive budgeted retrieval and feedback. |
| Context | 4K/8K/16K, then 32K only if resource budget permits; fixed vs dynamic budgets. |
| Runtime | Pinned llama.cpp CPU-only, GPU-offload and hybrid; matched quantization where possible; Q4 baseline and higher-precision control if available. |
| Verification | Proposal-only, targeted, targeted + static analysis, bounded repair loop; independent hidden scoring always remains enabled. |
| Knowledge | Offline, optional Boost, optional web/MCP (separate consent and security testing). |

Change one variable at a time first; use paired tasks and identical environment constraints; preserve seeds and all runs (at least three repeated trials for stochastic configurations if feasible). Track exact model revision/GGUF checksum, quantization, template, runtime commit and settings, OS, hardware, context, seed, turn count, and TinyBuilder commit. The target PC is Windows 11 Home, 12th-generation Intel i7, 16 GB RAM, NVIDIA RTX 3050 4 GB VRAM. Those are supplied specs, not measurements.

### Metrics and decision rules

- Functional pass: all task-specific hidden checks and required regression tests pass, no disallowed changes/actions. Count exact patch matches separately as diagnostics only. Report full denominator and excluded/blocked cases explicitly.
- Failure attribution: reasoning/localization, retrieval ranking, protocol parse vs semantic tool choice, edit freshness/application, verifier interpretation, permission policy, environment/external tool. Use supplied-vs-retrieved evidence to distinguish localization from synthesis.
- Cost: p50/p95 task wall time and first-token latency where available, prompt/output tokens, tool counts, peak process-tree RAM and VRAM, disk I/O, throughput, context. Sample GPU power and integrate over elapsed time where available; distinguish GPU-only energy from whole-system energy; mark unavailable CPU energy as unmeasured.
- Safety: zero unauthorized executed actions in all adversarial and benchmark trials is a hard proposed gate, not a negotiable score. Also report denied attempts and appropriate permission escalations separately.
- Resource: avoid OOM and sustained paging on target hardware; propose initial peak combined process-tree RSS target ≤ 8 GB and peak GPU allocated memory ≤ 3.5 GB on the 4 GB card where measurable, leaving room for the OS; these are provisional budgets, not claims. Record CPU-only fallback separately. Set latency targets after measuring the first baseline, then freeze them before final holdout runs.
- Quality: report confidence intervals and paired differences. Predeclare minimum functional pass and acceptable regressions with maintainer approval before holdout; do not fabricate an absolute pass threshold before task difficulty is established. Choose the smallest configuration satisfying the agreed gate. Do not promote an adapter or an embedding system solely because one benchmark point improved.

## Safety and privacy implementation notes (M3/M5)

Worktrees protect the primary checkout but do not isolate processes from the host. Require OS/container/VM containment where feasible for untrusted execution, sanitized environment and credential-free disposable dependencies; refuse or request separate explicit authorization when real containment is unavailable. Handle Windows reparse points, Unix symlinks, race conditions, path normalization, timeouts, output limits and child-process termination. Bind approval to action, normalized target, argv, working directory, risk and snapshot revision; invalidate on changes. Commands may execute project-controlled code even with exact argv, so the verifier itself needs the execution boundary.

Treat README, docs, MCP descriptions/results and skills as untrusted evidence. Network and local file reads do not imply permission to send private data externally. Re-evaluate each invocation; no disk persistence of web/MCP output or transcripts. Use session-bounded in-memory provenance and exact source windows. Use sanitized aggregate measurements or explicitly authorized synthetic research fixtures, not private user session transcripts, for training.

## Training go/no-go (M7)

1. No training before a documented, reproducible baseline and failure attribution. Fix retrieval/protocol bugs first. Do not download models or start paid compute without approval.
2. Build data from owned/permissive sources, independently reproduced task failures and verified repairs; track source revision, license, teacher terms, transformation history and split. Keep only successful and useful failed→recovered trajectories, plus clear negative examples; deduplicate by repository lineage and patch semantics.
3. Start with the existing 1.5B code base and compare untouched vs protocol SFT vs Laravel/verified repair SFT. Use short sequence lengths, low-rank adapters and gradient accumulation/checkpointing; record actual resource use. [QLoRA paper](https://arxiv.org/abs/2305.14314), [PEFT](https://huggingface.co/docs/peft/main/developer_guides/quantization), [Unsloth](https://github.com/unslothai/unsloth/) and [Soup](https://github.com/paulbrett/soup) are experiment candidates, not guaranteed fits. Validate Soup configuration against installed schema; keep it outside inference runtime.
4. If local training cannot fit safely, assess legitimate free [Colab](https://research.google.com/colaboratory/faq.html) or [Kaggle](https://www.kaggle.com/docs/notebooks) availability only with approval and data/license/privacy checks; no guaranteed quotas. Preserve resumable checkpoints.
5. Promote only if the held-out improvement meets predeclared margin with acceptable confidence and regression bounds. Continued PHP pretraining, licensed distillation, routing, QAT/pruning and execution-reward RL are conditional future experiments. Reject from-scratch model training on this hardware.

## Local Codex handoff and sequencing

Use the full report's seven implementation prompts as starting points, with current native release constraints taking precedence. Run one small, reviewable change at a time on the existing experimental track after reconciling concurrent work. Proposed order: benchmark harness → repository intelligence → safe patch/permission kernel → protocol qualification → adaptive controller → Laravel plugin → optional docs/MCP → live qualification → conditional training → thin TUI. Each change should include deterministic fixture tests and a short research evidence note (new findings rather than rewriting old evidence); report exact commands, results, failed cases, changed files and commit SHA. Do not claim success from a fake-model or exact-match smoke test.

## Sources for implementation choices

- Repository: [AGENTS.md](https://github.com/MrPunyapal/TinyBuilder/blob/main/AGENTS.md), [research vision](https://github.com/MrPunyapal/TinyBuilder/blob/research/workflow-slm-lab/docs/VISION.md), [PR #18](https://github.com/MrPunyapal/TinyBuilder/pull/18), [PR #20](https://github.com/MrPunyapal/TinyBuilder/pull/20).
- Retrieval/harness: [Aider repo map](https://github.com/Aider-AI/aider/blob/main/aider/repomap.py), [Tree-sitter](https://tree-sitter.github.io/tree-sitter/), [LSP](https://microsoft.github.io/language-server-protocol/), [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent), [Agentless](https://arxiv.org/abs/2407.01489).
- Evaluation/data: [SWE-bench](https://github.com/SWE-bench/SWE-bench), [SWE-smith](https://github.com/SWE-bench/SWE-smith), [SWE-Master](https://github.com/RUCAIBox/SWE-Master), [CodeRL](https://arxiv.org/abs/2207.01780).
- Runtime: [llama.cpp](https://github.com/ggml-org/llama.cpp), [memory guidance](https://github.com/ggml-org/llama.cpp/blob/master/docs/multi-gpu.md), [build options](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md).
- Laravel: [Boost](https://github.com/laravel/boost), [testing](https://laravel.com/framework/docs/13.x/testing), [Pint](https://laravel.com/framework/docs/pint), [PHPStan](https://phpstan.org/).
- Integration/UI: [MCP skills security guidance](https://skills.extensions.modelcontextprotocol.io/specification/beta/skills), [SearXNG](https://github.com/searxng/searxng) (separate optional service; AGPL license), [Ratatui](https://ratatui.rs/), [Tauri](https://v2.tauri.app/start/).

## Release and review boundary

The full research report is archival evidence with acknowledged incomplete research-tree access and no live model measurements. This roadmap is a proposal, not a replacement for the release requirements, an approved model recommendation, a claim of achieved thresholds or an instruction to merge this documentation PR. Keep failures, open questions and unsuccessful experiments visible; revise the future plan based on measured evidence, not marketing targets.
