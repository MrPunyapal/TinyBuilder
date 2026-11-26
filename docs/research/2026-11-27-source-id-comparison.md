# Snapshot-bound source identifier comparison

## Frozen setup

The [exact-retrieval comparison](2026-11-27-exact-retrieval-ablation.md)
found full recall and 3/3 behavior passes per arm for the 3B, plus
pre-scoring edit failures for the 1.5B. This experiment holds the supplied
source evidence fixed for the two primary arms and changes how the model
specifies the edit. It reuses the three smoke fixtures from the earlier
study. These fixtures are development diagnostics.

| Arm | Context | Proposal |
| --- | --- | --- |
| A | Both complete relevant files | Exact-text replacement with model-selected path and old fragment |
| B | Same two files, with one identifier per nonblank source line | Model-selected identifier and a single replacement line |
| C | Operator-selected file and line | Existing operator-location diagnostic |

In B, the identifier maps to a line in the request's complete read
snapshot. The lab adds the original indentation and verifies the edited
file's digest through the existing project patch guard. The model sees no
designated target or repair. Unknown identifiers, multiline payloads and
stale snapshots fail closed. A proposal does not apply itself. The
automated independent evaluator runs only its existing reviewed PHP
subset in disposable fixtures. It requires PHP lint plus behavior and
regression evidence for each pass.

The experiment was frozen at `62463fbbc31e4806ad60257144bc75c40066d21a`.
The order is A/B/C except for the seat case, which runs B/A/C. Inference
uses temperature zero, a pinned b12359 CPU runtime, and existing
Qwen2.5-Coder Q4_K_M 1.5B and 3B weights with preselected hashes.
The existing A/B generation budget is 1,024 tokens. C uses its existing
512-token budget. The two models run sequentially. There are no retries.

Incomplete responses keep only a fixed finish-reason label and available
token counters. Raw responses and arbitrary backend labels stay out of
the report. The completed study records all attempted and missing trials.

```text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example laravel_pilot
python -m benchmarks.laravel_pilot --suite coding-source-ids --baseline BASELINE --lab LAB --runtime RUNTIME --php PHP --model LABEL_15 MODEL_15 SHA_15 --model LABEL_3 MODEL_3 SHA_3 --output NEW_REPORT_DIR
```

## Verified results

The first attempt stopped before inference on a failing reference. The
retry used `9585b26d61c04e7000e0dac29df20be986931a74` to disable CLI
OPcache for rewritten-source controls. It passed the seeded, reference,
and wrong-repair controls and completed all 18 planned trials.
[Blocked attempt](../../benchmarks/results/2026-11-27-source-ids-initial-blocked.json) ·
[Completed trial evidence](../../benchmarks/results/2026-11-27-source-ids.json)

| Model | A exact text | B source ID | C operator control | Median prompts A/B/C | Median completions A/B/C | Median latency A/B/C | Peak sampled driver + server RAM |
| --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| 1.5B | 0/3 | 0/3 | 1/3 | 257 / 241 / 192 | 83 / 31 / 21 | 4.86 / 3.81 / 2.48 s | 2.50 GiB |
| 3B | 3/3 | 0/3 | 1/3 | 257 / 241 / 192 | 59 / 32 / 22 | 7.75 / 6.41 / 4.93 s | 4.30 GiB |

All six source-ID proposals resolved to a source location and then failed
PHP lint. The trial report preserves the syntax rejections without model
text. These results establish a replacement-output bottleneck for this
representation. They leave PHP behavioral correctness unmeasured in arm B.
All five accepted edits passed independent behavior and regression tests.
There were no incomplete responses in the retry. Both existing weight
hashes were preserved.

Keep exact-text editing with selective retrieval as the leading lab
baseline. Before another representation trial, isolate the replacement
grammar from location selection, and use the contained evaluator for
broader scoring after guest qualification.
