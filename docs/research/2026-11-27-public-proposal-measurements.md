# Public source-only proposal measurements

The twelve-task campaign uses existing public seeded classes, unchanged
task prompts, exact-text editing and the selective lexical retriever.
The plan and evaluator sources stay outside each task directory. Each job
has one proposal attempt. The measurement runner closes stdin, so the lab
cannot receive its required per-patch approval. No patch was applied.

The reviewed PR #23 checkpoint was
`e1e68ae894e322641bb431de81c236081d8920cb`. It merged into main at
`ce28337552933a671a95d1ad30baa07cfe7cc2b7`. The measurement changes were
carried forward byte for byte in `7f58a19` and `85433bc`. The pinned
b12359, model, plan and exact executable hashes are in the
[sanitized measurements](../../benchmarks/results/2026-11-27-public-proposals.json).

## Verified Windows runs

The development host has an i7-12700H, about 15.63 GiB physical RAM and a
4 GiB RTX 3050. Runs were sequential, on CPU. The GPU reported 0 MiB and
0% utilization in the pre/post readings for the bounded pair. Starting
available RAM was 4,042 MiB for 1.5B and 4,046 MiB for 3B. The 4,096-token
context is an explicit lab setting for the matched pair. The first 1.5B
run used the runtime default.

| Model / context | Tasks reached | Review-ready | Startup | Prompt / completion tokens | Proposal latency | Sampled combined peak RAM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.5B Q4_K_M / default | 12 | 1 | 3.36 s | 217 / 72 | 4.88 s | 2.49 GiB |
| 1.5B Q4_K_M / 4,096 | 12 | 1 | 1.75 s | 217 / 72 | 5.32 s | 1.72 GiB |
| 3B Q4_K_M research / 4,096 | 12 | 1 | 4.31 s | 217 / 72 | 12.81 s | 3.29 GiB |

Each row contains one actual inference call. Eleven tasks per run stopped
before starting the runtime because selective retrieval returned no
qualifying files. Only `group_inventory` retrieved an allowed complete
source file. That gave full allowed-file recall for 1/12 tasks and covered
1/14 allowed target paths. All three calls produced in-scope previews and
reached the approval boundary. Scope and readiness do not establish repair
correctness. No semantic observations were attempted. The model hashes,
runtime manifest and public campaign files were unchanged after each run.
The measurements contain timings and paths from reviewed public fixtures
and omit patch contents and raw model responses.

## Reproduce

```text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example grounded_lab
python -m benchmarks.public_proposal_campaign prepare --output NEW_PUBLIC_CAMPAIGN_DIR
python -m benchmarks.public_proposal_measure --root PUBLIC_CAMPAIGN_DIR --lab GROUNDED_LAB --runtime PINNED_RUNTIME --model EXISTING_GGUF --expected-model-sha256 MODEL_SHA256 --expected-runtime-manifest-sha256 RUNTIME_MANIFEST_SHA256 --context-tokens 4096 --output NEW_REPORT_DIR
```

## Next

Measure a retrieval-only comparison on the same natural-language tasks
before spending more inference. Keep evaluator-owned allowed targets out
of model context. Test the existing cutoff against a bounded, more
recall-oriented lexical control and compare whether all required files are
selected on multi-file tasks. Keep exact-text edits and both existing
weights fixed. An isolated evaluator remains required for execution and
behavioral scoring.
