# Model specialization — executive summary

Date: 2026-11-27 (Asia/Kolkata). Status: research proposals, not authorization. Read the [complete report and archival reconciliation](2026-11-27-model-specialization-deep-research.md), [dataset pipeline](2026-11-27-training-data-pipeline.md) and [roadmap](2026-11-27-model-specialization-roadmap.md).

## Decision requested

Do not train yet. Finish the existing Coding Intelligence v1 workstream, establish a contained executable private benchmark, and measure edit protocols and retrieval with existing weights. Only request new model downloads after candidate metadata, license, runtime and evaluation gates are ready. Only request training if repeatable model-attributable behavioral errors remain after qualifying pretrained candidates. Preserve native 0.1 read-only and its unchanged 10/10 oracle; clean-host acceptance remains separate.

## Evidence, classified

- **Verified repository facts during archiving:** main at [9d4343141bab4d710f7d16450105673c994d5c51](https://github.com/MrPunyapal/TinyBuilder/commit/9d4343141bab4d710f7d16450105673c994d5c51), active remote coding branch at [56889a82876d15362a54245e0e33eeabd8141012](https://github.com/MrPunyapal/TinyBuilder/commit/56889a82876d15362a54245e0e33eeabd8141012). PRs #18, #20, #21 were open drafts. Read AGENTS.md, agent guide, status, model-research, benchmark and knowledge-maintenance skills. Local uncommitted state not available.
- **Repository-reported measurements, not reproduced here:** [cross-file pilot](https://github.com/MrPunyapal/TinyBuilder/blob/c536508bdb1345b380ac2c88e01640120e70d25e/docs/research/2026-11-27-cross-file-validation.md) 1.5B 0/6, research 3B 5/6; narrow one-line repairs with cross-file evidence. [Exact retrieval ablation](https://github.com/MrPunyapal/TinyBuilder/blob/56889a82876d15362a54245e0e33eeabd8141012/docs/research/2026-11-27-exact-retrieval-ablation.md) 12/12 trials completed with full required-file recall. 1.5B 0/3 in each retrieval arm, all six pre-behavior failures; 3B 3/3 in each arm. Prompt tokens 1,818 to 258, latency 19.75 to 3.75 s and 38.40 to 9.65 s respectively; sampled peak driver + server RAM 2.66/4.50 GiB. No general multi-file claim.
- **Negative evidence:** model-selected line protocol accepted no repairs in prior ablation; source-ID experiment first attempt stopped at a failed known reference before inference. [Handoff](https://github.com/MrPunyapal/TinyBuilder/blob/56889a82876d15362a54245e0e33eeabd8141012/docs/research/2026-11-27-next-phase-handoff.md) reports PHP CLI OPcache fix and local retry. Trusted public/private corpus controls passed 12/12 and 2/2; contained evaluator model-free tests 10/10; live isolated guest/image and safety smoke tests remain required.
- **Previously accepted direction:** [PR #21 decisions](https://github.com/MrPunyapal/TinyBuilder/blob/a0c4fe0b6ee254da6afbe8e0801350f332210f31/docs/research/2026-11-27-coding-v1-decisions.md) retain existing controls, lexical then structural retrieval, model-selected targets, independent behavior and approval boundaries. PR #21 is still draft, not merged policy. Phase 2 proposes a new candidate ordering, not a new implementation or release plan.
- **Hypothesis:** behavioral specialization (evidence selection, structured actions, repair after tests) offers better value than memorizing Laravel. Test, do not assume.

## Candidate order for qualification, not a measured ranking

| Candidate | Reported license | Role / unresolved |
|---|---|---|
| [Qwen2.5-Coder 1.5B Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct) | Apache-2.0 | Existing low-resource baseline; preserve release gate. |
| [Qwen2.5-Coder 3B Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct/blob/main/LICENSE) | Qwen Research License, non-commercial absent separate license | Existing research-only control; not product base or unrestricted redistribution. |
| [MiniCPM5-2B](https://huggingface.co/openbmb/MiniCPM5-2B) | Apache-2.0 reported | First proposed new candidate; actual 2.516B parameters; publisher reports SWE-bench Verified 46.4, BFCL v4 66.6, LiveCodeBench v6 69.1; other reported agent scores much lower. [Official GGUF](https://huggingface.co/openbmb/MiniCPM5-2B-GGUF/tree/main). |
| [Granite 4.2-3B](https://huggingface.co/ibm-granite/granite-4.2-3b) | Apache-2.0 reported | Second new candidate; reported BFCL v4 52.41; no 3B SWE-bench score in cited card. [GGUF](https://huggingface.co/ibm-granite/granite-4.2-3b-GGUF/tree/main). |
| [Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B) | Apache-2.0 reported | Quality ceiling; multimodal overhead; [GGUF](https://huggingface.co/ggml-org/Qwen3.5-4B-GGUF) ~3.03 GB Q4_K_M. |
| [Phi-4-mini](https://huggingface.co/microsoft/Phi-4-mini-instruct) | MIT reported | Optional independent control, community GGUF provenance needed. |
| [OpenCoder 1.5B](https://huggingface.co/infly/OpenCoder-1.5B-Instruct) | Publisher describes permissive commercial use; exact terms pending | Secondary code-specialist control. |
| [Qwen2.5-Coder 7B](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF) | Apache-2.0 reported | Upper bound only if justified. |

Publisher benchmarks are not TinyBuilder results; no independently verified Laravel results for the new candidates. Verify exact model and GGUF license text, attribution/NOTICE, revision, artifact hash, template, conversion path and pinned llama.cpp support before any download request. No candidate is approved by this report.

## Hardware and method disposition

Target Windows 11/i7 12th gen/16 GB RAM/RTX 3050 4 GB. CPU inference established for narrow existing trials, not general usability. Local 0.5B QLoRA plausible, 1.5B constrained, 2–2.5B uncertain; conventional 3B+ training impractical on 4 GB. Start with rank 8/16, 1K context, microbatch 1, accumulation 8–32, checkpointing if later authorized; NF4 frozen training base is not GGUF inference. Free Kaggle/Colab may offer larger GPUs, variable quotas and session loss; confirm actual entitlement, cost and privacy first. Soup's 4 GB result predates a correctness repair, not proof. See full report and roadmap for estimates and caveats.

| Disposition | Methods |
|---|---|
| Adopt now as research procedure | Matched harness controls, deterministic independent verifier, provenance and split checks, compact context, failure attribution |
| Adapt after approval | SWE-smith executable mutations, SWE-agent environment lessons, rejection-sampled successful trajectories, PEFT/TRL QLoRA SFT, test-feedback curriculum |
| Defer | DPO, RLVR/GRPO, large teachers/distillation, Axolotl scaling, 7B, embeddings, Soup streaming experiments |
| Reject as primary strategy | Full training on target GPU, indiscriminate scraping, framework memorization, leaderboard-only selection, unsafe tool widening |

## Priority order and approval boundaries

1. Existing agent records source-ID retry and exact-head CI; finish containment and independent private task controls. Do not duplicate its work.
2. Freeze and compare edit representation and bounded retrieval separately; measure actual multi-file behavior and generalization.
3. Prepare license/runtime/model metadata and budget dossier; seek explicit permission for sequential candidate downloads (MiniCPM, Granite, then conditional Qwen3.5).
4. Run frozen matched qualification; prefer smallest passing system. Authorize no training if harness/pretrained gains suffice.
5. Prepare a small licensed original dataset, then separately request one calibrated QLoRA SFT pilot if residual errors justify it. Compare untouched base, two seeds, no weakened oracle. Stop if gains fail the agreed gates.

Numerical gates in the full report are proposed post-training promotion and stop criteria, not evidence or accepted engineering policy. No production source or canonical status changes; proposed procedural extension in roadmap. No new weights, training, compute, merging or release actions.
