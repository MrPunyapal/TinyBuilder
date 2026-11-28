# TinyBuilder Deep Research Phase 4 — Intelligence Beyond Parameter Count

Research: 2026-11-27. Evidence reassessment: 2026-11-28. Archival: 2026-11-28.

Scope: research, architecture, experimental design and engineering roadmap for local 1.5B–3B coding models on approximately 16 GB RAM and 4 GB VRAM. [Repository](https://github.com/MrPunyapal/TinyBuilder).

This archive preserves the original Phase 4 findings and subsequent evidence reassessment in chronological order. Interactive charts and diagrams are represented as Markdown tables or text diagrams; implementation prompts, detailed experiments and acceptance criteria are also preserved in the companion [roadmap](2026-11-27-repository-intelligence-roadmap.md) and [ablation plan](2026-11-27-intelligence-ablation-plan.md). The original research conclusions are historical, and Part II supersedes their sequencing where the new evidence warrants it. This is an accepted research direction, not qualification, permission to execute generated code, or approval of individual numerical thresholds.

Evidence conventions: repository facts are direct read-only observations of pinned remote code or metadata; measurements are repository-reported local results, not reruns; initial ranking reproduction was user-reported; external study results are author-reported from the original research; engineering proposals and illustrations are hypotheses, not measurements. Source links are ordinary Markdown hyperlinks. No exact comparison of external benchmark scores with TinyBuilder is implied.

# Part I — Original research (November 27)

## 1. Executive conclusion

Prioritize the intelligence of the complete coding system, rather than immediately increasing the intelligence or parameter count of the language model. The repository retrieval system prevents most tasks from reaching inference, while earlier experiments show the 1.5B can still struggle with editing when given correct evidence. These are distinct problems. Training to compensate for broken retrieval would be premature; fixing retrieval alone would not establish coding competence.

Build a lightweight evidence-driven coding engine in Rust: the model makes semantic decisions; deterministic software handles navigation, evidence collection, mechanical transformations, resource management and verification.

| Direction | Original research decision |
|---|---|
| Lexical retrieval | Immediate priority |
| Structural repository understanding | High priority |
| Deterministic reasoning and editing tools | High priority |
| Adaptive inference and candidate selection | Controlled experiments |
| Verifier-guided repair | After containment qualification |
| Embeddings and semantic models | Conditional |
| Larger model downloads | Deferred |
| Training and distillation | Deferred |

## 2. Repository audit and experimental evidence

Main at inspection: [ce28337552933a671a95d1ad30baa07cfe7cc2b7](https://github.com/MrPunyapal/TinyBuilder/commit/ce28337552933a671a95d1ad30baa07cfe7cc2b7). Measurement commit: [0fab9c6ae2b94dfb514287ded6275e72fadadcb9](https://github.com/MrPunyapal/TinyBuilder/commit/0fab9c6ae2b94dfb514287ded6275e72fadadcb9).

Read the repository's [AGENTS.md](https://github.com/MrPunyapal/TinyBuilder/blob/ce28337552933a671a95d1ad30baa07cfe7cc2b7/AGENTS.md), [agent guide](https://github.com/MrPunyapal/TinyBuilder/blob/ce28337552933a671a95d1ad30baa07cfe7cc2b7/docs/AGENT_GUIDE.md), [dated project status](https://github.com/MrPunyapal/TinyBuilder/blob/ce28337552933a671a95d1ad30baa07cfe7cc2b7/docs/PROJECT_STATUS.md), [original deep research summary](2026-11-27-research-summary.md), [original roadmap](2026-11-27-implementation-roadmap.md), [model specialization summary](2026-11-27-model-specialization-summary.md), [model specialization roadmap](2026-11-27-model-specialization-roadmap.md), [exact retrieval ablation](2026-11-27-exact-retrieval-ablation.md), [native context implementation](https://github.com/MrPunyapal/TinyBuilder/blob/ce28337552933a671a95d1ad30baa07cfe7cc2b7/rust/src/context.rs), grounded lab excerpts and [public proposal measurement report](https://github.com/MrPunyapal/TinyBuilder/blob/0fab9c6ae2b94dfb514287ded6275e72fadadcb9/docs/research/2026-11-27-public-proposal-measurements.md) with [sanitized measurements](https://github.com/MrPunyapal/TinyBuilder/blob/0fab9c6ae2b94dfb514287ded6275e72fadadcb9/benchmarks/results/2026-11-27-public-proposals.json).

The public corpus has 12 tasks and 87 planned semantic observations. Runtime b12359, existing Qwen2.5-Coder 1.5B and research-only 3B Q4_K_M, CPU sequential matched runs, explicit 4,096-token context. The developer PC has i7-12700H, 15.63 GiB physical RAM and 4 GiB RTX 3050.

| Model / context | Review-ready / planned | Actual inference calls | Startup | Prompt / completion tokens | Proposal latency | Sampled combined peak RAM |
|---|---:|---:|---:|---:|---:|---:|
| 1.5B / default | 1/12 | 1 | 3.36 s | 217/72 | 4.88 s | 2.49 GiB |
| 1.5B / 4096 | 1/12 | 1 | 1.75 s | 217/72 | 5.32 s | 1.72 GiB |
| 3B / 4096 | 1/12 | 1 | 4.31 s | 217/72 | 12.81 s | 3.29 GiB |

For each run, 11 tasks stopped before inference because selective retrieval returned no qualifying files. Only group_inventory retrieved its allowed complete source file (1/12 task and 1/14 allowed target-path recall). Zero patches were applied and zero behavioral observations were attempted. The result does not establish equal coding ability, a 1/12 semantic success rate or zero correct repairs; it establishes a blocked comparison. Initial available RAM was 4,042 and 4,046 MiB for the matched pair; GPU pre/post readings reported 0 MiB and 0% utilization, not a continuous GPU peak measurement. No weights, source files or runtime manifests changed in those experiments.

### Preliminary ranking reproduction

| Strategy | Complete task recall |
|---|---:|
| Existing selective | 1/12 (8.3%) |
| Lower threshold | 6/12 (50%) |
| Expanded case-insensitive lexical | 11/12 (91.7%) |

This is an elevenfold increase in complete-recall tasks, not an elevenfold increase in intelligence or correctness. At this point the reproduction was user-reported and needed formal Rust replication on a frozen corpus, with evaluator target-file metadata inaccessible to the retriever.

### Retrieval is not the whole problem

Earlier [exact-text retrieval ablation](2026-11-27-exact-retrieval-ablation.md) on three narrow fixtures retained both required files in all twelve trials.

| Metric | Baseline lexical | Selective lexical |
|---|---:|---:|
| Required-file recall | 100% | 100% |
| Median prompt tokens | 1,818 | 258 |
| 1.5B successful repairs | 0/3 | 0/3 |
| 3B successful repairs | 3/3 | 3/3 |
| 1.5B median trial latency | 19.75 s | 3.75 s |
| 3B median trial latency | 38.40 s | 9.65 s |

Selective retrieval removed 85.8% of prompt tokens, preserving the six accepted 3B repairs. The 1.5B failed replacement matching four times and exceeded edit scope twice across its six trials. These trials ended before behavioral scoring; they are not evidence that the model's intended repairs were semantically wrong. [Cross-file pilot](2026-11-27-cross-file-validation.md): 1.5B 0/6, research 3B 5/6, single-line edits with cross-file evidence, not general multi-file edits. [Source-ID comparison](2026-11-27-source-id-comparison.md): 18 trials, both models 0/3 with source IDs (all six PHP lint rejections), exact text 3/3 for 3B and 0/3 for 1.5B, operator-selected control 1/3 each; earlier model-selected line representation also failed. The initial blocked source-ID run is retained. Do not rerun unchanged negative experiments or promote their interfaces. [Coding Intelligence v1 experiment](2026-11-27-coding-v1-experiment.md) and [corpus adversarial controls](2026-11-27-corpus-adversarial-controls.md) are supporting evidence, not general qualification.

The central conclusion: separately improve evidence retrieval, reasoning, edit realization and verification. Improvement in one is not evidence of improvement in all four.

## 3. Research findings from existing systems and academic literature

The strongest transferable findings concern locating information, interacting with a repository and evaluating work, not merely parameter count. The following are the originally cited research findings (author-reported, not reproduced).

| Research | Originally reported finding | TinyBuilder application |
|---|---|---|
| [RepoCoder, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.151/) | Iterative retrieval/generation improved the in-file completion baseline by over 10% across reported settings | Repeat targeted retrieval when evidence is insufficient |
| [Agentless, FSE 2025](https://conf.researchr.org/details/fse-2025/fse-2025-research-papers/85/Demystifying-LLM-based-Software-Engineering-Agents) ([preprint](https://arxiv.org/abs/2407.01489)) | Localization, repair, validation pipeline; conference version reported 98/300 SWE-bench Lite | Bounded workflow rather than unrestricted autonomy |
| [SWE-agent, NeurIPS 2024](https://proceedings.nips.cc/paper_files/paper/2024/hash/5a7c947568c1b1328ccc5230172e1e7c-Abstract-Conference.html) | Agent-computer interface design materially affected coding performance | Optimize tools/edit interface for small models |
| [LocAgent, ACL 2025](https://aclanthology.org/2025.acl-long.426/) ([preprint](https://arxiv.org/abs/2503.09089)) | Graph-guided localization reached up to 92.7% file-level accuracy with a fine-tuned 32B model | Deterministic dependency navigation |
| [RepoGraph, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/4a4a3c197deac042461c677219efd36c-Abstract-Conference.html) | Repository-level code graphs investigated as extra context | Compare structural with lexical evidence |
| [T1, ICLR 2026](https://proceedings.iclr.cc/paper_files/paper/2026/hash/776a5f2c7d6dd4b0d83145fc044e2726-Abstract-Conference.html) | Tool-integrated verification let a 1B model outperform an 8B on the reported mathematics benchmark | Delegate objectively verifiable operations; coding transfer unproven |
| [Optimal test-time compute, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b623663fd9b874366f3ce019fdfdd44-Abstract-Conference.html) | Adaptive computation may beat uniform scaling | Allocate extra inference based on difficulty |
| [Self-correction limitations, ICLR 2024](https://proceedings.iclr.cc/paper_files/paper/2024/hash/8b4add8b0aa8749d80a34ca5d941c355-Abstract-Conference.html) | Unassisted self-correction can reduce accuracy | Do not repeatedly reconsider without new evidence |

These studies differ in models, training, tasks and environments. They support experimentation, not a claim that a quantized 1.5B achieves these scores on Laravel. Historical external figures and URLs are retained from the research and were not revalidated during archival; confirm exact publication version, metric, denominator and link before relying on them for qualification.

## 4. Proposed intelligence architecture

Evolve the existing Rust harness, not a new implementation.

~~~
Natural-language task
  -> Repository intelligence (lexical search / AST / dependencies)
  -> Evidence compiler (relevant source, signatures, constraints)
  -> 1.5B–3B local model (hypotheses, semantic decisions, bounded inference)
  -> Deterministic action engine (typed edits, scope, hashes, validation)
  -> Approval and qualified isolated verifier (lint, behavior, regression)
  -> Verified result or abstention
     Failure feedback -> model, bounded retries
~~~

The model should not have to memorize an entire framework, enumerate a filesystem, manually calculate line numbers, resolve every dependency, reproduce unchanged code or infer objective test results. Delegate these to software. The isolated verification step is conditional on approval and qualification.

## 5. Repository understanding and intelligent retrieval

### 5.1 Recall-oriented lexical baseline

The existing context module uses minimum scores of 1 and 10; selective threshold 10 worked on narrow fixtures but failed broader prompts. Absolute thresholds calibrated on three fixtures may not generalize. Start with no model inference, embeddings, vector database or external services.

| Technique | Example or purpose |
|---|---|
| Case-insensitive matching | inventory matches Inventory |
| CamelCase splitting | calculateTotal -> calculate, total |
| Snake-case splitting | contact_channel -> contact, channel |
| Path component matching | app/Services/BillingService.php |
| Exact identifier boost | Favor exact BillingService |
| Rare term weighting | Uncommon domain words |
| BM25 | Term frequency and document length |
| Bounded fallback | Recover plausible evidence when rigid cutoff rejects all |
| Coverage-aware selection | Complementary evidence instead of duplicate matches |

Fallback must not send arbitrary files; unrelated prompts need abstention/clarification. Original priority P0, cheap and evidence-backed. Part II updates this after the measured normalized arm.

### 5.2 Structural symbol index

Consider [Tree-sitter](https://tree-sitter.github.io/tree-sitter/) or a qualified parser. In-memory initial index: relative path/language/content hash; class name/namespace/inheritance; method signature/visibility/source range; interface contracts/implementations; imports and candidate definitions; candidate callers/references; test associations.

Syntax trees do not provide complete PHP semantics: dynamic container binding, magic methods, runtime-generated relationships need separate treatment. Persistent caching later only with invalidation, privacy and policy review.

### 5.3 Dependency-aware graph expansion

Illustrative graph (not a real fixture): CheckoutController calls CheckoutService and CheckoutRequest; service references InventoryService and Order model; associated CheckoutFeatureTest provides behavioral evidence. Start at one hop from initial ranked results; second hop only for unresolved references or missing evidence. Carry edge provenance and confidence (explicit import stronger than naming convention).

Study [Aider repository map](https://aider.chat/2023/10/22/repomap.html) and [implementation](https://github.com/Aider-AI/aider/blob/main/aider/repomap.py): syntax-derived relationships and graph ranking prioritize evidence within a token budget. Adapt the concept, not the full architecture. Part II makes comprehensive graphs conditional.

### 5.4 Laravel-specific knowledge

| Component | Discoverable relationship |
|---|---|
| Routes | Controller methods |
| Controllers | Requests, services, responses |
| Eloquent | Models, migrations, relations, casts |
| Container | Explicit interface bindings |
| Policies | Authorization and model relationships |
| Events | Listeners/subscribers |
| Jobs | Dispatch sites and queue configuration |
| Composer | Namespaces, autoloading, versions |
| Tests | Existing behavior contracts |

Use rules to prioritize search and provide evidence, not hard-code benchmark answers. Keep generic core independent; similar plugins may later support Django, FastAPI, Express, React or Rust.

### 5.5 Query decomposition and vocabulary mismatch

For "Prevent customers from buying more products than are available", repository vocabulary might include stock, quantity, inventory, reserve, available, checkout and order. Normalize original query; search literal terms, paths and identifiers; expand with repository-local vocabulary and discovered symbols; follow relevant dependency relationships; ask the model for short search queries only when deterministic search is insufficient. Generated hypotheses are not facts.

### 5.6 Hybrid semantic retrieval

Lexical + semantic similarity + structural relationships can improve vocabulary matching, but embeddings add weights, indexing, memory and maintenance. Implement/improve lexical first, compare BM25, then consider AST, dependency expansion, repository synonyms. Small embeddings are conditional; neural reranker, external vector database and large mandatory embedding models are not justified. Require incremental held-out recall or behavioral benefit rather than generic search scores.

### 5.7 Concrete original Rust findings

The [original context.rs](https://github.com/MrPunyapal/TinyBuilder/blob/ce28337552933a671a95d1ad30baa07cfe7cc2b7/rust/src/context.rs) keeps four longest query terms, preserves original term casing in term extraction, uses minimum score 10 in selective mode, maximum four files, 12 KiB excerpts per file, and errors when nothing qualifies. These are actual code characteristics; each individual cause required ablation. Word length is a poor relevance proxy (tax, fee, sku, vat, id, qty). Byte caps do not guarantee token limits, and four files may be insufficient for cross-file tasks. Investigate recovery rather than guessing.

## 6. Context compression and information density

A well-selected 2,000-token prompt may be more useful than a noisy 16,000-token prompt; existing results demonstrate compression without recall loss on small fixtures, not a universal optimum. [LLMLingua](https://www.microsoft.com/en-us/research/project/llmlingua/overview/) studies learned prompt compression; lossy compression is risky for exact code edits. Prefer deterministic syntax-aware evidence:

| Level | Content | Purpose |
|---|---|---|
| L0 | Repository structure | Orientation |
| L1 | Names and signatures | Localization |
| L2 | Dependencies and relevant contracts | Cross-file reasoning |
| L3 | Exact source bodies | Editing |
| L4 | Focused diagnostics and test output | Repair |

Fetch exact bodies when a relevant target is chosen; never lose exact source spans used for matching.

Illustrative 4,096-token allocation, not measured optimum: instructions/schema 400, task 250, map 350, exact evidence 1,800, diagnostics/template overhead 272, generation reserve 1,024. Count actual runtime tokenizer and chat template when supported. If evidence cannot fit, decompose or explicitly report insufficient context; do not silently truncate essential source.

## 7. Deterministic reasoning and editing

| Model responsibility | Deterministic counterpart |
|---|---|
| Understand ambiguous business requirements | Locate definitions, callers and dependencies |
| Decide semantic correction | Resolve source range and construct mechanical rename |
| Select evidence and hypotheses | Compare signatures, calculate values, parse package versions |
| Propose operation | Scope, exact match, freshness, structural validation |
| Interpret feedback | Independent evaluator determines actual test results |

User/permission engine authorizes changes. Previous source-ID and line protocols failed; preserve that evidence. Test whether software can handle edit mechanics after a model selects an unambiguous semantic operation, rather than inventing yet another ID scheme. Candidate typed transformations: add/remove import, resolved rename, literal/comparison change, insert argument in known signature, explicit config change, uniquely identified expression replacement. Complex business logic retains general exact-text edits. Test unseen variations; no benchmark-specific shortcuts.

Conceptual actions: search(query), read_symbol(symbol), find_definition(symbol), find_references(symbol), inspect_dependencies(symbol), propose_edit(path, old_text, new_text), request_verification(proposal). These are not implemented commands. Expose only stage-appropriate tools (no mutation in localization). Study [SWE-agent ACI](https://swe-agent.com/0.7/background/aci/). Grammar-constrained decoding may improve valid structure if supported by the pinned runtime; it cannot guarantee semantic appropriateness, safe arguments or correctness.

## 8. Test-time compute and adaptive inference

Spend more useful computation, not merely more tokens. Proposed experimental modes:

| Mode | Calls / cumulative budget | Purpose |
|---|---|---|
| Fast | 1 / 256 generated tokens | Simple well-localized tasks |
| Balanced | Up to 3 / 1,024 generated tokens | Targeted evidence expansion |
| Deep | Up to 6 / 3,072 generated tokens; up to 3 distinct candidates | Ambiguous/cross-file, verification availability dependent |

Modes are subject to context capacity, wall-clock and resource ceilings. Escalate on incomplete/conflicting evidence, unresolved dependency, ambiguous match, plausible alternate locations, static/contract failure or independent behavioral failure, not solely model self-confidence. [Optimal test-time compute](https://proceedings.iclr.cc/paper_files/paper/2025/hash/1b623663fd9b874366f3ce019fdfdd44-Abstract-Conference.html) motivates difficulty-aware allocation.

Candidate sampling illustrative formula: probability at least one correct among k independent samples of success probability p = 1 - (1-p)^k. For p=0.25, k=1/2/3/5/8 gives about 25%, 43.8%, 57.8%, 76.3%, 90.0%, with k times generation work under equal-call cost. This is an illustrative probability model, not measured performance: errors are correlated and selection is separate. Generate sequentially in one runtime, not multiple resident instances.

Candidate selection filters: schema -> scope/hash -> exact match -> structural validity -> existing project tests -> independent hidden score -> regression checks. The first four cannot establish semantic correctness. Among equally verified candidates, small edits and unnecessary changes are tie-breakers; majority vote/model confidence never overrides a failed trusted verifier. Hidden scoring belongs only to the external evaluator, not deployable selection.

## 9. Verifier-guided repair

An initially wrong proposal might become useful given precise external feedback. [T1](https://proceedings.iclr.cc/paper_files/paper/2026/hash/776a5f2c7d6dd4b0d83145fc044e2726-Abstract-Conference.html) provides mathematics evidence; coding needs replication.

Generate -> validate and authorize -> isolated execution -> pass/review, or bounded sanitized diagnostic -> revised candidate -> stop on exhausted budget, duplicate or verified success. Do not overwrite a verified good candidate with a regression. Keep agent-facing diagnostics separate from final hidden tests, reference repairs, private assertions and expected values; avoid leaking answers through repeated feedback. A model-generated test cannot be the sole verifier.

With no qualified evaluator, continue navigation, static analysis, inert previews and source-only metrics. Never execute generated PHP, Composer scripts, project tests containing untrusted changes or other candidate programs on the ordinary host. Worktree, human approval and syntax checks are not OS containment. Phase 3 is the execution dependency; no bypass.

## 10. Agent workflows and reusable skills

Avoid a rigid workflow executor while reducing avoidable decisions. A workflow specifies prerequisite capabilities, allowed tools, evidence needs, call/token limits, termination and verification; model chooses task-specific hypotheses and actions. Skills are compact declarative manifests, not automatically trusted scripts.

| Skill | Evidence focus |
|---|---|
| Repository exploration | Components/dependencies |
| Bug localization | Trace observed failure |
| Laravel validation | Requests/behavior |
| Authorization review | Policies/gates/middleware |
| API modification | Routes/controllers/contracts/callers |
| Database change | Migrations/models/compatibility |
| Refactoring | Behavior preservation |
| Test-guided repair | Authorized diagnostics |

Repository-discovered skills are untrusted data and cannot grant permissions. Avoid default independent planner/architect/coder/reviewer/tester models: redundant inference, context and coordination failures. Start with one resident model reused across phases.

## 11. Recent research noted in the original report

Historical source links and reported results are preserved; no new verification of external scores at archival.

- [Agent Retrieval Bench, July 2026](https://arxiv.org/abs/2607.24882) ([implementation](https://github.com/eyuansu62/agent-retrieval-bench)): reported 427 examples across 25 repositories, including positive, no-useful-evidence and counterfactual controls. Simple score thresholding did not improve selective retrieval success on its natural no-gold subset under repository-grouped cross-validation. Evaluate relevance and abstention separately.
- [Small Agents with Semantic Search, October 2026](https://arxiv.org/abs/2610.05099): compact multilingual localization agents with local semantic retrieval report gains over lexical agents and cross-language transfer. Trained agents, not evidence about existing untouched checkpoints; conditional semantic-search experiment only.
- [CORE-Bench, EMNLP 2026](https://aclanthology.org/2026.emnlp-main.1604/) ([preprint cited in reassessment](https://arxiv.org/abs/2606.11864)): separates understanding, localization and wider supporting context. Edit target is not all necessary evidence.
- [CodeGrep, 2026](https://aclanthology.org/2026.realm-1.80/): original report cited a trained 14B retrieval agent reducing rounds 15% and tokens 19% on resolved cases, overall resolution 25.8% to 27.0%; lower precision can harm downstream results. Do not adopt a 14B retrieval model.
- [TEX, October 2026](https://arxiv.org/abs/2610.27290) ([EMNLP Findings](https://aclanthology.org/2026.findings-emnlp.2190/)): original report cited 86.4% test-generation performance on SWT-Bench Verified, cross-candidate execution of tests and patches; quadratic cost and multi-agent design poor immediate fit.
- [CodeRAG-Bench](https://aclanthology.org/2025.findings-naacl.176/): useful retrieval does not automatically improve generation, especially with limited context or evidence utilization.

Synthesis: measure localization independently, improve recall without irrelevant source, use external tools/verifiers to guide computation, and earn semantic search through measured resource/quality trade-offs. No external benchmark establishes equivalent TinyBuilder capability.

## 12. Controlled original experiments

The complete A–G arm definitions, interpretation and gates appear in the [ablation plan](2026-11-27-intelligence-ablation-plan.md), Part I. The original 12 are development/regression tasks, not general qualification. The research objectives were:

- A: retrieval without inference, one variable at a time (threshold, case, expansion, identifier paths, BM25, AST, dependency and conditional semantic search). Score complete and individual required paths, required spans, precision, delivered tokens, retrieval latency/memory, unrelated queries and paraphrase stability. Original proposed gates 11/12 complete, 13/14 required, no silently truncated essential evidence, at least 90% no-evidence abstention, unchanged 10/10 native read gate and zero unauthorized reads/actions.
- B: existing vs improved lexical vs structural vs human-curated sufficient context (no reference repairs or hidden tests), with distractor and missing-essential-evidence controls. If oracle-context beats retrieval, evidence remains limiting; poor oracle-context isolates downstream bottlenecks, not automatically model reasoning.
- C: distinguish semantic operation from patch realization; compare exact text, deterministic construction, region selection, typed transformations, human operation/model realization and human operation/deterministic realization. Human controls diagnostic, independent reviewer judgments not executable correctness.
- D: density (full files vs exact methods vs signatures/map/framework metadata, controlled distractors), same context capacity. Start 4,096, conditionally 2,048 and 8,192.
- E: single attempt, larger output, three samples, sequential refinement, adaptive equal budget, then verifier-guided repair. Track oracle candidate availability separately from deployable selector.
- F: after containment, compare first attempt with one/two/three feedback repairs; separate syntax, target behavior, regressions, and repair degradation. Stop on verified success, duplicate or exhaustion.
- G: train only after a residual model-attributable bottleneck. Improve retrieval/spans/editing/selection first. No training needed for A–D; inference requires applicable authorization.

## 13. Benchmark methodology and failure attribution

The three existing applications have separate Git histories but share a Laravel skeleton. Lineage splits matter; related mutations must not straddle train/development/held-out splits. Original scale proposal: 12 existing development tasks; 36 expanded across at least six lineages; 60+ independent qualification; 100+ multiple frameworks and task types long term. Include single-file, cross-file, true multi-file, validation, authorization, database, API, refactoring, feature creation and no-safe-change tasks. This scale is provisional, not an approved dataset.

Original funnel per model: 12 planned -> 1 complete target-file recall -> 1 inference -> 1 review-ready -> 0 behavioral evaluations. Behavioral correctness unknown. The 87 observations are not independent tasks. Report planned denominator and stage-reached denominator for environment, retrieval, context truncation, malformed protocol, semantic reasoning, edit matching, scope, syntax, target behavior, regression, selection and safety failure. Include blocked, missing, crash, duplicate and exhausted trials. Freeze revisions, manifests, hashes, quantization, template, settings, budgets, evaluator, hardware. Paired randomized/counterbalanced order, predefined seeds, uncertainty intervals and paired differences; stochastic sample settings logged. Temperature zero rerun is not automatically independent.

## 14. Hardware-aware intelligence

Installed RAM is not available RAM; about 4 GiB was available in the matched runs. A nominal 16 GB machine may page or fail. Reuse existing quantized weights, one resident runtime, initial measured 4,096 context, bounded in-memory index, sequential candidates and inert patch metadata, cancellable/throttled indexing, separately isolated resource-bounded verification. Measure free RAM before starting; never stop unrelated workloads or change security/driver/OS settings.

Original proposed (not observed) targets: index <128 MiB on defined medium project; warm lexical p95 <250 ms; cold index <5 s for defined 1,000-source-file project; 1.5B peak proposal RAM <2.5 GiB; 3B <4 GiB; fast mode <15 s, balanced <60 s, deep hard configurable initial 180 s. Define benchmark and account separately for verification, if not safely co-resident.

The single 3B proposal took ~2.4 times as long as the matched 1.5B proposal. Hypothesis: two focused 1.5B attempts could offer better quality/latency at lower peak RAM. Sparse, unmatched broader evidence cannot answer. Optimize independently verified solved tasks per wall-clock/resource consumption, not tokens/s.

## 15. Knowledge distillation and specialization

Retain [Phase 2 specialization roadmap](2026-11-27-model-specialization-roadmap.md). Distill successful coding behavior rather than memorize framework docs. High-value behaviors: evidence selection, tool choice, valid actions, precise modifications, repair after trusted feedback, abstention. Lower priority: Laravel memorization/general conversation; lengthy reasoning narratives uncertain. Candidate example contains task, compact evidence, valid action, independently verified outcome and corrected action after a failure. Use only appropriately licensed, authorized, independently validated trajectories; no assumption that research-only 3B outputs are commercially reusable.

Reconsider training only after held-out retrieval, complete evidence, evaluated deterministic edit interface, qualified independent verifier, reasonable inference strategies and reproducible residual model-attributable failures; dataset/license/compute/evaluation approval separate. If harness resolves failures, training may be unnecessary.

## 16. Open-source implementation shortlist

| Project | Capability and disposition |
|---|---|
| [Tree-sitter](https://github.com/tree-sitter/tree-sitter), [PHP grammar](https://github.com/tree-sitter/tree-sitter-php) | Syntax parsing; original high priority, revised conditional |
| [ripgrep](https://github.com/BurntSushi/ripgrep) | Lexical search reference/control |
| [Tantivy](https://github.com/quickwit-oss/tantivy) | Rust full-text indexing if scale justifies |
| [Aider](https://github.com/Aider-AI/aider) | Repo maps/edit strategy |
| [Agentless](https://github.com/OpenAutoCoder/Agentless) | Localization/repair/validation |
| [LocAgent](https://arxiv.org/abs/2503.09089) | Graph-guided localization concept |
| [SCIP](https://github.com/scip-code/scip) | Language-independent navigation/symbol indexing; future interoperability |
| [PHPActor](https://github.com/phpactor/phpactor) | Optional PHP intelligence |
| [PHPStan](https://github.com/phpstan/phpstan), [Larastan](https://github.com/larastan/larastan) | Optional static verifier/ecosystem plugin |
| [Laravel Boost](https://github.com/laravel/boost) | Optional framework evidence and tools |
| [llama.cpp](https://github.com/ggml-org/llama.cpp) | Retain existing local inference |
| [SWE-smith](https://github.com/SWE-bench/SWE-smith) | Executable evaluation/training data, future |

Study/adapt selectively, no wholesale recreation or approved dependencies. Review exact versions, licenses, transitive dependencies, binary size, security and cross-platform costs.

## 17. Original roadmap and workstreams

Original proposed milestone name: Coding Intelligence v2 — Repository Intelligence (not repository policy). The [roadmap](2026-11-27-repository-intelligence-roadmap.md) preserves all eight original milestones and subsequent revisions. Original sequence: retrieval recovery -> structural intelligence -> evidence compiler -> deterministic action engine -> isolated behavioral qualification -> adaptive reasoning/repair -> conditional semantic retrieval -> conditional specialization. Original targets included 11/12 recall, 30% fewer median prompt tokens without evidence loss, 50% fewer edit-realization failures, all containment probes and 10 percentage point paired behavioral gain with held-out confirmation. None is established performance; freeze gates prospectively.

Retrieval-only benchmark, AST/index, context, static/inert proposals can advance independently of sandbox research (capabilities, resource/filesystem enforcement, trusted isolation controls and qualification). Workstreams converge at behavioral evaluation. Native clean-host 0.1 remains separate.

## 18. Illustrative Rust module structure

~~~
rust/src/
  project.rs
  context.rs
  grounded.rs
  runtime.rs
  intelligence/
    lexical.rs symbols.rs graph.rs query.rs ranking.rs evidence.rs
  ecosystem/
    mod.rs laravel/{routes.rs,composer.rs,eloquent.rs,contracts.rs}
  reasoning/
    controller.rs budget.rs actions.rs candidates.rs
  verification/
    static_checks.rs containment.rs diagnostics.rs
~~~

Evolutionary sketch, not a required reorganization. Extend existing context.rs, project.rs and grounded lab first; extract modules only with complexity/ownership/testing justification. Avoid large rewrite before measuring improved baseline.

## 19. Approaches rejected or deferred

| Approach | Disposition/reason |
|---|---|
| Immediate larger models | Deferred; retrieval originally blocked inference |
| Train to compensate for retrieval | Reject misdiagnosed bottleneck |
| Entire repository prompt | Reject default; noise/latency/memory |
| Mandatory vector database | Deferred, unproven necessity |
| Unbounded loops | Reject cost/safety |
| Long self-reflection | Deferred, unassisted correction can harm |
| Multiple resident models | Deferred, overhead |
| Majority vote without verifier | Reject correctness signal; correlated errors |
| Unchanged repeat of failed source-ID/line trials | Reject |
| Benchmark-specific repair templates | Reject inflated generalization |
| Model tests as sole oracle | Reject self-confirmation/reward hacking |
| Hidden scorer feedback | Reject leakage |
| Ordinary host generated code execution | Reject security boundary |
| Full RL infrastructure | Deferred complexity |
| Framework memorization as primary strategy | Reject stale/version-dependent knowledge |
| Persist remote tool outputs | Reject repository policy |

## 20. Original immediate Codex assignment

The historical narrow Retrieval v2 Stage 1 prompt is preserved in the [roadmap](2026-11-27-repository-intelligence-roadmap.md). It called for independent reproduction of 1/12, 6/12, 11/12, reuse of the original 12 public tasks, deterministic bounded changes, no inference/downloads/training/system changes, no oracle or release changes, focused draft PR and closeout before further inference. This assignment is superseded by Part II for further work, not erased.

## 21. Original recommendations

Continue 1.5B low-resource baseline and research-only 3B control; improve lexical retrieval, then structural graphs and Laravel intelligence; improve context density and deterministic tools; adapt inference only after baseline recovery; semantic embeddings conditional; repair after containment; no new checkpoint downloads, training or native rewrite.

## 22. Original closeout and limitations

Direct read-only GitHub inspection of main and specified measurement commit, relevant previous report summaries, code and lab excerpts; targeted academic literature and open-source review, not an exhaustive systematic review or entire Rust security audit. Earlier full research documents were not all exhaustively analyzed; PR and CI state was not fully rechecked at the original research checkpoint. External results author-reported, not locally reproduced. Proposed resource/latency limits, context allocations, corpus sizes and promotion thresholds were engineering decisions without explicit calibration. Initial ranking reproduction not independently run; executable behavioral verification blocked.

Proposed knowledge maintenance: archive the three files; eventually extend benchmark and implementation skills for retrieval-only failure attribution, delivered-evidence recall and adaptive inference. No new skill then warranted. No repository changes, commits, PRs, weights, training, generated code or machine changes occurred during original research.

## 23. Original conclusion

A modest model with better repository knowledge, more relevant evidence, less noise, fewer mechanical operations, reliable tools, bounded reconsideration and independent verification might compete with larger models on specific tasks; generalization is empirical. Ten additional potentially recoverable complete-retrieval tasks out of twelve were identified by the original reproduction without adding model parameters. Invest in repository intelligence first, not training. The next evidence update recovers eleven additional tasks instead and changes the priority.

---

# Part II — November 28 evidence reassessment

## 1. Updated executive conclusion and repository facts

Reviewed [e4471558a55e8cc0475c8ab8d9fc68bb8d008c14](https://github.com/MrPunyapal/TinyBuilder/commit/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14), its detailed [Retrieval Intelligence v2 report](https://github.com/MrPunyapal/TinyBuilder/blob/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14/docs/research/2026-11-27-retrieval-intelligence-v2.md), [retrieval JSON](https://github.com/MrPunyapal/TinyBuilder/blob/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14/benchmarks/results/2026-11-27-retrieval-v2.json), [1.5B proposal JSON](https://github.com/MrPunyapal/TinyBuilder/blob/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14/benchmarks/results/2026-11-27-retrieval-v2-proposals-1.5b.json), changed status and benchmark skill. Main still ce283375 at inspection; evidence was not merged. Measured Rust lab code at 5a5adb85a0392c0b05d7b3f64e910972769401f2. Retrieval coverage is no longer the dominant observed bottleneck on this corpus; establish independent generalization and whether small models can turn evidence into coordinated semantically correct changes. Key questions: sufficient but concise evidence, focused semantic decisions, Rust-coordinated patches, additional inference without increased peak memory, usefulness under limited available (not installed) RAM.

| Capability | Revised priority |
|---|---|
| Lexical recall | Validate generalization |
| Context precision | Critical |
| Comprehensive dependency graphs | Conditional |
| Task decomposition / multi-file planning | Critical |
| Memory efficiency | Critical |
| Behavioral verification | Critical dependency, blocked |
| Training | Deferred |

Do not continue maximizing recall on the same twelve tasks.

## 2. New measured retrieval and review-only proposals

All seven arms cumulative, identical source inventory and prompts; Rust binary receives project path, strategy, task only; separate Python scorer owns required edit paths. Baseline four terms threshold 10; lower to 5; expand term limit to 32; caseless content substring match; normalize identifier splitting and conservative plural/verb stems retaining exact tokens; dependencies one-hop same-directory/language static references from top lexical result; fallback only when no qualifying path and code-only inventory fits four files/12 KiB. No corpus aliases/task-specific ranking rules reported.

| Arm | Complete tasks | Required paths | Target precision | Non-target files / bytes | Total bytes | Median retrieval | Multi-file recall |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 1/12 | 1/14 | 100% | 0 / 0 | 247 | 1.56 ms | 0/2 |
| Threshold | 6/12 | 7/14 | 77.8% | 2 / 406 | 1,677 | 1.54 ms | 0/2 |
| Expanded | 11/12 | 12/14 | 63.2% | 7 / 1,352 | 3,353 | 1.95 ms | 1/2 |
| Caseless | 11/12 | 12/14 | 63.2% | 7 / 1,352 | 3,353 | 1.97 ms | 1/2 |
| Normalized | 12/12 | 14/14 | 58.3% | 10 / 1,890 | 4,178 | 2.43 ms | 2/2 |
| Dependencies | 12/12 | 14/14 | 58.3% | 10 / 1,890 | 4,178 | 3.09 ms | 2/2 |
| Fallback | 12/12 | 14/14 | 58.3% | 10 / 1,890 | 4,178 | 2.79 ms | 2/2 |

Target precision = complete required paths / selected paths; bytes summed across tasks; latency median of per-task medians of three Rust calls, excluding process launch, one Windows host. Expanded terms alone matched caseless coverage. Both missed two booking files, recovered by normalization. Dependency and fallback added no coverage, but separate synthetic controls check CamelCase/snake_case, regular inflection, same-directory unrelated-name dependency, fallback eligibility/refusal. The cumulative arms are not isolated factorial causal effects; normalized is the smallest tested full-recall combination on this corpus. Freeze candidate; independent evaluation before promotion. Historical 100% precision at baseline is not good retrieval (almost everything missed).

Existing 1.5B Q4_K_M, CPU b12359, 4,096 context, exact text, one attempt per multi-file task:

| Task | Required files delivered | Status | Startup | Proposal latency | Prompt / completion | Sampled combined peak |
|---|---|---|---:|---:|---:|---:|
| booking_availability | Booking.php, BookingRules.php | No change | 1.81 s | 6.84 s | 272/99 | 1.73 GiB |
| parcel_weight | ParcelLimit.php, ParcelIntake.php | Single-file ParcelLimit.php proposal, approval withheld | 1.63 s | 4.58 s | 269/50 | 1.73 GiB |

Both exactly two required files, not extra files; cannot attribute these outcomes to retrieved distractors. 1/2 readiness, 0 applied patches, 0 of 32 planned semantic observations attempted; source, weights and manifest unchanged. No VRAM measurement. No-change status reflects harness rejection, not proof of abstention or a specific reasoning failure. A single-file solution may satisfy behavior in principle; only independent oracle decides.

Both models initially held at 2,782 and 2,788 MiB available; 1.5B retry started at 2,890 MiB. Research-only 3B after 1.5B had 3,263 MiB, then 3,449 MiB at retry, below 3,500 MiB minimum (51 MiB short). Prior peak ~3.29 GiB. Both planned 3B trials blocked, zero attempted. Do not lower threshold merely to run. Do not infer 3B ability on these tasks from blocked measurements.

Repository report states local Windows checks: 45 Rust tests, 291 Python with two skips, 37 acceptance unit tests, six guidance tests, checker and Python compilation passed. Product CLI and both original read oracles match main. These are reported checks, not locally rerun in research.

## 3. Critical architectural discovery: one-edit expressiveness

Directly inspected [grounded.rs at e4471558](https://github.com/MrPunyapal/TinyBuilder/blob/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14/rust/src/grounded.rs#L122-L174), [grounded_lab.rs](https://github.com/MrPunyapal/TinyBuilder/blob/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14/rust/examples/grounded_lab.rs) and [runtime.rs](https://github.com/MrPunyapal/TinyBuilder/blob/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14/rust/src/runtime.rs).

~~~rust
struct Replacement { path: String, old: String, new: String }
~~~

The system prompt explicitly requests one minimal exact-text replacement in an existing file; the controller calls one proposal and processes one patch. Multiple allowed edit paths restrict scope, not expressivity. The tested path retrieves multiple files and can select one for modification, but does not express coordinated multi-file edits or iterative plan execution. Other repository paths are not audited as equivalent. Behavioral verification blocked. The experiment cannot distinguish model planning limitations from harness expressiveness. The single-file parcel proposal conforms to the requested interface. Do not claim inherent 1.5B multi-file inability.

## 4. Context precision: useful evidence, not merely target precision

Normalized selected 24 file occurrences across 12 tasks: 14 edit targets (58.3%), 10 non-targets (41.7%); 1,890/4,178 ~45% bytes non-target. Some may be necessary supporting contracts; non-target does not equal irrelevant. Both multi-file trials got exactly their two required files.

Distinguish edit evidence (may need modification), supporting evidence (contracts, callers, dependencies, schema and existing behavior), distractors (no useful task info). Retain original metric; add supporting-evidence recall, required-span recall and irrelevant-token fraction. [CORE-Bench](https://arxiv.org/abs/2606.11864), [Agent Retrieval Bench](https://arxiv.org/abs/2607.24882) and [CodeRAG-Bench](https://aclanthology.org/2025.findings-naacl.176/) motivate separating evidence roles/utilization.

Pipeline: broad recall-oriented retrieval -> classify edit/support/distractor -> compile exact editable source and compact supporting signatures -> focused model decision. Retrieval and context delivery are separate. Compare full normalized context, required evidence only, plus necessary signatures, plus controlled distractors. Model, task, edit interface fixed.

## 5. Independent retrieval generalization

Freeze normalized; treat existing twelve as development/regression. Repeated optimization on those fixtures risks overfitting. Proposed 30 additional tasks across at least six independent PHP/Laravel lineages: six single-file localization, six cross-file reasoning, eight genuine multi-file modifications, four vocabulary mismatch/ambiguous IDs, six no evidence/wrong repository. Paraphrases without target hints are robustness variants not independent observations. Include larger realistic directory trees and competing symbols.

Proposed gates: preserve 12/12 dev; >=90% complete evidence recall on positives; >=95% required edit-span recall; >=90% no-evidence abstention on sufficiently expanded negatives; material distractor-token reduction without evidence loss; medium-project retrieval p95 <250 ms; zero unauthorized access. With only six negatives a 90% point threshold demands 6/6 and still has wide uncertainty; expand negatives before promotion. Score exact numerators/denominators and paired task-level differences. Dependency/fallback remain experimental, not promoted just because synthetic controls pass. AST, full graph and embeddings conditional on independent diagnosed deficits.

## 6. Task decomposition: plan, focus, edit, reconcile

The model currently faces understanding a requirement, locating changes, cross-class reasoning and generating an edit at once. Split responsibilities. [CodePlan, FSE 2024](https://arxiv.org/abs/2309.12499) ([implementation](https://github.com/microsoft/CodePlan)) studies repository planning with dependency analysis and context of earlier changes. Adapt concept; results not transferable automatically.

~~~
Requirement -> normalized retrieval / focused reads
  -> compact semantic plan (dependencies)
  -> one focused semantic operation per model call
  -> Rust patch transaction and updated virtual source
  -> consistency / unresolved obligations
  -> explicit approval + qualified independent verifier
~~~

One resident model across phases, bounded decisions, intermediate changes inert. Illustrative parcel-weight task (not hidden solution): model identifies behavior; Rust finds classes/callers; model identifies contracts and first edit; Rust creates inert updated source view; model inspects caller against updated contract and proposes further edit if necessary; Rust assembles patch set; qualified verifier checks behavior/regression. Do not force every retrieved file to be edited; accept a correct single-file alternative if independently validated.

Illustrative compact plan (not implemented schema):
~~~json
{
  "goal": "Maintain consistent parcel weight validation",
  "steps": [
    {"file":"ParcelLimit.php","intent":"Inspect and update the weight constraint"},
    {"file":"ParcelIntake.php","intent":"Check compatibility with the updated constraint"}
  ]
}
~~~
Rust validates paths, scope, evidence, then supplies exact focused source. Plans are revisable hypotheses, may omit dependencies or introduce unnecessary operations. No benchmark hints or hidden solution.

## 7. Multi-file editing: extend exact text, do not abandon it

~~~rust
struct EditIntent { path: String, old: String, new: String }
struct PatchTransaction {
    edits: Vec<EditIntent>,
    // Validated source identities; dependency/ordering metadata; approval state
}
~~~

Keep familiar per-call path/old/new and collect into bounded inert transaction. Tie edits to verified source, reject/reconcile ambiguity and overlapping changes explicitly, later calls see virtual current source, revalidate all identities/permissions before application, review combined diff, prevent partial application or test rollback/recovery. Multi-file updates are not intrinsically atomic; do not claim transaction safety or hostile-filesystem containment.

Compare batched array in one call (lower latency, complex output), sequential exact text (lower per-call complexity, risk of inconsistent later edit), plan + sequential (coordination, extra latency and potentially wrong plan). Preferred first experiment sequential exact text, separate plan ablation. Measure expressiveness separately from planning.

## 8. Memory-efficient inference-time intelligence

The 3B blocked preflight and 1.5B two trials above motivate smaller allocated context and runtime reuse. Both requests consumed fewer than 400 prompt+completion tokens, capacity was 4,096. Reducing allocated capacity may reduce KV/cache memory depending on actual architecture/configuration. Current lab accepts 2,048–8,192 explicit context. First compare 2,048 vs 4,096; 1,024 requires conditional lab extension, 8,192 only when evidence capacity limiting, avoid large defaults. Never silently drop essential source/generation space. Retain RAM preflight; no unsafe workarounds.

Grounded lab starts runtime for each invocation. One verified runtime across bounded calls could remove repeated startups (1.63–1.81 s observed); it does not itself reduce peak RAM and longer residency has costs. Release on completion/cancel/bounded idle timeout.

| Optimization | Priority |
|---|---|
| Smaller context, sequential calls, compact external state, no growing history | Immediate experiments |
| Parallel slot control | Investigate |
| In-memory prefix reuse, batch allocation, KV-cache quantization, partial GPU offload | Conditional |
| More aggressive weight quantization | Later |
| Multiple simultaneous models | Avoid |

Current runtime hard-codes CPU via device none and zero GPU layers. [Upstream llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) describes contexts, caching, parallel slots; verify exact pinned b12359 flags/semantics before experimentation. No runtime upgrade, GPU/system change or download needed for first comparisons.

## 9. External task-local working memory

Store bounded structured state in Rust outside the neural model: original requirement and constraints, evidence references/hash provenance, current plan, validated proposed changes, unresolved contracts, remaining budget. Each call sees current subtask, relevant evidence and next-action schema, not entire chat history; controller incorporates validated response and refreshes evidence. In memory or authorized inert staging, not persistent product preference database. Model claims remain hypotheses unless grounded in source; never treat stored claims as trusted facts. Preserve repository storage/privacy policy.

## 10. Can extra computation make 1.5B competitive with 3B?

Compare 1.5B strategies against the 3B single-attempt baseline only when safe RAM and equivalent task/evidence budgets permit. Latest 1.5B proposal midpoint 5.71 s. Illustrative constant-call budget: 1/2/3/4/6 sequential calls ~5.71/11.42/17.13/22.84/34.26 s, one resident model. Prior 3B single proposal 12.81 s on a different task; not a matched performance comparison. Excludes startup, prompt-processing variation, verification; sequential does not prove constant peak RAM. Measure quality/latency/memory and report blocked denominator.

## 11. Revised controlled experiments

R1 independent generalization, R2 supporting vs distractors, E1 single vs multi expressiveness, E2 sequential vs batched all P0; P1 explicit plan, M1 2K/4K, M2 runtime reuse, P2 compact task state vs conversation history P1; I1 adaptive sequential inference P2; V1 verifier-guided repair containment-dependent; T1 specialization deferred.

Main matched planning comparison: A existing single-edit; B one call multi-edit; C sequential exact edits without plan; D compact plan + sequential; E human-curated plan + model edits diagnostic. Same tasks, evidence, weights and cumulative budgets as applicable, include planning costs, do not force same number of edits. B>A suggests expressiveness; C>B decomposition; D>C explicit planning; E>D model plan weakness; E still fails investigate reasoning/realization; correct candidates but selector fails indicates selection. Before containment, only proposal validity, coverage, consistency and resources; no semantic score. [Full revised ablation plan](2026-11-27-intelligence-ablation-plan.md#part-ii--revised-experiments).

Proposed promotion gates: >=90% independent complete evidence, all deterministic transaction controls, material plan benefit over unplanned sequential, no essential compression loss, resident runtime reduces cumulative startup without resource regressions, reduced measured memory from smaller context with no material quality loss, measurable sequential behavioral gain within latency budget, zero unauthorized actions, unchanged 10/10 read gate. Quality gates require independent behavioral scoring.

## 12. Revised engineering roadmap

Freeze normalized (12/12 development only); independent evidence qualification and multi-edit model-free infrastructure immediate, coordinated parallel ownership; efficient inference (2K, reuse, state); task decomposition and explicit plan ablation; contained behavioral qualification; add AST/graphs/semantic retrieval only if independent gaps; specialize only after residual model-attributable failures. See [roadmap](2026-11-27-repository-intelligence-roadmap.md#part-ii--revised-roadmap).

## 13. Local Codex assignment

See revised historical prompt in [roadmap](2026-11-27-repository-intelligence-roadmap.md). Preserve current work, benchmark and product oracles; independent retrieval and model-free inert transactions, prepare ablations and resource comparisons, stop for review before further inference. No generated code, downloads, training or personal Windows changes.

## 14. Reassessment closeout and limitations

Directly read experimental commit, reports, JSON, proposal schema, grounded lab and relevant runtime excerpts; reviewed additional planning/retrieval research. Local results not reproduced; no independent generalization, multi-file semantic score, attempted 3B follow-up, or measured memory/session/decomposition improvements. Main at inspection not e4471558. Corpus size, transaction design, sequencing and thresholds are proposals. No repository modifications, model downloads, training, system changes or candidate execution during the research/reassessment.

## 15. Final revised capability assessment

| Capability | Evidence state |
|---|---|
| Lexical retrieval on development corpus | Demonstrated 12/12, 14/14 |
| Independent repository generalization | Unverified |
| Single-file review-ready proposal | Demonstrated, not correctness |
| Multi-file proposal interface | Missing in tested lab |
| Multi-file semantic reasoning | Unverified |
| Memory-efficient 1.5B inference | Partial local evidence |
| Adaptive sequential reasoning | Proposed |
| Executable behavioral qualification | Blocked |
| Need for training | Not established |

Recovering all required files without adding parameters changes the question: can a small model solve a complex task through focused evidence-grounded decisions, external working memory, coordinated edits and efficient sequential inference? That is the next intelligence opportunity, not additional parameters. Training remains deferred.

---

# Part III — Maintainer reconciliation and archival closeout

The research and revised direction were accepted by the owner on November 28, authorizing these three documentation files and a draft PR only. No implementation permission, status edits, skill edits, merging, downloads, training or generated execution follow from archival. Numerical gates are proposed and must be frozen/reviewed prospectively.

At archival preflight main was still [ce283375](https://github.com/MrPunyapal/TinyBuilder/commit/ce28337552933a671a95d1ad30baa07cfe7cc2b7); exact-main query in preceding maintainer review returned seven successful workflow runs (not evaluator qualification). Two related draft PRs now exist: [#25 Phase 3](https://github.com/MrPunyapal/TinyBuilder/pull/25), head [28668ad18da56f812448ad8b11c6177fa1d9e8ed](https://github.com/MrPunyapal/TinyBuilder/commit/28668ad18da56f812448ad8b11c6177fa1d9e8ed); [#26 Retrieval v2](https://github.com/MrPunyapal/TinyBuilder/pull/26), head e4471558. Earlier "no open PRs" was historical and superseded. Previous retrieval branch query returned one successful Python workflow; applicable exact-head CI and integration review are separate. PR #26 says local agent owns independent source-only evidence, maintainer owns separate multi-edit protocol; do not duplicate work. Main status snapshot is stale but explicitly out of archival scope.

Phase 3 [portable sandbox report](https://github.com/MrPunyapal/TinyBuilder/blob/28668ad18da56f812448ad8b11c6177fa1d9e8ed/docs/research/2026-11-28-phase-3-portable-sandbox.md) recommends model-free experimental Wasmtime/WASI supervisor/worker, conditional PHP.wasm / Wasmer compatibility. Same-user worker is not outer OS isolation against runtime compromise; independently qualified outer boundary still mandatory. PHP/Laravel exact stack compatibility unverified. Keep existing [approved-guest design](2026-11-27-contained-qualification.md) (not a qualified live environment); no native-host fallback, private transfers, or personal Windows provisioning. Preserve black-box observation bridge: hidden scorer and expected values outside candidate/model roots. CI with trusted controls is not containment qualification. Intelligence and sandbox workstreams converge only at behavioral scoring; no need to block model-free retrieval and inert transaction work.

Reviewed existing benchmark, implementation, knowledge-maintenance skills and AGENTS.md. Proposed later procedural enhancement: distinguish edit-protocol expressiveness from model reasoning; delivered evidence vs selected paths; paired compute budgets and selection accounting. Do not modify skills/guidelines or project status in this archive, per explicit owner scope. No new skill warranted at this stage. Local uncommitted work and actual hardware measurements inaccessible; no tests or code executed in the research archive. Historical source links and study claims are preserved as reported, not freshly rechecked; this Markdown transcription preserves substantive findings, proposals, counterexamples, prompts and caveats rather than client-specific widgets/citation markers or chat transcript. Only external links explicitly available in the research text are retained; no opaque citation IDs. Check external primary sources before using numbers in acceptance decisions. No automatic merge or public release.

Next: lead maintainer review #26 and #25 and this archive; coordinate independently owned retrieval qualification and deterministic multi-edit work; evaluate resource/plan ablations only after reviewed manifests; execution qualification separately; no training until evidence warrants it.
