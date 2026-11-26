# Cross-file Laravel pilot, 27 November 2026

One paired Windows CPU run evaluated two existing GGUF files on three original
cases: contact validation, seat eligibility and editor role checks. Arm A
received both relevant files. Arm C used repository retrieval with the same
edit schema and no target-path hint. Both arms required a single safe
replacement, so the pilot measures cross-file reasoning with a one-line repair.

| Model | Supplied A | Retrieved C | Total | Ready | Server peak working set | Driver + server sampled peak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen2.5-Coder 1.5B Q4_K_M | 0/3 | 0/3 | 0/6 | 1.86 s | 2.64 GiB | 2.62 GiB |
| Qwen2.5-Coder 3B Q4_K_M, research weights | 3/3 | 2/3 | 5/6 | 7.36 s | 4.45 GiB | 4.44 GiB |

| Model | Median A latency | Median C latency | Median A prompt / completion | Median C prompt / completion |
| --- | ---: | ---: | ---: | ---: |
| 1.5B | 4.88 s | 22.32 s | 257 / 83 tokens | 1,818 / 88 tokens |
| 3B | 6.83 s | 37.66 s | 257 / 53 tokens | 1,818 / 57 tokens |

Trial latency includes context selection, inference and proposal validation.
Inference used the bundled b12359 CPU runtime with GPU layers disabled.
All 91 whole-device RTX 3050 observations reported 0 MiB and 0% utilization.
The combined working-set value is sampled and can miss the server's
instantaneous peak. Token counts are reported by llama.cpp.

## Independent checks and failure attribution

The fixture baseline was `b8f1471d477b127cc62674e9f37110e2dc80d8c4` with
PHP 8.5.13, Laravel 13.43.0 and PHPUnit 12.5.45. Each case had a failing
behavior assertion and a passing regression assertion on the seeded baseline.
Both assertions passed with the reference repair, and a plausible wrong repair
failed the behavior assertion. The evaluator ran PHP lint and the two exact
PHPUnit tests for every accepted candidate. Five generated 3B patches passed
all three checks. All disposable fixture sources were restored, hidden tests
were removed, and the original Laravel checkout and both weights were unchanged.

Arm C supplied both complete required files in all six trials. It also supplied
unrelated README or Composer material and raised median prompt size by roughly
seven times. The 1.5B model produced five unmatchable replacements and one
syntactically valid preview beyond the permitted edit scope. The 3B contact
case passed with supplied source and failed exact replacement matching with
repository context. The measured failure occurred at replacement validation.
One paired trial cannot establish whether context noise caused it. There were
no missing-evidence, transport, timeout or evaluator failures. Rejected
previews have no independently scored PHP behavior outcome.

## Reproduce and follow up

Build from lab revision `7bb336cf823ce3cfe05196b08e5985c55dd3f3df`.
Use a clean marked disposable Laravel Git baseline with existing Composer
dependencies, the pinned CPU runtime and existing verified weights.

```text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example laravel_pilot
python -m benchmarks.laravel_pilot --suite coding-cross-file --baseline BASELINE --lab LAB --runtime RUNTIME --php PHP --model LABEL_15 MODEL_15 SHA_15 --model LABEL_3 MODEL_3 SHA_3 --output NEW_DIR
```

The [sanitized campaign data](../../benchmarks/results/2026-11-27-coding-cross-file.json)
contains the exact model, runtime manifest and executable hashes and all 12 trial
outcomes. This run used a Windows development host and local loopback inference.

Next compare the current retrieval arm with a bounded retrieval arm on
held-out fixtures. Include policy-value mutations to catch hard-coded copies
and add cases that genuinely require edits across two files. The scorer's
current subset and three-fixture corpus leave those capabilities open. Keep
model training deferred until repeated held-out comparisons separate model
reasoning from context selection and exact replacement generation. The 3B
research weights remain lab evidence; see the [publisher license](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct/blob/main/LICENSE).

The Windows exact-main 10/10 read qualification remains development-host
evidence. Windows standard-user trust and dependency checks, clean Ubuntu
x64 acceptance and clean Apple Silicon acceptance remain open under the
[clean-machine checklist](../CLEAN_MACHINE_ACCEPTANCE.md).
