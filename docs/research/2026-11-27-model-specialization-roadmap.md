# Model qualification and specialization roadmap

Date: 2026-11-27. All new experiment thresholds and training settings are proposals for maintainer review. [Full report](2026-11-27-model-specialization-deep-research.md) · [Summary](2026-11-27-model-specialization-summary.md) · [Data pipeline](2026-11-27-training-data-pipeline.md).

## Dependencies and ownership

Do not create a competing implementation. Current main verified at 9d4343141bab4d710f7d16450105673c994d5c51; remote coding branch [56889a82876d15362a54245e0e33eeabd8141012](https://github.com/MrPunyapal/TinyBuilder/commit/56889a82876d15362a54245e0e33eeabd8141012). Local Codex owns source-ID retry and successor PR; PR #21 owns status refresh. [Phase 1 decision record](https://github.com/MrPunyapal/TinyBuilder/blob/a0c4fe0b6ee254da6afbe8e0801350f332210f31/docs/research/2026-11-27-coding-v1-decisions.md) retains existing baseline/control, bounded lexical retrieval first and independent scoring. Native read-only 0.1 acceptance remains independent and unchanged.

| Stage | Work and dependency | Exit evidence / decision |
|---|---|---|
| P0, current agent | Record all planned source-ID trials or blocked status, preserve first failed reference and OPcache fix, exact-head CI. Do not duplicate active runs. | Distinguish environment, parse, target, matching, scope, application, behavior and regression failures. |
| P0, containment | Freeze verified isolated guest/image; smoke deny network, writes outside root, unauthorized argv, resource escape; validate corpus controls before model-generated PHP. | Trusted controls pass; unsafe cases fail closed. No private model evaluation before this. |
| P1, protocol | Existing 1.5B and 3B, same evidence and task, compare exact text, snapshot-bound IDs/ranges, structured proposal. Operator-selected target diagnostic only. | Measure unconditional behavior and conditional accepted-patch behavior, no scope regression; preserve all attempts. |
| P1, retrieval | Fixed protocol: supplied-evidence diagnostic vs lexical baseline, selective lexical, then bounded PHP symbols/dependency hints if needed. | Full recall/precision evidence, context tokens, p50/p95 latency, behavior and resource trade-off across unseen repos. No default cutoff promotion from three cases. |
| P2, pre-download dossier | Freeze candidate list, artifact revision/hash, license and notices, runtime/template and quantization support, estimated download size/disk, test budget and approval. | Maintainer approves named sequential downloads. No automatic pulls. |
| P2, base qualification | MiniCPM5-2B then Granite 4.2-3B; optional Qwen3.5-4B ceiling, Phi/OpenCoder if justified; unchanged controls. Freeze tasks, same budgets and controller, record model-specific template differences, deterministic seeds, CPU and supported offload. | Smallest legally redistributable passing model/system; verify Q4 vs higher precision only if approved and relevant. No training if adequate. |
| P3, pre-training dossier | Residual repeated model-attributable failures, verified original/licensed trajectories, locked independent splits, measured candidate performance, feasibility and compute/privacy plan. | Separate explicit approval for one bounded SFT experiment; no post-training gain required before training, only evidence of a correctable deficit and a pre-registered evaluation plan. |
| P3, approved calibration/SFT | 0.5B feasibility probe or qualified 1.5B–2.5B base, QLoRA, PEFT/TRL or measured Unsloth path. Rank 8/16, microbatch 1, short context, checkpointing; calibrate then decide full pilot. | Report peak RAM/VRAM, measured tokens/sec, OOM, swapping, storage, elapsed time; untouched base and adapter in same serving format. |
| P4, conditional escalation | Verified SFT gain but preference ranking gaps: rejection-sampled pairs/DPO. RLVR only if verifier mature and SFT/DPO plateau. | Separate approval and measured incremental value. No indefinite optimization. |

## Hardware plan (estimates, not measurements)

Windows 11, i7 12th gen, 16 GB RAM, 4 GB RTX 3050. Inference file size differs from whole-process RAM and KV/context; Q4_K_M GGUF is not NF4 training storage. Existing CPU reports peak 2.66/4.50 GiB driver+server on narrow 1.5B/3B tests. See [ablation](https://github.com/MrPunyapal/TinyBuilder/blob/56889a82876d15362a54245e0e33eeabd8141012/docs/research/2026-11-27-exact-retrieval-ablation.md).

Illustrative planning calculation: frozen base loading estimate 0.9 bytes/parameter + 1.4 GB runtime from [Unsloth estimator](https://github.com/unslothai/unsloth/blob/main/studio/frontend/src/lib/vram.ts) is calibrated on different hardware and does not prove fit. Additional activation/workspace, adapters and optimizer headroom required. Use decimal GB for this arithmetic; compare actual available GPU memory, not advertised capacity. FP16/BF16 base file ~2 bytes/parameter before metadata; merged weights, caches, checkpoints and GGUF add disk. An illustrative 10M trainable adapter parameters at 2 bytes weights + 2 gradients + 8 FP32 Adam moments + optional 4 FP32 master weights = ~120–160 MB before implementation overhead. Quantized/paged optimizer may change this. Adapter count depends on rank and actual target matrices (sum of r*(in+out)); compute from candidate architecture. Activations depend on layers, sequence, kernel, checkpointing, logits and microbatch; no precise activation estimate verified. Measure instead of subtracting GGUF size from VRAM.

| Parameters | Illustrative load+runtime GB, before added training state | Local plan | FP16/BF16 source payload estimate |
|---|---:|---|---:|
| 0.5B | 1.85 | Plausible short-context probe, not measured | 1 GB |
| 1.5B | 2.75 | Tight; rank 8/16, microbatch 1, 512–1024 tokens initially | 3 GB |
| MiniCPM 2.516B | 3.66 | Uncertain/likely insufficient headroom; prefer free external GPU if approved | 5.03 GB |
| 3B | 4.10 | Conventional local QLoRA impractical; offload experimental | 6 GB |
| 4B | 5.00 | Do not plan conventional local training | 8 GB |
| 7B | 7.70 | Reject on target absent new evidence | 14 GB |

Reserve space for at least source + temporary/merged checkpoint + GGUF + adapters, dependencies and dataset; a provisional 20–40 GB free disk for small pilots (measure actual files first), larger for 3–7B. CPU offload can pressure 16 GB RAM and PCIe; stop persistent swapping or excessive offload. Start 1K context, accumulation 8–32, effective tokens/update ~8K–32K for full sequences; account for padding and masking. A 5M processed-token pilot at measured 20/50/100 tokens/s would take ~69/28/14 hours of training alone; these rates are illustrative, not observed. Calibrate 500–1,000 steps only within approved token/time budget (smaller 50–100-step memory smoke first); distinguish microsteps and optimizer updates. Extrapolate actual effective tokens/s and include evaluation, checkpoints, conversion and teacher generation separately. Stop OOM or unacceptable resource pressure rather than escalating automatically.

[QLoRA](https://arxiv.org/abs/2305.14314) freezes quantized base, trains adapters; [LoRA](https://arxiv.org/abs/2106.09685), [PEFT](https://huggingface.co/docs/peft/package_reference/lora), [TRL](https://huggingface.co/docs/trl/index). Verify backend support for exact architecture, conversion/merge and final quantized serving behavior. Soup [README](https://github.com/nullartist/soup/blob/main/README.md) documents un-retested 4 GB claim after correctness repair. Do not adopt as established feasibility.

Free resources: [Kaggle](https://www.kaggle.com/docs/notebooks) and [Colab](https://research.google.com/colaboratory/faq.html) first, dynamic quotas and session interruptions; [Lightning](https://support.lightning.ai/pricing/) initial credits only, no billing or card required for proposed path; [ZeroGPU](https://huggingface.co/docs/hub/main/spaces-zerogpu) not sustained training. Original report's specific accelerator/time/credit claims are time-sensitive and not account-verified. Verify no billing, session quota, GPU capability, storage retention, privacy and allowed usage before any approval. Public/original cleared training data only, no private holdout or secrets in external service.

## Evaluation and proposed gates

Use 30–50 development tasks and 60–100 locked private tasks across multiple lineages and disjoint subfamilies, stratify actual multi-file modifications and test-feedback. Public three-case smoke is not promotion evidence. Use development for selecting model/protocol/checkpoint; private confirmatory comparisons pre-registered. Same untouched base vs trained adapter and post-merge quantization; report paired per-task outcome and confidence interval (cluster by repo lineage where possible), denominators, failures and missing trials. Distinguish safety violations attempted vs actually executed; actual unauthorized action is a hard stop.

| Metric | Proposed post-training promotion | Product-oriented target / stop |
|---|---|---|
| Valid structured action / applied intended revision | ≥95% each | ≥98%; <90% after protocol tuning diagnose first |
| Behavioral success | ≥10 percentage points vs untouched base with meaningful paired evidence | ≥60% private Laravel; <5-point gain after two seeded runs stop |
| Unseen lineages | Gap ≤15 points from overall | Gap ≤10 points; stop same-lineage-only improvement |
| Genuine multi-file | Improvement vs base | ≥50% subset; stop if no gain after controls |
| Feedback repair | ≥20% of initial failures recovered within fixed retry budget | ≥40%; stop repeated identical failures |
| Regression preservation | ≥98% on accepted proposals; also unconditional task pass | ≥99%; systematic regression blocks promotion |
| Tool choice / hallucinated action | ≥90% / ≤2% | ≥95% / ≤1%; >5% hallucinated action diagnose |
| Whole-system process RAM | ≤12 GB preferred, report peak | ≤8 GB desirable; no persistent swapping |
| Inference VRAM | ≤4 GB for supported GPU mode; CPU-only viable | Measure total device/process VRAM and reserve |
| Latency | p50/p95 task and round, cold/warm, CPU and offload | Common p50 round ~30 s target; >2× baseline without meaningful accuracy gain stop |
| Model footprint | Exact weight/runtime sizes and context budget | Prefer smaller if larger gains <5 points while doubling latency/memory |
| Safety and rights | No actual unauthorized actions; unchanged release gate; exact permissive license and attribution review | Hard block if violated |

Training authorization is separate from post-training promotion. Stop if structured outputs improve without behavior, data leakage, weak verifiers, safety failure or costs exceed approved budget. Use a second controlled seed only within approval; do not keep training until a result appears. No claim of statistical significance from three smoke tasks.

## Knowledge maintenance — proposed changes only

Reviewed [model-research skill](../../.agents/skills/tinybuilder-model-research/SKILL.md), [benchmark skill](../../.agents/skills/tinybuilder-benchmark/SKILL.md), [knowledge-maintenance](../../.agents/skills/tinybuilder-knowledge-maintenance/SKILL.md), [AGENTS](../../AGENTS.md), [agent guide](../AGENT_GUIDE.md), and [status](../PROJECT_STATUS.md). Existing skills already cover license, lineage, untouched-base comparison, independent controls, resource capture and approval. Do not add two redundant skills as originally suggested; no AGENTS index change needed. No canonical status refresh competing with #21. Proposed addition to existing model-research skill after maintainer review and stable evidence:

> Before requesting candidate downloads, prepare a revision-pinned license/NOTICE, GGUF provenance, runtime/template support, size and evaluation-budget dossier. For dataset work, assign repo lineages and task subfamilies to splits before generation; record source rights, mutation/verifier revisions, reference and wrong-repair controls, and traceable derived IDs. Keep hidden oracles and private holdouts outside model context. For an approved adapter pilot, separate frozen quantized base, activations, adapters, optimizer and offload budgets from GGUF inference; run a bounded memory/throughput calibration. Pre-register untouched-base and quantized serving comparisons and stop rules. Treat numerical thresholds and candidate order as research proposals until accepted.

This is proposed procedural text, not an accepted change; no skill or guideline modified. Run python .agents/check_guidance.py after any future adopted change. Guidance validation is still applicable as an archival check if execution is available. No tests or inference run by authoring this roadmap.

## Maintainer decisions required

Review/archive research; approve any canonical skill change, private corpus and containment criteria, new model downloads one by one, actual qualification gates and resource budgets, any cloud data transfer, then any separate calibrated training authorization. No merge/tag/release/paid compute authorized here.
