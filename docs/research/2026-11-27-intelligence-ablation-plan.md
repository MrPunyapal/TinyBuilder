# TinyBuilder Phase 4 — Controlled ablation plan

Research 2026-11-27; revised 2026-11-28. Companion [report](2026-11-27-intelligence-beyond-parameters.md) and [roadmap](2026-11-27-repository-intelligence-roadmap.md). Research plan, not results or authorization to run live inference or generated code. Owner accepted revised research; proposed numerical gates require review/freeze. Preserve [benchmark skill](../../.agents/skills/tinybuilder-benchmark/SKILL.md), [original qualification](../../benchmarks/QUALIFICATION.md), [contained qualification](2026-11-27-contained-qualification.md) and unchanged read-only release oracles.

## Experimental baseline and frozen manifests

[0fab9c6 evidence](https://github.com/MrPunyapal/TinyBuilder/commit/0fab9c6ae2b94dfb514287ded6275e72fadadcb9) and [e4471558 evidence](https://github.com/MrPunyapal/TinyBuilder/commit/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14) are historical read-only sources; do not rerun unchanged smoke trials by default. Existing 12 tasks, three applications sharing a skeleton, 87 planned observations; matched existing Qwen2.5-Coder 1.5B and research-only 3B Q4_K_M, llama.cpp b12359 CPU, 4096 context. Retrieval v2 code measured at 5a5adb85a0392c0b05d7b3f64e910972769401f2. Normalized is lab-only, full development recall, not general qualification.

Freeze exact commit, repo lineage/task manifest/source/evaluator digests, model/license/runtime/template hashes, quantization, device, context capacity, generation reserve, actual token limits, seed/temperature/sampling, tool schema, proposal controller, budgets (calls, cumulative generated/input tokens, wall time, allowed memory), guest/image/config and diagnostics rules before experiments. Keep evaluator-owned allowed edit paths/hidden tests/expected values/reference patches outside all model-facing roots. Allowed scope is a validator, not a target hint. Human-curated evidence/operations are labeled diagnostic controls, never deployable arms or training examples without further review.

Paired task comparisons, randomized/counterbalanced order, predefined seeds. Report all planned tasks, attempted, reached each stage, remaining/blocked and reasons, actual tokens, startup/retrieval/inference/verification latency, sampled process/combined peaks and actual whole-worker resource limits where applicable, VRAM if measured (null otherwise), source integrity and cleanup. Record duplicate candidates, invalid/declined proposals, timeouts, budget exhaustion and missing metrics. Retain negatives. Zero temperature reruns not independent samples. Report paired differences and uncertainty; tasks clustered by lineage, paraphrases nested within task, 87 observations not 87 independent tasks. Do not tune on final confirmation set.

## Part I — Original experiments (preserved)

### A. Retrieval without inference

| Arm | Strategy |
|---|---|
| A0 | Existing selective lexical |
| A1 | Lower minimum threshold only |
| A2 | Case normalization only |
| A3 | Expanded query selection only |
| A4 | Identifier/path tokenization |
| A5 | BM25 |
| A6 | Best lexical combination |
| A7 | A6 plus AST evidence |
| A8 | A7 plus one-hop dependencies |
| A9 | A8 plus semantic retrieval, if separately approved |

Original plan was independent changes before combination. Actual v2 arms were cumulative; preserve this difference (do not claim isolated causal effects). Measure complete task recall, individual required path/span recall, precision, irrelevant context, delivered tokens, truncation, retrieval latency/memory, unrelated controls and paraphrase stability. Original dev gate >=11/12 complete, >=13/14 required paths, no silent essential truncation, >=90% no-evidence abstention on adequate sample, unchanged 10/10 native gate, zero unauthorized reads/actions. Medium Laravel repository resource limits to be calibrated. Actual normalized 12/12 and 14/14 supersede dev recall target only; A7–A9 conditional after independent gaps.

### B. Retrieval vs model reasoning

| Arm | Context |
|---|---|
| B0 | Original selective |
| B1 | Improved lexical |
| B2 | Improved lexical + structural |
| B3 | Human-curated sufficient evidence, no gold/hidden test |
| B4 | Curated evidence + irrelevant distractors |
| B5 | Curated evidence minus essential information |

Same tasks, models, prompt format, budgets and edit interface. B3 > B1 suggests evidence remains limiting. B3 poor suggests residual reasoning, action selection, editing or verification, not automatic diagnosis. B4/B5 test noise and missing-evidence effects; include realistic distractors. Do not make reference edits available.

### C. Reasoning vs editing

| Arm | Method |
|---|---|
| C0 | Existing exact-text replacement |
| C1 | Same semantic decision, deterministic edit construction |
| C2 | Model-selected source region with exact replacement |
| C3 | Restricted typed mechanical transformation |
| C4 | Human-supplied correct operation, model realizes edit |
| C5 | Human-supplied operation, deterministic tool realizes edit |

C4/C5 diagnostic only. Record independent reviewer classification of intended operation, separate from executable behavior. Test import, resolved rename, comparison/literal, argument/config or uniquely located expression as applicable; no benchmark-specific template. Earlier model-selected line and source-ID failures remain baselines, no unchanged repeat. Do not infer semantic error from replacement failure. Multi-file expressiveness added in Part II.

### D. Context density

| Arm | Evidence |
|---|---|
| D0 | Complete relevant files where fit |
| D1 | Exact relevant methods |
| D2 | D1 + dependency signatures |
| D3 | D2 + compact repository map |
| D4 | D3 + framework metadata |
| D5 | D3 + controlled irrelevant source |

Fixed context capacities, actual template overhead counted. 4,096 first; compare 2,048 and conditionally 8,192 only if justified. Record actual delivered source-span recall, prompt/generation tokens, truncation, latency and memory. Original proposal >=30% median token reduction on tasks fitting both full and compact arms with no required evidence loss. No lossy compression of editable source. If evidence cannot fit, decompose or abstain.

### E. Test-time computation

| Arm | Strategy |
|---|---|
| E0 | One deterministic proposal |
| E1 | One proposal with greater output budget |
| E2 | Three independent sampled candidates |
| E3 | Three sequential evidence-refinement attempts |
| E4 | Adaptive within same cumulative budget |
| E5 | Verifier-guided repair after qualified containment |

Compare equal cumulative compute conditions, record actual calls/tokens/time and model residency; generation budget is not identical to compute unless actual prompt costs accounted. Oracle pass@k (any correct candidate) distinct from deployable selected candidate success; selection cannot see hidden scorer. Correlated errors invalidate independence assumption; simulator formula 1-(1-p)^k is illustrative only. Never majority vote over failed trusted checks. Candidate generation sequential, not simultaneous models.

Provisional modes: fast 1 call/256 generated tokens/15 s target; balanced <=3/1024 cumulative/60 s; deep <=6/3072 cumulative/3 distinct candidates/180 s initial hard cap, verification dependent. Escalate observable unresolved evidence, ambiguous matches, syntax/contract/behavior feedback, not confidence alone. Stop verified, repeated candidate, no meaningful new evidence, resource/call/time exhaustion or blocked safety gate.

### F. Verification and repair (blocked)

Once approved isolated evaluator passes fresh probes, compare first-attempt behavior with one/two/three feedback attempts. Separate syntax, target behavior, regression, degrade-from-pass; retain independently verified good candidates. Candidate receives only ordinary allowed diagnostics or separate public feedback, never hidden test source/expected values/reference repair. Independent scorer outside model and candidate; output untrusted. Seeded baseline must fail target, reference pass, plausible wrong and one-file revert controls fail, regression controls pass. Worktrees, host lint or candidate self-reported tests are not isolation. No generated code on personal host, no fallback if guest/transport/cleanup ambiguity. Record infrastructure blocked vs proven candidate failure.

### G. Training necessity

| Observation | Intervention |
|---|---|
| Low retrieval recall | Retrieval |
| Incomplete necessary span | Context compiler |
| Correct operation, invalid patch | Editing interface |
| Wrong action with complete evidence | Reasoning/specialization review |
| Correct candidate exists but selector misses | Selection/verifier |
| No candidate under reasonable budget | Investigate model limits |
| Reproducible model-attributable held-out failures | Conditional specialization |

No new weights/training until evaluated existing harness and pretrained candidates under approved budget. License/data provenance and untouched base/adapters matched on held-out tasks; research-only 3B not presumed commercial teacher. See [Phase 2](2026-11-27-model-specialization-roadmap.md). Never compensate for broken harness with training.

### Corpus and funnel

Original staged scale 12 dev, 36 expanded >=6 independent lineages, 60+ independent qualification, 100+ multi-framework long-term. Single-file, cross-file evidence, genuine multi-file changes, validation, auth, DB, API, refactoring/features, no safe/evident change. Freeze repo-lineage split before tuning. Current public score funnel per model: 12 planned, 1 full target recall, 1 inference, 1 ready, 0 semantic observations. Correctness unknown, not 0% or 8.3% semantic. Failure labels environment, retrieval, delivered span/context, protocol parse, reasoning, edit realization/match, scope, syntax, behavior, regression, selection, safety, blocked preflight/cleanup.

## Part II — Revised experiments

Retrieval v2 cumulative table retained in full report; normalized 12/12, 14/14, 24 file occurrences, 10 non-target/1,890 bytes, 4,178 total bytes, target precision 58.3%, median 2.43 ms, one Windows host. Dependencies 3.09 ms and fallback 2.79 ms no extra coverage; synthetic controls passed; do not promote without independent evidence. Booking and parcel exactly both required files, 1.5B one no change and one single-file proposal, no application, 0/32 planned observations. [One-edit schema](https://github.com/MrPunyapal/TinyBuilder/blob/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14/rust/src/grounded.rs#L122-L174) is a confound, not multi-file model limitation. 3B planned two, zero attempted due to 3,500 MiB preflight threshold (latest 3,449 MiB). Distinguish blocked from candidate failure.

| ID | Variable | Priority |
|---|---|---|
| R1 | Independent retrieval generalization | P0 |
| R2 | Supporting evidence vs distractors | P0 |
| E1 | Single-edit vs multi-edit expressiveness | P0 |
| E2 | Batched vs sequential editing | P0 |
| P1 | Explicit plan vs no plan | P1 |
| M1 | 2K vs 4K allocated context | P1 |
| M2 | Resident runtime vs repeated startup | P1 |
| P2 | Compact external state vs accumulated history | P1 |
| I1 | Single vs adaptive sequential inference | P2 |
| V1 | Verifier-guided repair | Containment-dependent |
| T1 | Specialization | Deferred |

### R1 — Independent retrieval, model-free

Freeze current normalized strategy and all existing arms; no corpus-specific aliases or target hints. Proposed 30 new tasks, >=6 independent PHP/Laravel lineages: 6 single-file localization, 6 cross-file reasoning, 8 true multi-file, 4 vocabulary mismatch/ambiguous identifiers, 6 no-evidence/wrong-repo. Include large realistic directory structures, competing names, ignored files and paraphrases without identifiers. Paraphrases not independent tasks. Freeze labels independently before running; separate edit loci/paths, supporting evidence required for reasoning, distractors; allow alternative correct repairs in eventual behavior score (labels are retrieval evidence, not semantic oracle). No private holdout tuning. Run negative controls with explicit abstention criterion defined before tests; fallback not forced to answer.

Proposed positive-task gate >=90% complete evidence (if 24 positive tasks, at least 22/24); >=95% required edit-span recall, preserve 12/12 dev and original 10/10 read gate, zero unauthorized reads and silent truncation. >=90% correct negative abstention after expanding negative sample; with 6 negatives requires 6/6 and is only initial signal. Report raw counts, confidence intervals and uncertainty by lineage, not just percentages. Target warm p95 <250 ms on defined medium project, actual cold startup/index/memory separately. No unnecessary graph/embedding until diagnosed independent failures. Score required paths and delivered spans separately, selected file size vs delivered actual tokenizer tokens, counts of supporting vs distracting evidence and relevant-token fraction.

### R2 — Context usefulness and noise

At frozen normalized recall compare:
- Full normalized context.
- Human-curated required evidence only (diagnostic).
- Exact edit evidence plus necessary supporting signatures/contracts.
- Same sufficient evidence plus controlled irrelevant source at predefined token/noise bands.
- Optional missing essential evidence control from original B5.

Use same model, task, edit protocol and context capacity; if one arm exceeds window, mark blocked/decompose as preregistered rather than truncate only that arm. Measure delivered exact spans, support recall, distractor-token fraction, prompt/total tokens, latency, RAM, proposal stages, contained behavior later. Do not equate 58.3% edit-target precision with semantic relevance; both actual multi-file trials had no extra files. Compare evidence classification and compression benefit before adding structural machinery.

### E1/E2/P1 — Multi-edit expressiveness and planning

Prerequisite: deterministic inert transaction tests (see roadmap), no generated execution; review before inference. Preserve existing single-call single exact edit schema as control. Proposed paired arms:

| Arm | Controller |
|---|---|
| A | Existing single replacement |
| B | One call allowing array of exact replacements |
| C | Sequential exact text, no explicit plan |
| D | Compact plan then sequential exact |
| E | Human-curated plan, model-generated edits (diagnostic) |

Identical model, task, context evidence, authorization/scope, cumulative budget as applicable; account for planning tokens/calls and use matched latency/compute comparison in addition to equal generation cap. Do not force edits to every allowed path or count arbitrary number of files edited as correctness. B vs A expressiveness; C vs B sequential decomposition; D vs C explicit planning; E vs D model planning bottleneck; E also fails investigate reasoning/edit mechanics; if correct candidates exist but selection fails, diagnose selection. These are hypotheses and paired differences, not causal certainty with multiple changed variables. Also compare one variable at a time and curated operation controls from original C.

Before containment record schema validity, allowed-scope consistency, exact-match/overlap/no-change/stale errors, number of proposals and covered obligations, virtual-state consistency, combined diff, resource costs; static consistency/readiness/coverage not semantic pass. After independent qualification, target behavior, regressions, accepted alternatives. Reject/resolve overlapping operations, refresh virtual source; rollback tests on trusted fixtures not model output execution. If single edit can satisfy whole task independently, accept it.

Proposed promotion gate all deterministic transaction tests pass; material reduction in edit realization failures (original >=50% on adequate matched sample); explicit plan benefit over unplanned sequential and later paired behavioral improvement with held-out confirmation (original >=10 percentage points vs frozen single-attempt baseline, not automatic promotion). Freeze minimum effect and resource ceilings before experiment.

### M1/M2/P2/I1 — Memory and efficient inference

Use existing CPU b12359 runtime and weights only. Both latest 1.5B requests total <400 tokens, 4096 allocated. Compare 2048 vs 4096 on same evidence and output budgets; record actually allocated slots/cache/config, prompt and completion, memory preflight, sampled driver/server/combined peak, VRAM null if unmeasured, startup/wall time and completion/behavior status. 1024 requires explicit lab change, 8192 only if essential evidence limiting. Do not reduce context by hiding essential source or reserve. Preflight safety unchanged, do not stop unrelated processes. 3B stays blocked unless safe availability, report zero attempts rather than lower threshold.

Compare repeated per-call startup vs one verified resident runtime per task with same prompts, sequential generation, proper cancellation/cleanup/bounded idle timeout. Record startup vs generation separately, wall time, peak and time-resident memory. Runtime reuse removes startup work, not necessarily peak. Compact structured state vs accumulated history at matched task progression; model outputs are hypotheses, not trusted facts. No persistent remote/user transcripts; no multiple loaded models.

Investigate exact pinned runtime slot/cache/batch settings only if supported by verified version. Prefix caching/KV quantization/partial offload conditional; no runtime upgrade, more aggressive weight quantization or new model downloads without approval. CPU currently device none / zero GPU layers. [llama.cpp upstream server docs](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md) are reference, not proof for b12359.

I1 compare one attempt vs fixed sequential budget vs adaptive; actual tokens/time/memory, independent correct candidate and selector success, not just call count. Example 1.5B call average 5.71 s suggests two calls ~11.42 s and three ~17.13 s excluding startup; prior 3B 12.81 s different task, no matched conclusion. Measure 1.5B against 3B only when approved and safe with same tasks. Proposed memory targets <2.5 GiB 1.5B and <4 GiB 3B combined proposal peak; not sufficient to override preflight. Lower measured memory and no evidence/quality loss, lower cumulative startup without resource regressions, measurable behavioral gain within latency limits before promote.

### V1/T1 — Semantic scoring and specialization

Do not admit candidate execution until a separately approved outer environment passes exact fresh isolation qualification, [Phase 3 draft](https://github.com/MrPunyapal/TinyBuilder/pull/25) and existing contained qualification requirements. Same-user process is not outer sandbox; trusted CI not equivalent. Keep hidden scorer outside candidate/model visibility; no transfer of private source without approval; authoritative outcome and cleanup checks required. Freeze development controllers before independent private confirmation. If blocked, record remaining and continue R1/E1 deterministic work. Do not run generated PHP on host or use low-level observe bypass. Behavioral pass must satisfy existing target and regression oracles; no weakening read/behavior tests.

T1 deferred. If after adequate retrieval, complete evidence, expressive edit protocol, decomposition/compute and independent verification significant repeatable residual model failures remain, consider Phase 2 candidate qualification first, then licensed independently verified trajectories, SFT/QLoRA only with explicit approval. No training here. No claim that optimizing system guarantees flagship competence.

## Reproduction references (historical, not executed during archival)

The [v2 report](https://github.com/MrPunyapal/TinyBuilder/blob/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14/docs/research/2026-11-27-retrieval-intelligence-v2.md) records commands below; use exact pinned artifacts and new output paths, review authorization and preflight before live proposal measure. Commands are documentation, not instructions to run now. Retrieval-only source campaign and trusted controls do not execute model-generated code.

~~~text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example retrieval_lab --example grounded_lab
python -m benchmarks.public_proposal_campaign prepare --output NEW_SOURCE_DIR
python -m benchmarks.public_retrieval_measure --root PUBLIC_SOURCE_DIR --lab RETRIEVAL_LAB --output NEW_REPORT_JSON
python -m benchmarks.public_proposal_measure --root PUBLIC_SOURCE_DIR --lab GROUNDED_LAB --runtime PINNED_RUNTIME --model EXISTING_GGUF --expected-model-sha256 MODEL_SHA256 --expected-runtime-manifest-sha256 RUNTIME_MANIFEST_SHA256 --context-tokens 4096 --retrieval-strategy normalized --task booking_availability --task parcel_weight --output NEW_PROPOSAL_REPORT_DIR
~~~

Original measurement reproduction (at original pinned commit; no normalized flag):
~~~text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example grounded_lab
python -m benchmarks.public_proposal_campaign prepare --output NEW_PUBLIC_CAMPAIGN_DIR
python -m benchmarks.public_proposal_measure --root PUBLIC_CAMPAIGN_DIR --lab GROUNDED_LAB --runtime PINNED_RUNTIME --model EXISTING_GGUF --expected-model-sha256 MODEL_SHA256 --expected-runtime-manifest-sha256 RUNTIME_MANIFEST_SHA256 --context-tokens 4096 --output NEW_REPORT_DIR
~~~

Original narrow exact-text comparison [report](2026-11-27-exact-retrieval-ablation.md), code 258834305242b4f97a0fb2ebb261d951174cf65d, remains historical; legacy host candidate execution is disabled and must not be re-enabled. Preserve prior reports and controls.

## Final reporting and stop criteria

For each arm publish manifest hashes, exact commands/versions, task-level stage results and paired denominators, retrieval/support/span/distractor metrics, proposal readiness separately from semantics, candidate selection and regressions, timing/resource metrics, failure/blocked reasons and source integrity. Report uncertainty and exact lineage splits; no invented metrics. CI trusted controls/model-free tests do not equal model or containment qualification. Stop on unsafe memory, unauthorized path, stale evidence, failed qualification/cleanup, hidden scorer leakage, exhausted budget or inability to attribute outcome; do not fix by weakening gate. Review existing skills but no changes in this archive. The accepted research direction is conditional improvement of complete system intelligence under hardware and safety constraints; no authority to train, provision or publish.
