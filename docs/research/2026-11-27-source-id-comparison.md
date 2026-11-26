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
