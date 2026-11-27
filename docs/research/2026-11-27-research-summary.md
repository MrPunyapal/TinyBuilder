# TinyBuilder deep research — executive summary

Date: 2026-11-27  
Status: Proposed research direction; not a release specification or approved training plan.  
Full evidence and limitations: [Complete deep research report](2026-11-27-deep-research.md).  
Execution plan: [Implementation roadmap](2026-11-27-implementation-roadmap.md).

See the [maintainer decisions](2026-11-27-coding-v1-decisions.md) for the accepted direction and the approval scope of this documentation PR.

## Executive decision

Build a small-model amplifier, not a model-size demonstration: a lightweight Rust coding harness, initially Laravel-first, that gives a local 1.5B–4B model compact repository evidence, a constrained action space, trustworthy executable feedback and version-aware documentation. Choose the smallest model that meets measured functional and safety thresholds, not the smallest downloadable file. The normal native read-only 0.1 release remains independent; the Python and mutation examples are reference/lab only.

The TUI is the preferred first interface, but headless engineering and evaluation precede product UX. The product must remain free to use locally without a paid inference or search subscription.

## Evidence and confidence

| Classification | Finding | Implication |
|---|---|---|
| Verified repository guidance | [AGENTS.md](https://github.com/MrPunyapal/TinyBuilder/blob/main/AGENTS.md) separates weights, memory, runtime and live documentation; requires opt-in writes and commands, transient remote content, cheap model-free CI, and executable benchmarking before training. | Preserve the existing safety and release boundaries. |
| Verified PR metadata | [PR #18](https://github.com/MrPunyapal/TinyBuilder/pull/18) is a lab-only evidence-bound patch proposal experiment; [PR #20](https://github.com/MrPunyapal/TinyBuilder/pull/20) is stacked research with narrow single-line cross-file fixtures. | Reuse validated ideas; do not market smoke tests as general multi-file competence. |
| Repository-reported result | Stock Qwen2.5-Coder 0.5B/1.5B/3B Ollama tags produced zero native tool calls in the recorded experiment. [Repository](https://github.com/MrPunyapal/TinyBuilder) | Qualify model + chat template + runtime + protocol together. This does not establish that the existing native read-only gate failed. |
| Publisher-reported results | [Agentless](https://arxiv.org/abs/2407.01489) reported 32% SWE-bench Lite at publication; [SWE-Master](https://github.com/RUCAIBox/SWE-Master) reported 61.4% Pass@1 SWE-bench Verified with a 32B model; [SWE-smith](https://github.com/SWE-bench/SWE-smith) provides roughly 52,000 tasks. | Learn from executable benchmarks, data generation and simpler controls; do not extrapolate scores to TinyBuilder. |
| Arithmetic estimate | Four-bit payload is approximately 0.5 bytes/parameter, before overhead. A 1.5B model has a theoretical 0.75 GB raw payload; a 3B model 1.5 GB; a 4B model 2 GB. | A 200–500 MB weight file is plausible at smaller scales; that is not a total resident memory budget or evidence of coding competence. |
| Engineering hypothesis | 1.5B Q4 is the easiest initial target on the i7/16 GB RAM/RTX 3050 4 GB VRAM PC; 3B/4B may benefit from hybrid offload. | Measure, do not promise throughput, energy or fit. |
| Proposed decision | Prioritize lexical/AST retrieval, typed patching, executable verification and a benchmark before training. | Attribute failures before spending compute. |

## Ranked qualification candidates (proposed, not measured)

1. [Granite 4.2-3B](https://huggingface.co/ibm-granite/granite-4.2-3b): quality-tier candidate; publisher documents tool calling, but PHP ability and pinned local backend support need testing.
2. [Qwen2.5-Coder-1.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct): primary low-memory baseline and first possible specialization base; official [GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF).
3. [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B): quality ceiling/hybrid reference.
4. [Phi-4-mini-instruct](https://huggingface.co/microsoft/Phi-4-mini-instruct): 3.8B MIT-licensed cross-family reference.
5. [Qwen2.5-Coder-0.5B](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct): ultra-light micro-specialist/control.
6. [DeepSeek-Coder-1.3B](https://huggingface.co/deepseek-ai/deepseek-coder-1.3b-instruct): older control; custom license merits review.
7. 7B-class coding models: upper-bound reference only, not the initial default.

Qwen2.5-Coder-3B is not a default recommendation because of its distinct [license](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct). Verify checkpoint terms, runtime support, redistribution conditions and benchmark scores before any selection. Keep the established 0.1 model gate unchanged.

## Priorities

- **P0 — Measurement:** inventory existing Rust lab work; preserve original oracles; implement independent executable scoring in disposable worktrees. Start with 30–50 validated tasks, expand to 60–100 across repository-held-out splits. Separate supplied-evidence from retrieved-evidence arms, parsing from semantic tool choice, and environmental failures from model failures.
- **P1 — Harness:** adapt [Aider's repo-map concept](https://github.com/Aider-AI/aider/blob/main/aider/repomap.py), use [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) and optional [LSP](https://microsoft.github.io/language-server-protocol/); use [llama.cpp](https://github.com/ggml-org/llama.cpp) for CPU/GPU/hybrid inference. Keep the controller adaptive, with deterministic budgets and small tool menus.
- **P1 — Safety:** content-hash-bound proposals, explicit approval, exact argv, worktree confinement, real process containment where available; deny unauthorized writes, exec, network and MCP actions independently. No arbitrary prose/fenced-JSON parsing. A worktree is not an OS sandbox.
- **P1 — Laravel plugin:** detect Composer/package versions and framework relationships; discover Pest/PHPUnit, Pint, PHPStan/Larastan; make [Boost](https://laravel.com/framework/docs/boost) optional. Keep generic core free of Laravel-specific types.
- **P2 — Knowledge:** local package source first; version-aware docs second; optional self-hosted or user-specified search and [MCP](https://github.com/modelcontextprotocol/modelcontextprotocol). Keep remote evidence transient and untrusted. Do not require cloud accounts or paid services.
- **P2 — Specialization:** only with failure evidence, try [QLoRA](https://arxiv.org/abs/2305.14314) on a verified trajectory dataset. Benchmark the untouched base and adapters under identical held-out conditions. Consider continued PHP pretraining, licensed distillation and executable-reward RL only when simpler interventions demonstrably fail.
- **P3 — UX:** [Ratatui](https://ratatui.rs/) / Crossterm thin TUI over the headless event stream, separately consented models and platform acceptance for Windows x64, macOS ARM64 and Linux x64. Desktop via Tauri only if measured user needs justify it.

## Approaches to avoid

No from-scratch transformer training on the target PC; no arbitrary fixed workflow executor, mandatory embeddings/vector database, unrestricted Bash, mandatory cloud inference, permanent web/MCP/transcript storage, desktop-first rewrite or multi-agent swarm. Defer pruning/QAT, RL and multi-model routing until their benefits are independently demonstrated. Do not optimize only syntax-valid tool calls or exact patch matches, allow benchmark test leakage, or treat tool annotations as permission grants.

## Unresolved limitations

The complete report records intermittent access to the full research-branch document tree. Source/license reviews are not exhaustive; no live model, Laravel execution, memory/latency/energy or training measurements were made during Deep Research. Its candidate ranking is qualitative. Neither the claimed 200–500 MB agent nor the ability to train 3B–7B models on a 4 GB GPU is established. OpenCode, 100M-scale models, curriculum and routing require additional targeted research if they become decision-critical. No new release, model download, paid compute or training is authorized by these documents.

**Next action:** reconcile the existing local Codex implementation with the roadmap, obtain exact-head benchmark evidence and preserve failures. Do not open a competing implementation branch simply because this documentation PR exists.
