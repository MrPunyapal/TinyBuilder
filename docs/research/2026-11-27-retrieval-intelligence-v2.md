# Retrieval Intelligence v2

## Model-free comparison

Measured Rust lab code at `5a5adb85a0392c0b05d7b3f64e910972769401f2`
against the same twelve public source-only prompts and unchanged source
inventory from the [proposal campaign](2026-11-27-public-proposal-measurements.md).
The retrieval binary receives only a project path, a strategy and task text.
The separate Python scorer compares returned paths with the campaign's
required edit paths. The Rust executable never receives that list.

The arms are cumulative. Baseline is the existing selective retriever
with four terms and threshold 10. Threshold lowers the cutoff to 5.
Expanded raises the term limit to 32. Caseless folds content matches
while retaining substring matching. Normalized splits identifiers and
keeps exact tokens beside conservative plural and verb stems. Dependencies
adds one hop of same-directory, same-language static references from the top
lexical result. Fallback adds a complete code-only inventory only when no
path reaches the lexical cutoff and the result fits in four files and
12 KiB. There are no corpus aliases or task-specific ranking rules.

| Arm | Complete tasks | Required files | Target precision | Non-target files / bytes | Total context bytes | Median retrieval | Multi-file tasks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 1/12 | 1/14 | 100% | 0 / 0 | 247 | 1.56 ms | 0/2 |
| Threshold | 6/12 | 7/14 | 77.8% | 2 / 406 | 1,677 | 1.54 ms | 0/2 |
| Expanded | 11/12 | 12/14 | 63.2% | 7 / 1,352 | 3,353 | 1.95 ms | 1/2 |
| Caseless | 11/12 | 12/14 | 63.2% | 7 / 1,352 | 3,353 | 1.97 ms | 1/2 |
| Normalized | 12/12 | 14/14 | 58.3% | 10 / 1,890 | 4,178 | 2.43 ms | 2/2 |
| Dependencies | 12/12 | 14/14 | 58.3% | 10 / 1,890 | 4,178 | 3.09 ms | 2/2 |
| Fallback | 12/12 | 14/14 | 58.3% | 10 / 1,890 | 4,178 | 2.79 ms | 2/2 |

Target precision divides complete required paths by selected paths.
Non-target files are a proxy for extra context. Some contain useful
dependencies or unchanged source. Context bytes are summed across twelve
tasks. Latency is the median of per-task medians from three Rust calls,
excluding process launch. These timings come from one Windows host.

Rust reproduced the reported threshold and combined case-insensitive
results. Expanded terms alone reached the same coverage as caseless
matching. Both missed the two booking files. Identifier normalization
recovered both. Dependency and fallback did not add public-corpus coverage.
Separate synthetic fixtures check CamelCase and snake_case words, regular
inflection handling, a same-directory static dependency with an unrelated
name, and fallback eligibility and refusal. Keep normalized retrieval as
the smallest full-recall candidate on these fixtures. Review precision and
recall on additional independent repositories before considering promotion.
[Per-task measurements](../../benchmarks/results/2026-11-27-retrieval-v2.json)

## Review-only inference follow-up

After the deterministic comparison, the existing Qwen2.5-Coder 1.5B
Q4_K_M ran one trial on each multi-file task with the normalized arm,
exact-text edits, a 4,096-token context limit and the pinned b12359 CPU
runtime. Both calls received both required files. The initial preflight
held both models at 2,782 and 2,788 MiB available, respectively. The 1.5B
retry started with 2,890 MiB available. The research-only 3B had 3,263 MiB
after the 1.5B run and 3,449 MiB at the retry preflight, below its 3,500 MiB
preflight minimum for the prior 3.29 GiB sampled peak on this host. Both
planned 3B trials remain blocked with 0 attempted.

| Task | Proposal status | Startup | Proposal latency | Prompt / completion tokens | Sampled combined peak RAM |
| --- | --- | ---: | ---: | ---: | ---: |
| `booking_availability` | No change | 1.81 s | 6.84 s | 272 / 99 | 1.73 GiB |
| `parcel_weight` | Review-ready, approval withheld | 1.63 s | 4.58 s | 269 / 50 | 1.73 GiB |

The parcel proposal targeted one file. The experiment established
1/2 proposal readiness, with 0 applied patches and 0 semantic observations.
The harness verified that source files, weights and the runtime manifest
remained unchanged. This was CPU inference. No VRAM measurement was taken.
[1.5B measurement record](../../benchmarks/results/2026-11-27-retrieval-v2-proposals-1.5b.json)

## Checks

Local Windows checks passed: 45 Rust tests, 291 Python tests with two
skips, 37 acceptance unit tests, six agent guidance tests, the guidance
checker and Python compilation. The normal native CLI and the original
read qualification oracles match main at `ce28337552933a671a95d1ad30baa07cfe7cc2b7`.

## Reproduce

```text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example retrieval_lab --example grounded_lab
python -m benchmarks.public_proposal_campaign prepare --output NEW_SOURCE_DIR
python -m benchmarks.public_retrieval_measure --root PUBLIC_SOURCE_DIR --lab RETRIEVAL_LAB --output NEW_REPORT_JSON
python -m benchmarks.public_proposal_measure --root PUBLIC_SOURCE_DIR --lab GROUNDED_LAB --runtime PINNED_RUNTIME --model EXISTING_GGUF --expected-model-sha256 MODEL_SHA256 --expected-runtime-manifest-sha256 RUNTIME_MANIFEST_SHA256 --context-tokens 4096 --retrieval-strategy normalized --task booking_availability --task parcel_weight --output NEW_PROPOSAL_REPORT_DIR
```
