# Retrieval comparison with exact-text edits

The [earlier Coding Intelligence v1 run](2026-11-27-coding-v1-experiment.md)
showed smaller prompts with selective retrieval, but both retrieval arms
used the model-selected line protocol and accepted no repairs. This follow-up
uses the existing exact-text edit schema in both arms and changes only the
lexical score cutoff. It reuses the three original smoke cases.

## Experiment

- **L** uses the baseline lexical ranking and the existing four-file cap.
- **S** uses that ranking and cap with a minimum score of 10.
- Both use the pinned b12359 CPU runtime, the same existing Qwen2.5-Coder
  Q4_K_M GGUFs, temperature zero, and a 1,024-token replacement cap. Trials
  run once in L/S order except the seat case, which uses S/L for both models.
- The evaluator checks complete required-file recall, scope and safety,
  then PHP lint and independent Laravel PHPUnit behavior and regression
  assertions on accepted previews. Each fixture also exercises seeded,
  reference, and plausible wrong controls. The three-fixture count limits
  conclusions about performance on unfamiliar repositories.

Build the lab from `258834305242b4f97a0fb2ebb261d951174cf65d`. Supply a
marked disposable Laravel baseline with existing Composer dependencies.
Reuse the approved model and runtime digests from the earlier experiment.

```text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example laravel_pilot
python -m benchmarks.laravel_pilot --suite coding-retrieval-exact --baseline BASELINE --lab LAB --runtime RUNTIME --php PHP --model LABEL_15 MODEL_15 SHA_15 --model LABEL_3 MODEL_3 SHA_3 --output NEW_REPORT_DIR
```

## Verified Windows results

All 12 planned trials completed. Both retrieval arms supplied both complete
required files in every trial. All six accepted repairs passed PHP lint and
independent Laravel behavior and regression assertions. The 1.5B failed
replacement matching four times and exceeded the permitted edit scope twice.
The six 1.5B trials ended before behavioral scoring. There were no missing
trials, runtime failures, or evaluator errors. The three disposable fixtures
were restored, their hidden tests removed, and both model hashes matched
after the run.

| Model | L / S passes | L / S median prompt tokens | L / S median completion tokens | L / S median trial latency | Startup | Peak sampled driver + server RAM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1.5B Q4_K_M | 0/3 · 0/3 | 1,818 · 258 | 88 · 88 | 19.75 s · 3.75 s | 1.72 s | 2.66 GiB |
| 3B Q4_K_M research | 3/3 · 3/3 | 1,818 · 258 | 53 · 129 | 38.40 s · 9.65 s | 3.33 s | 4.50 GiB |

The cutoff reduced median prompt tokens by 85.8% for each model. The 3B
used more completion tokens in the selective arm and still finished faster
on these cases. The RTX 3050 reported 0 MiB and 0% utilization in 32
whole-device samples. [Trial evidence](../../benchmarks/results/2026-11-27-exact-retrieval-ablation.json) ·
[GPU observations](../../benchmarks/results/2026-11-27-exact-retrieval-gpu.json)

## Decision and follow-up

Keep selective lexical retrieval with exact-text edits as a lab candidate.
It preserved recall and verified behavior on these three fixtures. Repeat
on unseen repositories before promoting the cutoff, and keep the 1.5B
results visible when choosing a protocol. Test explicit source identifiers
against the existing representation on smoke fixtures. Broader testing of
model-generated PHP still requires a contained runner and private holdout.
Keep model downloads and training deferred. Native 0.1 clean-host release
qualification remains a separate gate.
