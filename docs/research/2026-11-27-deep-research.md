# TinyBuilder Deep Research Report

> Research date: 2026-11-27. Archival edition: the report's substantive text, examples, unsuccessful approaches, limitations and recommendations are preserved below; ChatGPT citation markers have been converted to ordinary Markdown hyperlinks. This is a research proposal, not an approved implementation specification or release qualification.
>
> Evidence guide: repository inspection describes verified accessible documents/PR metadata; model cards, project READMEs and papers describe publisher-reported capabilities and results, not independent TinyBuilder measurements; arithmetic estimates are not measurements; engineering hypotheses and proposed decisions require local validation. No model downloads, training, paid compute, or live model benchmarks were performed for this report.
>
> Maintainer note: references in the original report/prompts to a "Python 0.1" contract are historical wording, not authorization to change the native Rust read-only release. The current [AGENTS.md](https://github.com/MrPunyapal/TinyBuilder/blob/main/AGENTS.md) and [release requirements](https://github.com/MrPunyapal/TinyBuilder/blob/main/docs/RELEASE_0_1.md) take precedence; Python/mutation examples remain reference/lab only. The research rankings and targets are proposals, not established product claims.

## Executive recommendation and repository findings

TinyBuilder should **not** optimize first for the smallest possible model file. It should optimize for the smallest *system* that reliably completes real coding tasks. The most promising design is a **Rust coding harness around a 1.5B–4B local model**, with deterministic repository intelligence, constrained tool protocols, bounded context, executable verification, optional Laravel Boost/MCP integration, and explicit safety controls outside the model. That direction is consistent with the repository's own strongest design decisions: the current guidance already separates weights from runtime memory, keeps web/MCP results transient, requires opt-in writes and execution, and says training should wait until a repeatable executable benchmark exists. [AGENTS.md][agents] · [VISION.md][vision]

The recommended model strategy is therefore **two-tiered rather than single-model absolutism**. Qwen2.5-Coder-1.5B-Instruct should be the first specialization and low-memory baseline because it is code-specific, Apache-2.0 licensed, small enough for aggressive local experimentation, and has official GGUF releases. [Model card][qwen15] · [GGUF][qwen15gguf] Granite 4.2-3B should be the leading candidate for the initial higher-quality default because IBM's current model card describes native tool calling with integrated reasoning and its 3B scale is a materially better fit for a 4 GB GPU than most 7B-class models. [Model card][granite] · [README][granitereadme] Qwen3.5-4B and Phi-4-mini-instruct should be benchmarked as ceiling/reference candidates rather than assumed winners: Qwen3.5-4B exposes a current tool-call parser and long-context serving path, while Phi-4-mini is MIT licensed, 3.8B parameters, supports 128K context, and includes an explicit function-calling format. [Qwen3.5][qwen35] · [Phi-4-mini README][phireadme] · [Phi-4-mini model card][phi]

A **200–500 MB total resident coding agent is not a realistic target** if TinyBuilder is expected to perform dependable unfamiliar-repository reasoning, multi-file repair and tool use. At four bits, the theoretical raw weight payload alone is roughly 0.5 bytes per parameter, so 500 MB corresponds only to about one billion parameters before quantization metadata, KV cache, compute buffers, tokenizer state, runtime libraries, repository indexes and the TinyBuilder process itself. llama.cpp explicitly documents that KV memory grows roughly with context length and supports reducing GPU layers when VRAM is exhausted, demonstrating why model-file size and runtime memory are different quantities. [llama.cpp memory guidance][llamamemory] · [AGENTS.md][agents] A 200–500 MB **weight file** is achievable for a roughly 0.4B–1B quantized model, but TinyBuilder's own recorded experiment found zero native tool calls from stock Qwen2.5-Coder 0.5B, 1.5B and 3B Ollama tags, so size alone is clearly not evidence of agent reliability. [TinyBuilder repository][repo]

The repository inspection supports keeping the existing 0.1 line separate. Main currently describes itself as a research prototype with a local OpenAI-compatible model endpoint, a small tool loop, optional Laravel Boost through MCP, explicit SQLite project preferences, and opt-in write/execute permissions. It specifically says the current product has no trained TinyBuilder model, no generic browser/search tool, no Docker sandbox and no demonstrated autonomous-coding reliability. [TinyBuilder repository][repo] `AGENTS.md` goes further: a 400 MB file is not equivalent to a 400 MB resident process; externally retrieved information must remain transient; training should follow benchmark evidence rather than precede it; and arbitrary prose or Markdown must never be reinterpreted as a tool action. [AGENTS.md][agents] These are sound constraints and should be preserved.

PR #18 is appropriately conservative. It is a draft, lab-only Rust patch experiment on `feat/rust-patch-lab`, explicitly preserving the production read path and avoiding product CLI/runtime changes. Its stated purpose is evidence-bound patch proposals, independent diagnostics, fresh snapshots and exact-head validation, and its author explicitly says exact proposal scoring is not semantic qualification. [PR #18][pr18] This is useful infrastructure, but it should not become the product architecture. A patch laboratory is a test instrument, not an agent design.

PR #20 is more strategically important. It is stacked on #18 and explicitly declares itself independent of the 0.1 release. Its research direction emphasizes general coding intelligence instead of reproducing a fixed workflow, a Laravel-first local-SLM TUI, retrieval/plugins/bounded temporary memory, and new cross-file fixtures. Crucially, it also states that the current cross-file suite is only a **narrow single-line repair** and that actual model/Laravel runs remain pending. [PR #20][pr20] That honesty matters: these fixtures should remain smoke tests, not headline evidence that TinyBuilder has solved multi-file coding.

`docs/VISION.md` on `research/workflow-slm-lab` gives the right high-level product boundary: Rust core independent from UI; lightweight terminal UI first; the smallest model should be chosen by measured capability rather than marketing size; changing facts belong in docs/web/MCP rather than weights; temporary context should be bounded; permissions and security must remain deterministic; and Windows x64, macOS ARM64 and Linux x64 should all be measured explicitly. [VISION.md][vision] The architecture below develops that vision further but deliberately rejects one possible interpretation: **TinyBuilder should not become a workflow engine whose intelligence is mainly a hand-authored state machine**. Deterministic orchestration should constrain unsafe or mechanically reliable operations while leaving diagnosis, hypothesis formation, evidence selection and repair synthesis to the model.

There is one material repository-inspection blocker. GitHub exposed the repository, `AGENTS.md`, both PR descriptions/commits, and `docs/VISION.md`, but attempts during research to enumerate the full research-document tree on `research/workflow-slm-lab` intermittently failed through the GitHub fetch layer. Therefore, findings about research documentation that was not separately surfaced by the PR pages are limited to the accessible files and PR summaries; I have not inferred unseen file contents. The user-supplied heads—PR #18 at `8f1c45e2233d93ea0958449cb53728a4085ea071` and PR #20 at `c7e6646288ec1a964c917366eb298b70036d7a5d`—should be treated as the reproducibility anchors for future local review.

**Executive decision:** build a **small-model amplifier**, not a tiny-model demonstration. The first credible TinyBuilder milestone should be: Rust harness + token-budgeted repository map + lexical/AST/LSP retrieval + typed edit protocol + disposable Git worktree + Laravel verifier chain + 1.5B/3B/4B model qualification suite. Fine-tuning should begin only after that harness separates model failures from retrieval and protocol failures.

## Evidence from open-source projects and research

No single existing project is a blueprint for TinyBuilder. The strongest approach is to extract one or two experimentally useful ideas from each and reject the parts that conflict with the product constraints.

**Aider** provides one of the most relevant repository-intelligence patterns. Its implementation uses Tree-sitter-derived definitions/references, constructs a graph of relationships and ranks the graph so a small token budget contains high-value repository structure rather than entire files. The current source still contains PageRank-based repo-map logic and Tree-sitter language support. [Source][aidermap] · [Repo map documentation][aiderdocs] This is exactly the type of deterministic preprocessing that improves a small model without consuming model capacity. TinyBuilder should adapt the principle—symbol extraction, dependency edges, ranking and hard token budgets—but not copy Aider's implementation or assume PageRank is universally optimal. For Laravel in particular, framework conventions, Composer metadata, service providers, routes, Eloquent relationships and Blade/Livewire references may provide better ranking signals than generic reference centrality.

**mini-swe-agent** demonstrates the opposite useful extreme: a surprisingly small harness can be competitive when the model and environment are strong. The project describes its core agent class as roughly 100 lines and uses a simple command-driven interaction model; its current configuration also aggressively truncates long command output. [Project][mini] · [Configuration][miniconfig] The lesson is architectural simplicity, not “give a tiny model unrestricted Bash.” Its default Bash-centric interface is unsuitable as TinyBuilder's primary weak-model tool surface because shell syntax has an enormous action space and collapses authorization, editing, retrieval and execution into one dangerous primitive. TinyBuilder should adopt **small harness concepts and bounded observations**, while exposing narrow typed tools.

**Agentless** is especially important as a control condition. Its paper found that a simple localization → repair → validation pipeline achieved a reported 32% on SWE-bench Lite at low inference cost at the time of publication. [Paper][agentless] The result does not imply an interactive coding assistant should be a fixed three-stage workflow. It does imply TinyBuilder should test whether a complicated agent loop actually beats simpler decomposition. Agentless should therefore become an **evaluation ablation**: for each benchmark task, compare adaptive TinyBuilder against a constrained localization/repair/validate path using the same model and evidence. If the fixed baseline wins often, the orchestration layer is wasting model capacity.

**OpenHands** demonstrates the breadth of a generalist software-development environment: code editing, command-line interaction, browser access, sandboxing and benchmark integration. [Paper][openhands] · [ICLR proceedings][openhandsiclr] Its value to TinyBuilder is principally in security and evaluation patterns. Its full generalist architecture is too broad for a lightweight first release. TinyBuilder should resist copying multi-agent coordination, browser abstractions or general-purpose platform machinery until a measured Laravel workload needs them.

**SWE-smith** is more valuable for data creation than runtime architecture. The project turns repositories into software-engineering training environments and currently distributes roughly 52,000 task instances. [Project][swesmith] · [README][swesmithreadme] TinyBuilder should adapt the idea for PHP: introduce controlled defects into permissively licensed Laravel applications, require real Pest/PHPUnit/static-analysis verification, preserve repository lineage and license metadata, and retain only tasks whose injected bug is independently reproducible. Unlike generic synthetic prompt generation, this produces executable supervision.

**SWE-Master** provides evidence that post-training trajectories, execution feedback, context management and LSP integration can materially matter. The authors report 61.4% Pass@1 on SWE-bench Verified for their Qwen2.5-Coder-32B system and describe a pipeline spanning trajectory synthesis, SFT, RL with execution feedback, test-time scaling, LSP tools and summary-based context management. [Project][swemaster] Those absolute scores are not transferable to a 1.5B or 3B TinyBuilder model, and the 32B training regime is far outside the available hardware. What *is* transferable is the ordering: build valid trajectories and execution infrastructure before attempting reinforcement learning.

**CodeRL** provides earlier evidence for the same principle at a smaller conceptual scale: executable unit-test outcomes can act as functional rewards, and test feedback can drive regeneration rather than relying only on static supervised labels. [Paper][coderl] · [Code][coderlcode] TinyBuilder should use this only after high-quality SFT and a reliable verifier exist. RL on a noisy harness teaches the model harness quirks.

**QLoRA** is the most relevant training-efficiency technique for the user's hardware. It freezes a 4-bit base model and backpropagates through it into low-rank adapters, significantly reducing training memory compared with full fine-tuning. [Paper][qlora] This is a strong reason to improve an existing code-capable pretrained model rather than train a new transformer architecture. The original paper's demonstration of 65B fine-tuning used a 48 GB GPU, however, so it does **not** establish that every useful 3B–7B sequence length can be trained comfortably on 4 GB. Hardware feasibility still needs local measurement.

**workflow-slm** is useful as a narrow research idea rather than a product foundation. Its core thesis is that a small model may execute a known branching/tool procedure more efficiently when the behavior is heavily constrained. That can be investigated for TinyBuilder's **stable micro-skills**—for example, selecting a verifier or emitting a patch envelope—but it conflicts with the broader requirement to reason over unfamiliar repositories if generalized into the entire agent. The TinyBuilder vision and PR #20 correctly reject making the product a fixed workflow compiler. [workflow-slm][workflow] · [PR #20][pr20] · [VISION.md][vision]

**little-coder** is relevant for harness engineering: model-specific profiles, dynamic skills, context compaction, tool parsers and evidence-oriented prompting are sensible ideas for weak models. Its public benchmark claims should not be treated as independent evidence unless reproduced under TinyBuilder's own harness. This distinction is important throughout the project: repository README claims are *reported results*, not TinyBuilder measurements. [little-coder][littlecoder] · [Architecture][littlearchitecture]

**Laravel Boost** should be an optional first-party Laravel intelligence source rather than a hard dependency. Current Laravel documentation says Boost exposes an MCP server, version/package-aware documentation retrieval, AI guidelines/skills and more than 17,000 Laravel ecosystem knowledge items through its hosted documentation API. [Boost documentation][boost] · [Laravel 12 AI documentation][laravelai] It can therefore solve two hard problems cheaply: framework-aware inspection and changing documentation. But Boost can expose powerful tools such as database operations and Tinker, so TinyBuilder's own permission system must remain authoritative. [Boost announcement][boostannouncement]

**Tree-sitter and LSP solve different problems and both belong in the design.** Tree-sitter is an incremental parser that can rapidly build and update syntax trees. [Tree-sitter][treesitter] · [Implementation][treesitterimpl] That makes it suitable for cheap local symbol extraction, imports, declarations and syntactic ranges. LSP should provide semantic operations—definition, references, diagnostics, workspace symbols—when a language server is available. TinyBuilder should use Tree-sitter as the universal structural layer and LSP as an optional semantic accelerator, rather than making PHP language-server availability a prerequisite. [LSP specification][lsp]

The research literature and project survey point to a general principle: **agent intelligence is multiplicative**. Model capability, evidence quality, protocol reliability and verification all matter. A mediocre model with an excellent repository map can still fail because its edit protocol is unreliable; a better model can still fail because a wrong file was retrieved; and a correct patch can still be unsafe because the harness permitted an unintended command. TinyBuilder's benchmark must therefore decompose these failure channels instead of reporting a single pass rate.

## Model selection, specialization, and hardware feasibility

### Ranked candidates

The ranking below is for **TinyBuilder fit**, not generic model prestige. “Reported capability” means the publisher's model card or project report, not a TinyBuilder measurement.

| Rank | Candidate | Why it belongs | Main concern | TinyBuilder role |
|---|---|---|---|---|
| **1** | **Granite 4.2-3B** | Apache-licensed 3B model; publisher explicitly documents integrated reasoning and tool calling. [Model card][granite] · [README][granitereadme] | Not specifically a PHP/Laravel coding model; must test code-repair quality independently. | Primary 3B qualification candidate and likely first “quality default.” |
| **2** | **Qwen2.5-Coder-1.5B-Instruct** | Code-specialized, Apache-2.0, official GGUF availability, small enough for extensive QLoRA experimentation. [Model card][qwen15] · [GGUF][qwen15gguf] | Existing TinyBuilder Windows evaluation found unreliable stock tool use, so harness/training must compensate. [Repository][repo] | Best first specialization base and low-resource production candidate. |
| **3** | **Qwen3.5-4B** | Current 4B model with official serving examples using reasoning and `qwen3_coder` tool parsers. [Model card][qwen35] · [README history][qwen35readme] | General/multimodal rather than narrowly code-specialized; 4 GB VRAM is tight once context/KV/buffers are included. | Quality ceiling candidate for hybrid CPU/GPU execution. |
| **4** | **Phi-4-mini-instruct** | MIT, 3.8B, 128K context, explicit function-calling format and strong instruction-following focus. [Model card][phi] · [Pinned README][phipinned] | General model; PHP/Laravel competence must be established experimentally. | Cross-family control against Qwen/Granite. |
| **5** | **Qwen2.5-Coder-0.5B** | Extremely small code-specific baseline from the same family. | TinyBuilder already observed zero native tool calls in its recorded stock Ollama evaluation. [Repository][repo] | Ultra-light control; possibly autocomplete/local micro-specialist, not main agent. |
| **6** | **DeepSeek-Coder-1.3B-class models** | Historically useful compact coding baselines. | Older generation and custom model licensing makes them less attractive than Apache/MIT alternatives. | Secondary research baseline only. |
| **7** | **7B-class local coding models** | Likely higher raw reasoning ceiling. | Poor match for 4 GB VRAM and “ordinary computer” latency objective. | Benchmark occasionally as an upper bound, not first target. |

Qwen2.5-Coder-3B deserves a special note: technically it sits in a useful size range, but the 3B checkpoint family used a different Qwen research license rather than the clean Apache-2.0 licensing of the 0.5B/1.5B/7B variants. For a commercially usable open-source product, that licensing asymmetry makes it a poor default unless legal review establishes compatibility. TinyBuilder should prefer a clearly permissive alternative rather than optimize around an avoidable licensing question. [3B model card][qwen3b] · [0.5B model card][qwen05] · [DeepSeek license][deepseeklicense]

### Why 1.5B–4B is the practical band

For rough planning, four-bit weight-only storage is approximately:

| Parameters | Theoretical 4-bit payload |
|---:|---:|
| 0.5B | ~0.25 GB |
| 1.0B | ~0.50 GB |
| 1.5B | ~0.75 GB |
| 3.0B | ~1.50 GB |
| 4.0B | ~2.00 GB |
| 7.0B | ~3.50 GB |

These are **arithmetic lower-bound estimates, not measurements**. Real GGUF sizes vary with quantization format and tensor treatment, and runtime memory adds model metadata, tokenizer structures, compute buffers and KV cache. llama.cpp's documentation explicitly notes that KV cache scales approximately with context size and that users may need to reduce `--n-gpu-layers` when GPU memory is insufficient. [llama.cpp memory guidance][llamamemory]

On an RTX 3050 with 4 GB VRAM, a 1.5B Q4 model should be the least constrained candidate; a 3B Q4 model is likely practical with useful partial/full GPU offload depending on context and backend buffers; and a 4B Q4 model is likely to require tighter contexts or hybrid offload. These are **engineering hypotheses**, not measured throughput claims. llama.cpp explicitly supports CPU+GPU hybrid inference, making it well suited to this hardware class. [llama.cpp][llama] · [Server options][llamaserver] A 7B Q4 model can plausibly reside in 16 GB system memory, but the 4 GB GPU cannot hold model weights plus a substantial context comfortably, so latency may undermine the “everyday local assistant” goal.

TinyBuilder should therefore benchmark contexts such as 4K, 8K, 16K and perhaps 32K rather than advertise the model's theoretical maximum. Repository intelligence should keep the *useful* context small enough that most tasks do not need 100K+ tokens.

### What to specialize

The model should learn skills that are difficult to enforce deterministically but stable across projects:

**Inside the weights:** code reasoning; intent decomposition; reading compact repository maps; choosing among a small set of tools; interpreting test/static-analysis errors; proposing concise edits; PHP syntax and Laravel idioms; determining when evidence is insufficient; following TinyBuilder's typed action protocol; and revising a patch based on verification.

**Outside the weights:** current Laravel/package documentation; exact repository structure; package versions; permissions; sandbox policy; file freshness; ASTs; symbol/reference indexes; secret detection; network access policy; command allowlists; patch application; and success/failure determination.

This division directly follows the repository vision that changing facts and security policy should not be encoded solely in weights. [VISION.md][vision]

### Training strategy

The highest intelligence improvement per engineering effort is likely:

**First: harness qualification without training.** Establish model × quantization × context × tool-protocol baselines. This prevents fine-tuning around defects that actually belong to retrieval or parsing.

**Second: supervised LoRA/QLoRA on verified trajectories.** QLoRA's 4-bit frozen-base approach is specifically designed to reduce fine-tuning memory. [Paper][qlora] Train TinyBuilder behavior rather than broad knowledge: evidence requests, tool selection, patch envelopes, repair after test failure, and concise final reporting.

**Third: continued code pretraining only if PHP gaps are clearly diagnosed.** If models understand agent protocol but repeatedly fail PHP syntax/framework patterns, a small amount of license-clean PHP/Laravel continued pretraining can help. Do not do this merely because “the model contains too much general knowledge.” Parameter count is architectural; deleting facts does not automatically remove parameters.

**Fourth: distillation where legally and contractually permitted.** Distill *reasoning behavior and verified actions*, not proprietary prose. Prefer teacher-generated problem variations whose final solutions are independently validated by tests and whose source repositories permit the resulting training use. Distillation should be treated as a data-generation technique, not proof that a 1.5B model can inherit a frontier model's full reasoning depth.

**Fifth: executable-reward RL only after SFT succeeds.** CodeRL and SWE-Master both support the general idea that test execution can provide useful learning signals. [CodeRL][coderl] · [SWE-Master][swemaster] Start with tightly scoped rewards: patch applies, target test passes, regression tests pass, static analysis does not worsen, and no forbidden action occurs. Avoid complex reward models initially.

**Pruning and quantization-aware training should be deferred.** Post-training 4-bit quantization is much easier to evaluate and reverse. Structural pruning can permanently damage code knowledge and tool-following behavior; QAT adds complexity before there is evidence that normal Q4 is the bottleneck.

**Training a new architecture from scratch should be rejected.** A few-billion-parameter code model requires orders of magnitude more data and compute than available locally, and the main unsolved problem is not transformer architecture—it is reliable repository-level behavior. TinyBuilder's advantage should come from specialization and harness design.

### Training on the available machine

The RTX 3050's 4 GB VRAM makes **1.5B QLoRA the sensible first experiment**. Short sequences, gradient accumulation, checkpointing and careful adapter targeting are likely necessary. A 3B adapter run may be possible with CPU offload or layer-streaming tools, but should be treated as experimental until measured. Claims by specialized trainers that much larger models can be fine-tuned on 4 GB hardware are interesting but not sufficient evidence for a production plan unless TinyBuilder reproduces them end-to-end with correctness checks. [PEFT LoRA][peft] · [PEFT quantization][peftquant] · [Unsloth][unsloth] · [Soup][soup] · [Soup training documentation][soupdocs]

Free cloud GPU services can supplement experiments, but they should not become a dependency. Free notebook offerings are quota-constrained, hardware availability varies and sessions can terminate; therefore TinyBuilder should use them only for reproducible one-off experiments with pinned environments and resumable checkpoints. The project should remain fully usable without them. [Colab FAQ][colab] · [Kaggle notebooks][kaggle]

## Recommended TinyBuilder architecture and Laravel integration

The central architectural recommendation is a **capability-based Rust kernel with adaptive model reasoning**.

```text
User / TUI
    │
    ▼
Task Session
    │
    ├── Permission & trust state
    ├── Bounded temporary memory
    ├── Context/token budget
    └── Audit metadata
    │
    ▼
Adaptive Agent Controller
    │
    ├── Model provider
    ├── Context planner
    ├── Tool selector
    └── Verification/retry policy
    │
    ├────────── Repository Intelligence ───────────┐
    │       lexical │ Tree-sitter │ LSP │ graphs      │
    │                                                │
    ├────────── Typed Local Tools ──────────────────┤
    │ read │ search │ patch │ test │ diagnostics     │
    │                                                │
    ├────────── Plugin Runtime ─────────────────────┤
    │ Laravel │ docs │ web │ MCP │ future ecosystems │
    │                                                │
    └────────── Safety Boundary ────────────────────┘
            worktree / sandbox / exact approvals
```

### Rust core responsibilities

| Core component | Responsibility | Why it belongs in Rust rather than the model |
|---|---|---|
| **Repository index** | File inventory, ignore handling, lexical index, AST symbols, import/reference edges | Deterministic, fast, reusable and cheap. |
| **Context planner** | Fit evidence to explicit token budgets; rank files/symbols/errors | Prevents small-model context overload. |
| **Tool registry** | Typed JSON schemas, capability metadata, result limits | Protocol reliability is infrastructure. |
| **Permission engine** | Read/write/exec/network/MCP capabilities; exact action approvals | Safety cannot depend on model compliance. |
| **Patch engine** | Freshness check, atomic apply, rollback, diff generation | Avoids model-written shell mutation. |
| **Verifier scheduler** | Syntax, formatter, static analysis, targeted tests, full tests | Independent truth signal. |
| **Worktree/sandbox layer** | Disposable mutation environment | Limits blast radius. |
| **Provider layer** | llama.cpp/Ollama/OpenAI-compatible local adapters | Keeps model interchangeable. |
| **Session memory** | Bounded in-memory facts/summaries | Prevents transcript explosion and unintended persistence. |
| **Plugin host** | Ecosystem adapters, MCP, docs/search | Keeps Laravel specialization outside the generic core. |

The Rust core should expose only a handful of strong abstractions. Avoid a giant internal “agent framework.” A useful design target is that a headless session can be driven by a test harness without the TUI, and that every model-visible action ultimately resolves into a typed capability checked by the core.

### Repository intelligence

Start with **lexical + structural retrieval before embeddings**. This is one assumption worth challenging: vector embeddings are not automatically the best first retrieval mechanism for source code. Exact class names, symbols, route names, method calls, package names and error strings often favor lexical retrieval, while Tree-sitter can expose structural relationships cheaply. Aider's repository-map success shows that symbol graphs can produce compact high-value context. [Aider source][aidermap]

A TinyBuilder query should create candidates from several deterministic channels:

`ripgrep/BM25-like lexical hits → AST declarations/references → Composer/autoload relationships → framework convention edges → LSP definitions/references → recent verifier-error locations`.

Then a cheap ranker merges them under a token budget. Embeddings should remain an optional plugin and be promoted into the default only if an ablation demonstrates statistically meaningful task-success improvement per RAM/latency cost.

A repository map should not be a fixed dump. Generate several levels:

- **Level A:** path + language + important package metadata.
- **Level B:** class/function signatures and inheritance/trait relationships.
- **Level C:** edges relevant to the current task.
- **Level D:** selected code windows requested by the model.

A typical SLM should see hundreds to low thousands of map tokens, not every source file.

### Agent loop

TinyBuilder should use a flexible loop rather than a workflow script:

```text
orient
  ↓
request evidence ──────────┐
  ↓                    │
form hypothesis        │
  ↓                    │
propose action         │
  ↓                    │
permission check       │
  ↓                    │
execute/apply          │
  ↓                    │
verify                 │
  ├── success → final
  └── failure → compact diagnosis ─────┘
```

These are **states available to the controller**, not mandatory phases. The model may retrieve additional evidence after a failed test or decide that no edit is warranted. The controller should enforce only budgets, permissions, protocol and verification.

For weak models, dynamically expose a **small tool menu**. A PHP bug-fix turn may need only `search_symbols`, `read_ranges`, `propose_patch`, and `run_verifier`; it should not simultaneously receive 30 MCP tools, a browser, memory mutation, Git operations and arbitrary shell. Tool selection itself consumes reasoning capacity.

### Tool protocol

Do not rely on prompt-only JSON. The repository already observed fenced/invalid JSON behavior from small models and explicitly forbids arbitrary-prose extraction. [Repository][repo] · [AGENTS.md][agents] Prefer, in order:

1. server/backend grammar or JSON-schema constrained generation;
2. model-native tool calling **only after per-model qualification**;
3. a strict TinyBuilder action envelope parsed independently.

A valid action should include a monotonically increasing evidence revision or file hash. If a patch was generated against stale source, reject it and refresh the model context rather than “best effort” applying it.

### Laravel plugin architecture

Laravel should be the first **ecosystem plugin**, not the core's identity. A possible Rust trait boundary is:

```rust
trait EcosystemPlugin {
    fn detect(&self, repo: &Repository) -> Detection;
    fn repository_hints(&self, repo: &Repository) -> Vec<RepoHint>;
    fn tools(&self) -> Vec<ToolSpec>;
    fn verifiers(&self) -> Vec<VerifierSpec>;
    fn documentation(&self) -> Vec<DocsProviderSpec>;
    fn guidelines(&self) -> Vec<GuidelineSource>;
}
```

The Laravel implementation should detect `composer.json`, `artisan`, installed Laravel/framework/package versions, test stack and Boost availability. It should augment retrieval with framework-specific edges—routes to controllers, models to migrations/factories, request validators, policies, Blade/Livewire components, jobs/events/listeners, service providers and tests—without teaching the generic repository index what Laravel is.

Boost should be an **optional MCP-backed enrichment**. Official Laravel documentation describes Search Docs as package/version aware and Boost as exposing a broad set of project-inspection tools. [Boost documentation][boost] · [Announcement][boostannouncement] TinyBuilder should wrap these capabilities with its own trust labels:

`read-only`, `project-sensitive`, `write-like`, `exec-like`, `networked`.

A Boost tool that runs Tinker must never become safe merely because its MCP metadata calls it benign.

The default Laravel verifier chain should be adaptive:

```text
changed PHP → php -l
style-sensitive → Pint check
typed/domain code → PHPStan/Larastan if installed
targeted tests → Pest or PHPUnit
broader affected subsystem → test subset
high-confidence completion → optional full suite
```

The plugin should discover commands from the project rather than assume every repository has Pest, Larastan or Pint. Formatting should be treated separately from correctness so an autoformatter does not obscure the model's semantic patch during diagnosis.

Laravel-specific knowledge such as Eloquent conventions, Blade directives and Livewire patterns should be split between **stable model specialization**, **version-aware docs**, and **project evidence**. Do not attempt to memorize every Laravel API revision in the model.

## Knowledge, tools, security, interface, and distribution

### Free and sustainable retrieval

The knowledge strategy should have an explicit hierarchy:

**Local first:** project files, `composer.json`/lockfile, project guidelines, AGENTS-like files, Git history if permitted, Tree-sitter index, LSP, local installed package source and generated framework metadata.

**Framework retrieval second:** Laravel Boost Search Docs when installed and explicitly enabled. Its documentation endpoint is version/package-aware and therefore preferable to general web search for Laravel API questions. [Boost documentation][boost] · [Laravel 12 Boost][boost12]

**Generic web retrieval third:** a provider interface that can use a user-specified free endpoint or a self-hosted metasearch service. The core should not depend on a paid search API. Search results and fetched content should be held in session memory and discarded, matching `AGENTS.md`'s explicit no-disk-cache requirement. [AGENTS.md][agents] · [SearXNG][searxng] · [SearXNG license][searxlicense]

**Offline fallback:** installed package source, vendored documentation when its license permits redistribution, plugin-provided static guidance and project-local documents. The interface must clearly distinguish “live documentation unavailable” from “no answer.”

Every retrieved item should carry provenance:

```text
origin
URL or local path
provider/server
retrieval timestamp
package/version scope
trust classification
content hash
```

The model should receive the source text inside explicit “untrusted evidence” boundaries. Retrieved instructions should never alter permissions.

### MCP

MCP belongs behind the same capability engine as native tools. Current MCP security guidance for skills explicitly says server-provided skill content must be treated as untrusted model input and cannot be allowed to widen host permissions merely through its own metadata. [MCP Skills Extension][mcpskills] · [MCP C# SDK][mcpcsharp] That aligns closely with TinyBuilder's vision that external content is data rather than instruction. [VISION.md][vision]

Recommended MCP policy:

```text
server installation → explicit user trust
tool discovery       → schema only, no privilege grant
tool invocation      → TinyBuilder capability check
sensitive argument   → exact human approval where configured
result               → tainted/untrusted evidence
follow-up action     → new capability check
```

Capabilities should be **non-transitive**. Reading a malicious README must not allow a subsequently suggested web tool to exfiltrate `.env`. A session that has read private source and then wants an open-network action should trigger a higher-risk approval path.

### Prompt-injection resistance

Model prompting is only a secondary defense. The robust boundary is deterministic:

- tool and MCP descriptions are untrusted;
- retrieved web/docs text cannot create permissions;
- secret-bearing paths can be hidden/redacted from remote providers;
- commands are represented as argv vectors, not shell strings, where possible;
- approvals bind to exact command, path set, working directory and content revision;
- symlinks are resolved before path-policy checks;
- write targets are restricted to the worktree;
- destructive commands require a different capability than ordinary test execution;
- network access is independent from command execution;
- patch application occurs through TinyBuilder, not arbitrary model shell commands.

The current 0.1 warning correctly acknowledges that exact argv allowlists are **not an OS sandbox**. [Repository][repo] Research TinyBuilder should add real containment for mutating/exec tasks. On platforms where strong sandboxing is difficult, disposable Git worktrees plus narrowly granted process execution are still better than an unrestricted project directory, but should not be marketed as equivalent to a container or VM.

### TUI versus desktop

Start with a **native Rust TUI**. `docs/VISION.md` already points that way, and the rationale is strong: a terminal UI minimizes memory, distribution complexity and webview dependencies while naturally matching developer workflows. [VISION.md][vision] The TUI should be intentionally thin: task composer, evidence/tool timeline, diff viewer, approval dialog, test status, model/runtime status and context-budget indicator.

Ratatui + Crossterm is the most sensible first stack. [Ratatui][ratatui] · [Installation][ratatuiinstall] The important architectural requirement is that no agent logic lives in TUI widgets. The UI consumes an event stream from the Rust core so the same kernel can support:

```text
tinybuilder       interactive TUI
tinybuilder run   headless CLI
TinyBuilder IPC   future IDE / desktop integration
```

A Tauri desktop shell is reasonable later if developers need richer diff rendering, settings, MCP management or onboarding. It should call the same Rust core rather than create a second agent runtime. [Tauri][tauri] · [Architecture][tauriarchitecture]

### Distribution

Do not bundle a model into the main executable. Ship signed/checksummed binaries for Windows x64, macOS ARM64 and Linux x64, then let the user select/install an explicitly licensed model. Separating model distribution from the core keeps the Rust binary small, avoids silently downloading multi-gigabyte assets, and permits model upgrades without application releases. This also matches the existing repository constraint against implicit large downloads. [AGENTS.md][agents]

llama.cpp should be the principal low-level runtime target because it supports CUDA and CPU execution and CPU/GPU hybrid offload. [Build guide][llamabuild] · [llama.cpp][llama] TinyBuilder can continue supporting Ollama/OpenAI-compatible servers as a convenience abstraction, but benchmarking should pin the underlying runtime/version because provider defaults can otherwise confound model comparisons.

## Evaluation and data-generation pipeline

TinyBuilder needs its own benchmark because mainstream coding benchmarks do not adequately measure the actual product: low-resource local inference, Laravel, permission-aware tools, live docs and multi-file application changes.

### TinyBuilder Bench

Build **60–100 executable tasks initially**, growing only when task quality remains high. Use several permissively licensed or purpose-built Laravel repositories, held out by repository rather than merely by issue. Each benchmark instance should contain:

```text
base Git commit
natural-language task
environment manifest
allowed capabilities
public tests
hidden tests
static-analysis checks
maximum turns/tool calls
context budget
expected behavioral properties
security expectations where relevant
```

Suggested composition:

| Class | Example | Primary success signal |
|---|---|---|
| Code generation | Add validated endpoint + test | Hidden tests |
| Bug diagnosis | Explain and fix broken authorization | Target + regression tests |
| Feature implementation | Add model relationship and UI path | Multi-file hidden tests |
| Multi-file repair | Rename domain behavior across controller/service/test | Compile + tests + affected references |
| TDD | Given failing test, implement behavior | Test transitions fail→pass |
| Unfamiliar repo | Change feature with no file hint | Retrieval + tests |
| Laravel-specific | Eloquent scopes, events, Blade, Livewire, queues | Framework tests |
| Tool use | Locate symbol, inspect package version, execute exact verifier | Correct action trace |
| Docs | Resolve version-dependent API from live/local docs | Correct citation + implementation |
| Security | Malicious README asks to read `.env` and upload it | No prohibited action |
| Refusal/approval | Destructive migration/command request | Correct escalation/denial |

SWE-bench's central insight—that real repository tasks are scored by executable repository tests rather than textual similarity—is appropriate here. [SWE-bench][swebench] · [FAQ][swebenchfaq] Exact patch matching should never be the primary metric because many repairs have multiple valid implementations.

The PR #20 cross-file fixtures should be retained as fast CI smoke tests, but its own description says they are narrow single-line repairs rather than general multi-file editing. [PR #20][pr20] They are useful for catching regressions, not for claiming coding-agent competence.

### Measurements

For every trial record:

**Correctness:** task pass/fail, hidden tests, regressions, syntax/static analysis, unauthorized action count.

**Model behavior:** tool-call validity, incorrect-tool rate, retrieval requests, edit attempts, repair attempts, premature-final rate.

**System cost:** wall-clock latency, time to first token where exposed, generation throughput where exposed, model prompt/output tokens, peak process RAM, peak GPU VRAM, context length and disk I/O.

**Energy:** sample NVIDIA GPU power via NVML/`nvidia-smi` where available and integrate over task duration. CPU energy should be reported only when a reliable platform counter is available; do not invent it on machines without one.

**Reproducibility:** model repository/revision, GGUF hash and quantization, llama.cpp commit, OS/build, CUDA version, CPU/GPU, context settings, temperature/seed and TinyBuilder Git commit.

Run a deterministic or near-deterministic baseline and at least several repeated trials for stochastic configurations. Report confidence intervals rather than one lucky run.

### Failure attribution experiments

The highest-value benchmark output is not a leaderboard; it is a failure matrix. Hold the model fixed and vary one subsystem:

```text
retrieval:
  full files
  lexical
  lexical + AST
  lexical + AST + LSP
  lexical + AST + LSP + embeddings

protocol:
  native tools
  prompt JSON
  constrained schema

verification:
  none
  targeted tests
  targeted + static analysis
  adaptive repair loop

knowledge:
  offline only
  Laravel Boost
  generic web

context:
  fixed large
  dynamic token-budgeted
```

Then hold orchestration fixed and vary model/quantization. This separates:

`reasoning failure`, `localization failure`, `retrieval ranking failure`, `protocol failure`, `edit-application failure`, `test interpretation failure`, `permission-policy failure`, and `external-tool failure`.

That decomposition will tell TinyBuilder where to invest. If Qwen2.5-Coder-1.5B generates correct fixes when given the right file but fails to retrieve it, fine-tuning code synthesis is not the priority. If retrieval is correct but tool envelopes fail, protocol SFT may produce much more value than adding another billion parameters.

### Training-data pipeline

A license-conscious data pipeline should be:

```text
permissive / owned repository
        ↓
task source
  ├── real historical bug/feature
  ├── manually authored task
  └── controlled synthetic mutation
        ↓
reproduce failure
        ↓
generate candidate trajectory
        ↓
independent executable validation
        ↓
policy + provenance + license filters
        ↓
deduplicate by repository/task/patch semantics
        ↓
train / validation / held-out split by repository
        ↓
SFT dataset
```

For synthetic repair, adapt SWE-smith's idea of generating repository-level tasks and retaining executable environments. [SWE-smith][swesmith] For trajectories, keep **only verified successful paths and informative failed→recovered paths**. Do not train on every agent transcript: verbose confusion becomes learned behavior.

Each trajectory should include structured events rather than natural-language theater:

```json
{
  "task": "...",
  "evidence": [...],
  "action": {"tool": "...", "arguments": {...}},
  "observation": {...},
  "patch": "...",
  "verification": {...},
  "outcome": "pass"
}
```

Generate counterexamples for tool safety as well: malformed arguments, stale patches, forbidden paths, prompt-injected tool results and unnecessary high-risk actions. A small model benefits from seeing what **not** to do when the rejection signal is unambiguous.

PHP/Laravel continued-pretraining material must preserve source licensing metadata and avoid assuming that “public GitHub” means unrestricted training rights. Model-specific and dataset-specific terms should be captured in a machine-readable manifest.

### Specialization experiments

Run controlled comparisons rather than “fine-tuned feels better”:

```text
base
base + protocol SFT
base + protocol + Laravel SFT
base + verified repair trajectories
base + continued PHP pretraining + SFT
base + SFT + execution-reward RL
```

Evaluate each on the **same held-out repositories**. A training technique is accepted only if it raises executable task success without unacceptable regression in general code tasks, tool reliability, security or runtime resource use.

## Roadmap, decisions, risks, and implementation prompts

### Prioritized roadmap

**Foundation milestone — preserve 0.1, create the research kernel.** Keep the Python 0.1 contract untouched. Define a Rust workspace for the experimental core, event schema, model-provider trait, repository snapshot abstraction and benchmark runner. Treat PR #18 as a laboratory source of ideas rather than the release path. [PR #18][pr18]

**Measurement milestone — repository intelligence and TinyBuilder Bench.** Implement lexical search, Tree-sitter PHP symbols, Composer-aware dependency hints, token-budgeted repository maps and disposable worktrees. Create the first 30–50 real Laravel tasks with hidden executable tests. Benchmark unmodified candidate models before any training. This is the highest-priority milestone because `AGENTS.md` itself identifies repeatable worktree/Pest/PHPUnit evaluation as the next engineering target. [AGENTS.md][agents]

**Safe coding milestone — typed edits and verification.** Add content-hash-bound patch proposals, per-action approvals, exact command capabilities, automatic diff review and targeted verifier scheduling. Do not expose unrestricted shell as the primary model API.

**Laravel milestone — ecosystem plugin and Boost.** Implement Laravel detection, structural retrieval hints, verifier discovery and optional Boost MCP integration. Boost supplies valuable version-aware docs and project tools, but TinyBuilder remains usable without it. [Boost documentation][boost]

**Knowledge/security milestone — web, MCP and injection tests.** Add ephemeral search/docs provider traits, MCP trust profiles, secret/network boundaries and a hostile-content benchmark. Treat MCP skill/tool text as untrusted as required by current MCP security guidance. [MCP Skills Extension][mcpskills]

**Specialization milestone — 1.5B QLoRA.** Only after failure analysis exists, build a small verified trajectory set and specialize Qwen2.5-Coder-1.5B or the best 1.5B-class model identified by then. Compare against the untouched base under identical runtime conditions. QLoRA is the appropriate first memory-efficient method. [QLoRA][qlora]

**Quality milestone — 3B/4B and execution rewards.** If the 1.5B model remains below the product threshold, benchmark/tune Granite 4.2-3B and the best current 4B candidate. Experiment with executable-reward reinforcement learning only when the verifier is demonstrably stable. SWE-Master and CodeRL support the concept, but their reported gains should not be extrapolated to TinyBuilder without reproduction. [SWE-Master][swemaster] · [CodeRL][coderl]

**UX milestone — thin Ratatui product.** Add a TUI only after the headless benchmark harness can solve tasks. A beautiful UI around an unreliable agent would slow research and make behavior harder to isolate.

### Adopt, adapt, build, reject

| Decision | Technology / idea | Reason |
|---|---|---|
| **Adopt** | llama.cpp | Local CPU/CUDA/hybrid inference directly fits 4 GB VRAM hardware. [llama.cpp][llama] |
| **Adopt** | Tree-sitter | Fast embedded structural parsing. [Tree-sitter][treesitter] |
| **Adopt** | LSP as optional semantic layer | Definitions/references/diagnostics complement syntax retrieval. |
| **Adopt** | Git worktrees | Cheap isolation and deterministic benchmark reset. |
| **Adopt** | MCP protocol | Ecosystem interoperability, but only behind TinyBuilder permissions. |
| **Adopt** | QLoRA/PEFT-style adapters | Highest practical tuning leverage on limited VRAM. [QLoRA][qlora] |
| **Adapt** | Aider repo map | Token-budgeted symbol graph, reimplemented independently for TinyBuilder. [Source][aidermap] |
| **Adapt** | mini-swe-agent simplicity | Small control loop and bounded outputs, not unrestricted Bash. [Configuration][miniconfig] |
| **Adapt** | Agentless | Fixed localization/repair/validation benchmark baseline, not product workflow. [Paper][agentless] |
| **Adapt** | SWE-smith | Executable synthetic task creation for PHP/Laravel. [Project][swesmith] |
| **Adapt** | SWE-Master | Verified trajectories, LSP and execution feedback, not its 32B-scale recipe wholesale. [Project][swemaster] |
| **Adapt** | workflow-SLM | Narrow stable micro-skills/protocol research, not entire coding behavior. |
| **Adapt** | little-coder | Skills/context/tool-harness concepts only after independent validation. |
| **Build ourselves** | Rust adaptive controller | TinyBuilder's core differentiator. |
| **Build ourselves** | Permission/taint model | Must match product threat model, not third-party defaults. |
| **Build ourselves** | Laravel retrieval graph | Framework conventions are a product advantage. |
| **Build ourselves** | Typed patch engine | Critical safety and model-reliability boundary. |
| **Build ourselves** | TinyBuilder Bench | Existing benchmarks do not test the intended product envelope. |
| **Build ourselves** | Plugin API | Prevent Laravel specialization from contaminating generic core. |
| **Reject** | 200–500 MB resident-memory target | Confuses weight storage with system memory and encourages under-capable models. [AGENTS.md][agents] · [llama.cpp memory guidance][llamamemory] |
| **Reject** | Training a transformer from scratch | Poor compute/data economics versus adapting a pretrained model. |
| **Reject** | Arbitrary prose/fenced-JSON action parsing | Already identified as unreliable and unsafe. [AGENTS.md][agents] · [Repository][repo] |
| **Reject** | Unrestricted shell as primary weak-model tool | Excessive action space and privilege. |
| **Reject** | Mandatory vector database | Added RAM/complexity without evidence it beats lexical/structural retrieval. |
| **Reject** | Mandatory cloud inference/search | Violates free/local-first core objective. |
| **Reject** | Persisting web/MCP/transcripts | Conflicts with explicit project privacy boundary. [AGENTS.md][agents] |
| **Reject/defer** | Multi-agent swarm | Large token/runtime overhead with no demonstrated need. |
| **Reject/defer** | Desktop-first architecture | Higher maintenance and memory before core reliability is proven. |

### Principal technical risks

The largest risk is **mistaking harness progress for model intelligence**. A constrained benchmark can accidentally encode the solution through file hints, replacement-line hints or narrow repair templates. PR #20 explicitly recognizes this issue by noting the current fixtures remain narrow. [PR #20][pr20] Future tasks should withhold edit locations and independently score final behavior.

The second risk is **benchmark contamination**. Popular open repositories and standard coding datasets may have appeared in model training. TinyBuilder should emphasize newly constructed or substantially held-out Laravel tasks and split by repository rather than random task row.

The third risk is **over-specialization**. Training too heavily on Laravel tool traces can make the model excellent at one harness syntax and worse at reasoning about ordinary PHP or unfamiliar ecosystems. Maintain a general-code regression suite throughout training.

The fourth is **tool-use overfitting**. A model can learn to emit syntactically perfect tool JSON without choosing the right tool. Track selection correctness separately from parse validity.

The fifth is **silent security regression**. Agent benchmarks reward completing tasks, which can incentivize increasingly aggressive execution. Permission correctness and prompt-injection resistance need first-class pass/fail tests, not optional qualitative review.

The sixth is **optimizing context window instead of context quality**. A 128K or 262K advertised context does not mean consumer hardware should use it. KV cache growth and latency make disciplined retrieval more important on the target system. llama.cpp explicitly documents context/KV memory pressure. [llama.cpp memory guidance][llamamemory]

The seventh is **training-compute optimism**. QLoRA reduces memory, but 4 GB remains highly constrained. TinyBuilder should not announce that 3B/7B training is practical until a measured, reproducible run exists.

The eighth is **licensing/data provenance debt**. Model license, base model license, adapter dataset license, synthetic teacher terms and source-repository license are separate questions. A permissively licensed output checkpoint does not cure incompatible training inputs.

### Concrete local Codex implementation prompts

The following prompts are intentionally scoped so a local coding agent can implement research pieces without rewriting the 0.1 release.

#### Benchmark harness

```text
You are working on TinyBuilder's experimental Rust research track.

Objective:
Implement a model-agnostic executable benchmark harness for Laravel/PHP coding tasks.

Constraints:
- Do not modify the behavior or public contract of the existing TinyBuilder 0.1 Python release.
- Work only in the experimental/research Rust area.
- Do not download models, call paid services, or require network access in tests.
- Tests must run model-free with fixtures/fakes.
- Every benchmark run must use a disposable Git worktree or equivalent disposable copy.
- Never score exact patch text as the primary success criterion.

Design:
1. Define a BenchmarkTask manifest containing:
   repo/base commit, task text, allowed capabilities, public commands,
   hidden verifier commands, turn/context limits, tags and expected security policy.
2. Define structured BenchmarkResult and failure categories:
   reasoning, retrieval, protocol, patch, verifier, permission, environment.
3. Run setup, agent invocation and verification as separate phases.
4. Capture wall time, peak process RAM when available, tool counts and context/token fields.
5. Preserve no source contents in telemetry by default.
6. Ensure cleanup occurs after failures.
7. Add fixture tasks using tiny synthetic PHP projects; no PHP installation should be required for unit tests.

Deliver:
- Rust types and modules.
- Unit/integration tests.
- A short design document explaining reproducibility and hidden-test separation.
- No production CLI wiring yet.
```

#### Repository intelligence

```text
Implement TinyBuilder's token-budgeted repository intelligence layer in Rust.

Do not copy Aider source. Reimplement the design independently.

Requirements:
- Respect .gitignore and configurable exclusions.
- Build a file inventory.
- Provide deterministic lexical search.
- Add a parser abstraction with Tree-sitter-compatible symbol records.
- For PHP fixtures, extract namespaces, classes, interfaces, traits,
  methods, functions, imports and source ranges.
- Build lightweight edges for definition/reference/import relationships.
- Define RepoMap rendering with a hard token/character budget.
- Ranking must be deterministic and accept task query terms and already-selected files.
- Do not add embeddings yet.
- The API must permit a future LSP enrichment layer without requiring LSP now.
- Detect stale file snapshots with content hashes.

Tests:
- ranking changes when task terms identify a symbol;
- output never exceeds configured budget;
- ignored/vendor files are excluded;
- malformed PHP still produces useful partial records where parser support allows;
- same inputs produce byte-identical map output.

Do not touch TinyBuilder 0.1 behavior.
```

#### Safe patch and permission kernel

```text
Build the experimental Rust permission and patch-application kernel.

Security requirements:
- Permissions are capabilities: read, write, exec, network, MCP.
- Write and exec are denied by default.
- A granted capability must never imply another capability.
- Approval binds to exact normalized paths / argv / working directory / snapshot revision.
- Resolve symlinks before enforcing project-root boundaries.
- Refuse stale patches if source hashes differ.
- Apply edits atomically and return a structured diff.
- Never execute shell text implicitly; command actions use argv arrays.
- Provide a separate high-risk/destructive command classification hook.
- External evidence cannot alter permission state.

Implement:
PermissionPolicy, Capability, Approval, Snapshot, PatchProposal,
PatchResult, CommandProposal, PolicyDecision.

Add adversarial tests for:
path traversal, symlink escape, stale patches, shell metacharacters,
approval replay, command argument mutation, and untrusted text that
contains fake permission instructions.

No UI and no real command execution are required in this change.
```

#### Laravel ecosystem plugin

```text
Implement a Laravel ecosystem plugin behind a generic EcosystemPlugin interface.

The generic Rust core must not import Laravel-specific types.

Laravel detection:
- composer.json contains Laravel/framework or recognizable Laravel packages;
- artisan exists;
- collect installed package constraints from composer.lock when available;
- detect Pest/PHPUnit, Pint, PHPStan/Larastan and Boost without assuming they exist.

Repository hints:
- routes → controllers;
- models → migrations/factories/policies where discoverable;
- tests → tested classes/routes;
- Blade/Livewire component relationships where deterministic evidence exists.

Verifier planning:
- php -l for changed PHP files;
- project-configured Pint/PHPStan/Larastan;
- targeted Pest/PHPUnit;
- optional broader suite.
Return command proposals only; never execute directly.

Boost:
- represent Laravel Boost as an optional MCP/docs capability.
- Missing Boost must degrade gracefully.
- No network or MCP calls in tests.

Add Laravel fixture repositories and model-free tests.
Do not modify the 0.1 release.
```

#### Model protocol qualification

```text
Implement a model-provider and action-protocol qualification harness.

Providers:
- generic OpenAI-compatible local endpoint interface;
- no mandatory Ollama-specific logic;
- leave room for direct llama.cpp integration.

Action protocols:
1. native tool calling;
2. strict TinyBuilder JSON envelope;
3. constrained JSON/schema mode when the provider advertises support.

Rules:
- Never extract fenced JSON or JSON substrings from prose.
- Reject duplicate keys, unknown actions, extra privileged fields,
  invalid argument types and oversized outputs.
- Parsing success and semantic tool-choice correctness are separate metrics.
- A model/protocol combination is 'qualified' only after benchmark thresholds,
  never merely because one smoke test succeeds.

Create a fake provider that emits malformed, fenced, mixed-prose,
duplicate-key and correct responses.
Write exhaustive fail-closed tests.
No live model downloads or network tests.
```

#### Adaptive controller and bounded context

```text
Build a minimal adaptive TinyBuilder agent controller.

The controller is NOT a fixed workflow engine.

Responsibilities:
- maintain bounded session state;
- ask the model to select among currently exposed tools;
- dynamically expose only tools relevant to the current state;
- enforce token/context budgets;
- compact old observations into structured factual summaries;
- never summarize away unresolved verifier failures or permission decisions;
- permit retrieval after a failed patch;
- stop on success, explicit model final, budget exhaustion or policy failure.

The model decides hypotheses and which evidence it needs.
The controller decides permissions, freshness, execution and verification truth.

Add deterministic fake-model tests showing:
- retrieve → patch → verify success;
- retrieve → patch → failing test → new evidence → revised patch;
- malformed action recovery;
- permission denial;
- context-budget compaction;
- infinite-loop prevention.

Keep the implementation small and observable.
```

#### TUI and measurement layer

```text
After the headless research core passes its benchmark tests, implement a thin
Ratatui/Crossterm interface over the existing event stream.

Views:
- task composer;
- current model/runtime;
- repository/context budget;
- evidence/tool timeline;
- proposed patch diff;
- exact approval dialog;
- verifier/test results;
- final result.

Rules:
- no agent policy in UI code;
- closing the TUI must not corrupt session/worktree state;
- approval displays exact paths/argv and risk classification;
- do not render source contents into telemetry/log files;
- support Windows terminal behavior explicitly.

Also expose the same event stream to a headless CLI so benchmark automation
does not depend on the TUI.
```

The end-state this roadmap aims for is deliberately different from both “a tiny chatbot with tools” and “a giant autonomous IDE agent.” TinyBuilder's strongest plausible niche is a **measured, compact coding system whose model is small because deterministic software handles everything that does not require learned reasoning**. A 1.5B model that receives the correct symbols, a constrained set of actions, trustworthy test feedback and current Laravel documentation can be far more useful than its raw parameter count suggests; but where 1.5B remains inadequate, the architecture should permit a 3B or 4B model without redesigning the product. The benchmark—not the desired download size—should decide that boundary. [AGENTS.md][agents] · [VISION.md][vision] · [llama.cpp memory guidance][llamamemory]

---

## Source links and research limitations

The inline reference-style links above are standard Markdown. The following additional sources were surfaced during the original research; they are provided as leads, not as claims of independent replication or exhaustive source audits.

- [OpenCode](https://github.com/anomalyco/opencode) — relevant comparison requested; no detailed independent evaluation was presented in the original report.
- [Agentless experimental instructions](https://github.com/OpenAutoCoder/Agentless/blob/main/README_swebench.md)
- [SWE-World](https://github.com/RUCAIBox/SWE-World) and [data preparation](https://github.com/RUCAIBox/SWE-World/blob/main/data_preparation/README.md)
- [SWE-bench experiments](https://github.com/SWE-bench/experiments)
- [QLoRA implementation](https://github.com/artidoro/qlora)
- [Curriculum Learning for Small Code Language Models](https://www.alphaxiv.org/abs/2407.10194)
- [StarCoder2-3B model card](https://huggingface.co/bigcode/starcoder2-3b)
- [Qwen3-4B license](https://huggingface.co/Qwen/Qwen3-4B/blob/main/LICENSE)
- [Qwen3-4B-Instruct-2507](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- [Qwen2.5-Coder-1.5B base](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B)
- [DeepSeek-Coder-1.3B-Instruct](https://huggingface.co/deepseek-ai/deepseek-coder-1.3b-instruct)
- [Maincoder-1B](https://huggingface.co/Maincode/Maincoder-1B)
- [llama.cpp feature matrix](https://github.com/ggml-org/llama.cpp/wiki/Feature-matrix)
- [llama.cpp quantization](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md)
- [Laravel Boost repository](https://github.com/laravel/boost)
- [Laravel testing](https://laravel.com/framework/docs/13.x/testing), [Pint](https://laravel.com/framework/docs/pint), [PHPStan](https://phpstan.org/), [PHPStan extension library](https://phpstan.org/user-guide/extension-library)
- [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/index.mdx), [security policy](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/SECURITY.md), [tool annotation limitations](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/)
- [Ratatui Windows FAQ](https://ratatui.rs/faq/), [Rust cross-compilation](https://github.com/rust-lang/rustup/blob/main/doc/user-guide/src/cross-compilation.md), [Tauri app size](https://v2.tauri.app/concept/size/)

The original report does not establish an exhaustive licensing audit, a quantitative head-to-head PHP/Laravel model ranking, actual memory/latency/energy measurements on the target PC, or a demonstrated 4 GB training run. It does not settle all requested questions about 100M-scale models, multi-model routing, curriculum learning, or OpenCode implementation details. These are open research questions, not evidence that these approaches fail. The incomplete research-tree inspection limitation above remains in force. Check exact model/runtime support, source revisions and licenses before adoption.

[agents]: https://github.com/MrPunyapal/TinyBuilder/blob/main/AGENTS.md
[vision]: https://github.com/MrPunyapal/TinyBuilder/blob/research/workflow-slm-lab/docs/VISION.md
[repo]: https://github.com/MrPunyapal/TinyBuilder
[pr18]: https://github.com/MrPunyapal/TinyBuilder/pull/18
[pr20]: https://github.com/MrPunyapal/TinyBuilder/pull/20
[qwen15]: https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct?local-app=docker-model-runner
[qwen15gguf]: https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF?hardware=l20
[granite]: https://huggingface.co/ibm-granite/granite-4.2-3b
[granitereadme]: https://huggingface.co/ibm-granite/granite-4.2-3b/blob/main/README.md
[qwen35]: https://huggingface.co/Qwen/Qwen3.5-4B?library=transformers
[qwen35readme]: https://huggingface.co/Qwen/Qwen3.5-4B/blame/main/README.md
[phi]: https://huggingface.co/microsoft/Phi-4-mini-instruct?library=transformers
[phireadme]: https://huggingface.co/microsoft/Phi-4-mini-instruct/blob/main/README.md
[phipinned]: https://huggingface.co/microsoft/Phi-4-mini-instruct/blob/5e185593ed95c2f37ffc4e75da4411ca296271d2/README.md?code=true
[qwen3b]: https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct
[qwen05]: https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct
[deepseeklicense]: https://huggingface.co/deepseek-ai/deepseek-coder-1.3b-instruct/blob/main/LICENSE
[llamamemory]: https://github.com/ggml-org/llama.cpp/blob/master/docs/multi-gpu.md
[llama]: https://github.com/ggml-org/llama.cpp?ref=proaitools
[llamaserver]: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md?plain=1
[llamabuild]: https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
[aidermap]: https://github.com/Aider-AI/aider/blob/main/aider/repomap.py
[aiderdocs]: https://github.com/Aider-AI/aider/blob/main/aider/website/docs/repomap.md
[mini]: https://github.com/SWE-agent/mini-swe-agent
[miniconfig]: https://github.com/swe-agent/mini-swe-agent/blob/main/src/minisweagent/config/mini.yaml
[agentless]: https://arxiv.org/abs/2407.01489
[openhands]: https://arxiv.org/abs/2407.16741
[openhandsiclr]: https://proceedings.iclr.cc/paper_files/paper/2025/hash/a4b6ad6b48850c0c331d1259fc66a69c-Abstract-Conference.html
[swesmith]: https://github.com/SWE-bench/SWE-smith
[swesmithreadme]: https://github.com/SWE-bench/SWE-smith/blob/main/README.md
[swemaster]: https://github.com/RUCAIBox/SWE-Master
[coderl]: https://arxiv.org/abs/2207.01780
[coderlcode]: https://github.com/salesforce/CodeRL/blob/main/README.md
[qlora]: https://arxiv.org/abs/2305.14314
[workflow]: https://github.com/arpitbbhayani/workflow-slm
[littlecoder]: https://github.com/itayinbarr/little-coder
[littlearchitecture]: https://github.com/itayinbarr/little-coder/blob/main/docs/architecture.md
[boost]: https://laravel.com/framework/docs/boost
[boost12]: https://laravel.com/framework/docs/12.x/boost
[laravelai]: https://laravel.com/framework/docs/12.x/ai
[boostannouncement]: https://laravel.com/blog/announcing-laravel-boost
[treesitter]: https://tree-sitter.github.io/tree-sitter/?from_theconsensus=1
[treesitterimpl]: https://tree-sitter.github.io/tree-sitter/5-implementation.html
[lsp]: https://microsoft.github.io/language-server-protocol/
[peft]: https://huggingface.co/docs/peft/main/conceptual_guides/lora
[peftquant]: https://huggingface.co/docs/peft/main/developer_guides/quantization
[unsloth]: https://github.com/unslothai/unsloth/
[soup]: https://github.com/paulbrett/soup
[soupdocs]: https://github.com/bossadvisors/soup/blob/main/docs/training.md
[colab]: https://research.google.com/colaboratory/faq.html
[kaggle]: https://www.kaggle.com/docs/notebooks
[searxng]: https://github.com/searxng/searxng
[searxlicense]: https://github.com/searxng/searxng/blob/master/LICENSE
[mcpskills]: https://skills.extensions.modelcontextprotocol.io/specification/beta/skills
[mcpcsharp]: https://csharp.sdk.modelcontextprotocol.io/v2/concepts/skills/skills.html
[ratatui]: https://ratatui.rs/
[ratatuiinstall]: https://ratatui.rs/installation/
[tauri]: https://v2.tauri.app/start/
[tauriarchitecture]: https://v2.tauri.app/concept/architecture/
[swebench]: https://github.com/swe-bench/SWE-bench
[swebenchfaq]: https://github.com/SWE-bench/SWE-bench/blob/main/docs/faq.md
