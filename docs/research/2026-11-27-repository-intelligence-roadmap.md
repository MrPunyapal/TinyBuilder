# TinyBuilder Phase 4 — Repository intelligence engineering roadmap

Date: 2026-11-27; revised 2026-11-28. Companion [full report and reassessment](2026-11-27-intelligence-beyond-parameters.md), [ablation plan](2026-11-27-intelligence-ablation-plan.md). Owner accepted research direction and authorized documentation-only archival, not implementation changes or individual experiment approvals in this PR. All numerical gates are proposals; freeze/review before running. Preserve [AGENTS.md](../../AGENTS.md), [agent guide](../AGENT_GUIDE.md), both original behavioral and native read qualification oracles and read-only 0.1 scope.

## Part I — Original roadmap (historical)

Proposed milestone name Coding Intelligence v2 — Repository Intelligence. These are the original eight milestones, not an instruction to restart finished work.

| Stage | Objective | Proposed measurable gate |
|---|---|---|
| 1 Retrieval Recovery | Reproduce baseline, isolate threshold and vocabulary, bounded recall-oriented lexical arm; model-free | >=11/12 complete task recall and >=13/14 required edit paths, no weakened safety or original release gate |
| 2 Repository Intelligence | PHP symbols, namespace resolution, dependency edges, compact maps | Cross-file/paraphrase improvement within agreed resource budgets |
| 3 Evidence Compiler | Lossless relevant source, signatures/contracts, actual tokenizer budget | >=30% fewer median prompt tokens vs complete-file context where both fit, no essential evidence loss |
| 4 Deterministic Action Engine | Compare exact text, bounded transformations, simplified schemas | >=50% reduction in edit-realization failures on adequate matched development set |
| 5 Isolated Behavioral Qualification | Qualified isolated execution, independent behavioral oracles, both existing models | All mandatory containment probes pass, no ordinary-host fallback |
| 6 Adaptive Reasoning and Repair | Candidate sampling, targeted evidence refinement, feedback | >=10 percentage point paired behavioral gain vs frozen single-attempt baseline on expanded development evaluation, held-out confirmation |
| 7 Conditional Semantic Retrieval | Small local embeddings only if lexical/structural gaps remain | Material held-out recall or behavioral gain justifying complete resource/maintenance cost |
| 8 Conditional Specialization | Revisit Phase 2 only after residual attribution | Held-out behavioral gain under same resource and safety limits |

Proposed resource objectives (not results): <128 MiB repository index on defined medium project, warm lexical p95 <250 ms, cold indexing <5 s for 1,000-source-file project, proposal peak combined RAM <2.5 GiB 1.5B and <4 GiB 3B, fast <15 s, balanced <60 s, deep configurable hard 180 s. Verification overhead separate; budget available memory, not installed memory. Context compilation starts at 4,096 total tokens with 1,024 reserved generation; compare smaller allocation and actual template accounting. Avoid unbounded loops and multiple resident models.

Original parallel lanes: intelligence (lexical, retrieval-only benchmark, PHP AST, context compiler, inert/static proposal validation) and containment (portable sandbox, trusted isolation probes, permissions, resource enforcement, qualification). Meet at semantic scoring. Clean-machine 0.1 release is a separate gate.

### Historical Stage 1 assignment (superseded by measured Retrieval v2; preserve for provenance)

Act as senior Rust engineer and benchmark researcher. Read [current main](https://github.com/MrPunyapal/TinyBuilder), AGENTS.md, agent guide, status and skills; [original public measurements at 0fab9c6](https://github.com/MrPunyapal/TinyBuilder/commit/0fab9c6ae2b94dfb514287ded6275e72fadadcb9). Preserve uncommitted work, coordinate active owner.

Objective: remove retrieval bottleneck via deterministic improvements before inference. Preliminary recall 1/12 selective, 6/12 threshold, 11/12 expanded case-insensitive; reproduce independently rather than treating preliminary as Rust evidence.

Inspect context.rs, project.rs and grounded lab; reuse existing 12 source-only tasks; evaluator metadata outside model-facing roots. Compare threshold, case normalization, query selection, CamelCase/snake_case, path/identifier weighting, bounded fallback and BM25 if warranted individually, then combine. Record ranked files, delivered spans, recall, precision, tokens/estimates, truncation, latency/memory. Add paraphrases, short identifiers, distractors, unrelated-query abstention. Preserve negative results.

Gate >=11/12 complete, >=13/14 required edit paths, no task-specific answers/path hints or silent essential truncation, no wider permissions, unchanged read oracle, deterministic cheap CI, retain baseline. No training/downloads, generated code, VM/system/security changes, host restart or stopping workloads; no embeddings/AST graphs/swarm/specialization without separate reviewed experiment. Native product read-only; lab only. Report hashes, commands, task-level evidence, failures/blockers, knowledge maintenance; focused draft PR, no merge/release. Stop at retrieval-only checkpoint before further inference.

## Part II — Revised roadmap

New repository-reported evidence at [e4471558](https://github.com/MrPunyapal/TinyBuilder/commit/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14): normalized 12/12 complete tasks, 14/14 required files, 58.3% target precision, 2.43 ms median. Dependencies/fallback no coverage increment. Both multi-file tasks received both required files; 1.5B one single-file proposal ready, one no-change, no behavior; 3B blocked RAM threshold. [Grounded code](https://github.com/MrPunyapal/TinyBuilder/blob/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14/rust/src/grounded.rs#L122-L174) permits only one replacement/file; no inference about inherent multi-file inability. Freeze normalized development candidate; do not promote to product or maximize overfitted dev recall.

| Priority / stage | Work and owner boundary | Evidence/gate | Dependency |
|---|---|---|---|
| P0 / 1 | Freeze Retrieval v2, integration review in existing local branch/PR #26 | Preserve all seven arms and dev 12/12, 14/14; applicable exact-head CI and no scope/release regressions | Review by maintainer; local uncommitted work not visible remotely |
| P0 / 2 | Independent evidence qualification, existing retrieval owner | Proposed 30 tasks / >=6 lineages, >=90% complete evidence positive, >=95% edit span, no essential truncation/unauthorized reads, negative set and measured precision | Frozen corpus/ranker; model-free |
| P0 / 3 | Deterministic inert multi-edit transactions, separate maintainer-coordinated owner | All deterministic tests pass, combined diff, no unauthorized writes, stale/overlap/rollback controls | Existing exact-text and project guards; no generated execution |
| P1 / 4 | Memory-efficient sessions, coordinated local owner | Compare 2K/4K, resident runtime, bounded task state; reduced overhead or memory with no evidence or later quality loss | Reviewed deterministic session controls and manifest before live calls |
| P1 / 5 | Planning/decomposition and sequential-vs-batched editing | Material improvement over unplanned matched strategy; before containment only proposal validity/coverage/consistency | Multi-edit infrastructure, resource limits; live inference approval |
| Critical dependency / 6 | Independent contained behavioral qualification | All fresh isolation probes pass, actual task correctness/regressions, no host fallback | Phase 3 / separately approved Linux outer evaluator; no waiting for full portability if approved existing design can qualify |
| Conditional / 7 | AST/index/dependencies/semantic retrieval | Independent diagnosed failures and incremental held-out gain vs frozen normalized; complete resource costs | R1/R2 evidence, review dependencies |
| Deferred / 8 | New checkpoint selection and specialization | Residual attributable failures plus unchanged matched behavior/safety/resource evaluation | Phase 2 license/runtime/data/compute review and explicit approvals |

Stages 2 and 3 can proceed in parallel with coordinated ownership. Stage 6 is necessary for semantic claims, but not a prerequisite to model-free stages. Do not mislabel readiness or static consistency as correctness.

### Context precision and generalization

Separate edit targets, supporting contracts/callers/dependencies, and irrelevant distractors. 14/24 selected occurrences were edit targets; 10/24 non-target, 1,890/4,178 bytes; not every non-target is irrelevant. Existing two multi-file tasks have no extra file occurrences. Distinguish selected paths, actually delivered evidence spans/tokens and permission scope. Compile exact editable bodies plus lossless relevant signatures under token limits, and request further evidence or abstain if necessary. Include paraphrases, no-evidence controls, realistic distractors, vocabulary mismatch and larger independent lineages. Do not tune on final held-out set.

### Multi-edit transaction acceptance

Build on project identity, source hashes and exact matching. Keep single replacement baseline. Bounded inert transaction of path/old/new edits, virtual source with updates and provenance, same-file nonconflicting edits, multi-file edits, combined diff, explicit approval of exact final action, validation of fresh source and scope before any approved application. Deterministic controls for ambiguous matches, overlaps, changed paths/content, stale proposal, no-op, repeated or contradictory operations, cross-project binding, path escape, partial failure and rollback/recovery using trusted fixtures. Do not promise atomic cross-file filesystem changes or hostile-concurrent-writer security. No execution of generated code; no automatic application to user's ordinary projects. Preserve human authorization semantics; exact permission reviewed per action, not broad plan permission.

### Task decomposition and runtime direction

One resident verified runtime, compact plan as a hypothesis, focus on one semantic operation per call, update virtual state, check dependent contract and unresolved obligations, assemble candidate. Do not force edits to all retrieved paths. Use bounded task-local state (requirement, evidence/hash, plan, completed operations, obligations, remaining budget), not growing conversation or persistent memory. Keep exact-text and single-edit baseline. Measure batched vs sequential vs plan+sequential with curated-plan diagnostic. Compare 2,048 and 4,096 capacity first; 1,024/8,192 conditional; actual tokenizer/overhead and no silent evidence truncation. Reuse saves startup, not automatically peak RAM; release at finish/cancel/bounded idle. Sequential not parallel models. Investigate pinned runtime slots/cache/batch only if supported; no runtime upgrades or GPU/system changes implicit. Keep preflight 3,500 MiB 3B threshold; previous 3,449 MiB blocked, do not weaken to run. 1.5B latest peak ~1.73 GiB, proposal 4.58–6.84 s, startup ~1.63–1.81 s. Compare matched task success per time/memory, not unrelated latency or raw call count.

### Phase 3 coordination

[Phase 3 archive draft #25](https://github.com/MrPunyapal/TinyBuilder/pull/25) proposes Rust-native Wasmtime/WASI experimental worker; PHP.wasm/Wasmer compatibility separately, exact Laravel parity unproven. Same-user worker not outer OS security boundary. Keep [approved Linux evaluator design](2026-11-27-contained-qualification.md) and independent black-box observation bridge; no live qualification asserted. Ordinary CI, worktree, approval and syntax checks are not containment. No generated candidate admission without separately approved outer boundary, fresh trusted probes, exact runtime/image identities, hidden scorer isolation, cleanup verification and explicit authorization. No private fixtures/outputs transferred absent approval; no personal Windows provisioning.

### Ownership and next integration checkpoints

At archive main [ce283375](https://github.com/MrPunyapal/TinyBuilder/commit/ce28337552933a671a95d1ad30baa07cfe7cc2b7). PR [#26](https://github.com/MrPunyapal/TinyBuilder/pull/26) owns Retrieval v2 and planned independent source-only evidence; its body assigns separate multi-edit protocol to maintainer. PR [#25](https://github.com/MrPunyapal/TinyBuilder/pull/25) Phase 3 documentation. The owner should reconcile exact-head CI and active local work before assignment; no competing branch or duplicated experiment. Review the archival draft independently. Canonical project status is stale; not modified here. Native clean-machine release remains independent and not authorized.

## Historical revised Codex assignment (November 28)

Act as TinyBuilder's senior Rust engineer and benchmark researcher. Read guidance, current main, skills, [e4471558](https://github.com/MrPunyapal/TinyBuilder/commit/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14) and Phase 4; verify branch/PR/CI state, preserve uncommitted work. Normalize candidate already 12/12, 14/14; no more repeated dev tuning. Precision 58.3%; no extra coverage from dependency/fallback. Both files in each multi-file task; one single-file ready, one no-change; one-edit interface means no inherent model conclusion. 3B blocked.

Workstream A: freeze normalized and build independent public fixtures with realistic distractors, vocabulary mismatch, cross-file dependency, paraphrases and no-evidence controls; approximately 30 tasks / six lineages. Score edit targets, support, irrelevant source, file/span recall, tokens/truncation/latency/resources. No embedding or graph machinery unless independent failure supports it.

Workstream B (only with coordinated separate owner): extend exact text into bounded inert transaction; test multi-file, multiple same-file edits, overlap/ambiguity, stale and unauthorized paths, updated virtual state, combined review, safe trusted application/failure recovery. Retain baseline; no generated execution.

Prepare matched single-edit, batched multi-edit, sequential exact, compact plan+sequential and curated-plan control; 2K/4K and resident/repeated startup, compact state vs history. Do not weaken RAM thresholds. Stop at deterministic infrastructure and independent retrieval checkpoint for review before next live inference.

No model downloads/training, personal host provisioning/system changes, generated execution outside qualified containment, original oracle changes, product writes/exec, unapproved merge or release. Report commits, exact commands/results, negative evidence, resource observations, limitations; knowledge-maintenance closeout. This is preserved historical assignment wording; current ownership must be coordinated with PR #26 and maintainer. Not a new implementation instruction from the archival PR.

## Stop conditions and knowledge maintenance

If independent recall weak, diagnose threshold/terms/spans/relationships before graph/embedding; if oracle evidence does not help, inspect reasoning/realization; if typed operations help, retain simpler interface; if selector fails despite candidate availability, improve selection not training; if memory preflight fails, keep blocked and optimize safe configuration without changing threshold; if no approved qualified verifier, continue source-only work and report no semantic score. Escalate model size/training only with named owner approval and residual failure evidence. Preserve unsuccessful approaches, prior source-ID/line negative evidence, task denominators, model hashes and licenses. Existing implementation and benchmark skills cover scope/approval; proposed refinements for expressiveness and delivered evidence are deferred to maintainers, not edited in this archival scope.
