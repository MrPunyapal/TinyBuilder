# Independent retrieval confirmation

The seven strategies remain frozen at
`e4471558a55e8cc0475c8ab8d9fc68bb8d008c14`. The 12 earlier public tasks
are development evidence. The independent queries and authored source
inventory were committed before scoring at
`b4949dd6ab0dd38ad5b63a0e29792e2034221d04`. No ranker was changed for this
evaluation. The source-only fixtures make no claims about runtime
framework behavior or repair correctness.

The main suite has **32 tasks across six Laravel-style lineages**, including
seven no-evidence controls. The supplementary Python and Rust projects add
24 tasks and four no-evidence controls. Each project has a separate root
and inventory (9–38 source files), with eight lineages and 156 files total.
The tasks use vocabulary mismatch, alternative names, same-name modules,
cross-directory references, distractors and three essential spans in long
source files. These are small authored repositories, so generalization to
full-size production repositories remains open.

The scorer separately labels candidate edit loci, necessary supporting
evidence, known distractors and unjudged source. An edit locus is the
reviewer's designated site for a potential change. No reference patch or
target path is sent to the executable. Each Rust subprocess starts inside
the corresponding source root and receives only its root, strategy and
question. A path hit measures the delivered ranking. An evidence hit
requires the whole file, or its explicitly required source line for one of
three long-file cases. Scores use the actual delivered ranges. Token
estimates are bytes divided by four, rounded up per file. They omit prompt
framing and are not tokenizer measurements.

## Results

| Strategy | Laravel complete / 25 | Overall complete / 45 | Path hits / 65 | Evidence hits / 65 | Long spans / 3 | Precision | No-evidence abstention / 11 | Context bytes | Median ms | Peak MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Baseline | 9 | 13 | 25 | 22 | 0 | 51.0% | 9 | 47,112 | 4.56 | 6.82 |
| Threshold | 14 | 21 | 40 | 37 | 0 | 47.6% | 9 | 53,829 | 5.28 | 6.81 |
| Expanded | 17 | 30 | 53 | 50 | 0 | 44.9% | 5 | 72,473 | 5.49 | 6.93 |
| Caseless | 18 | 33 | 56 | 53 | 0 | 44.8% | 5 | 74,309 | 5.17 | 6.98 |
| Normalized | 20 | 38 | 60 | 58 | 1 | 49.2% | 5 | 63,211 | 5.11 | 6.86 |
| Dependencies | 20 | 38 | 60 | 58 | 1 | 49.2% | 5 | 63,211 | 7.44 | 6.92 |
| Fallback | 20 | 38 | 60 | 58 | 1 | 49.2% | 5 | 63,211 | 7.71 | 6.85 |

Precision is relevant selected paths divided by all selected paths on
positive tasks. Negative queries have a separate abstention score.
Latency is the median of per-task medians from three in-process
retrievals on a Windows i7-12700H host with about 15.63 GiB physical RAM.
Peak is the largest Windows process working-set high-water mark observed
across the arm, including the small CLI probe. Context bytes sum delivered
payloads across all 56 tasks. Normalized retrieval used an estimated
15,857 source tokens across the tasks. No inference or GPU measurement
was performed. [Task-level evidence and summaries](../../benchmarks/results/2026-11-28-retrieval-confirmation.json)

**Gate result: failed.** Complete-task evidence was 38/45 (84.4%) overall
and 20/25 (80.0%) in Laravel. Even per-item evidence recall, 58/65 (89.2%)
overall and 34/39 (87.2%) in Laravel, fell below 90%. Normalized retrieved
43/47 designated edit loci and 15/18 required supporting items. It
completed 13/17 multi-file tasks. It selected 19 labelled distractors and
61 extra files whose relevance was not annotated. The baseline abstained
on four more negative tasks. Dependency expansion and fallback added no
coverage in the frozen comparison.

Two tasks found the correct long file but missed the essential span
(`theatre/aisle` and `observatory/region`). The third long file delivered
its essential line and was still marked as a partial excerpt. Other
normalized failures include missing route and controller evidence, a
checksum implementation, and an action where the prompt said “payout”
and source used “disbursement.” No arm returned a path outside its
authorized inventory or silently flagged a truncated excerpt as
complete. A separate deterministic boundary control tests a parent
path, a restricted file and a hard link under all seven arms. These
checks cover observed results and those deny cases. No filesystem
syscall trace was collected.

An initial attempt stopped before retrieval because Windows merged
`app/Support` with `app/support`. The corpus paths were reconciled
before the scored freeze. No retrieval evidence was discarded. The
scoring run confirmed that the inventory and all source bytes were
unchanged.

## Reproduce

```text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example retrieval_lab
python -m benchmarks.retrieval_confirmation --output NEW_CONFIRMATION_DIR
python -m benchmarks.retrieval_confirmation_measure --root NEW_CONFIRMATION_DIR --lab RETRIEVAL_LAB --output NEW_REPORT_JSON
cargo test --manifest-path rust/Cargo.toml --all-targets --locked --offline
python -m unittest discover -s tests -p test_retrieval_confirmation.py
```

Confirmation manifest SHA-256
`2e0a898bd588d9058c43747f434728622ede01ab3e5908089e5b4c3aad91c3fe`.
Windows probe SHA-256
`1c682afa0be354d42bc640d383516fb1783c46e610527e8973fb2295400139a4`.

Retain normalized retrieval as the lab candidate. Develop any excerpt
alignment or abstention change on different development tasks and freeze
it before a fresh confirmation. The maintainer owns multi-edit protocol
work. The [inference memory plan](2026-11-28-inference-memory-review-plan.md)
is ready for review before any live model use.
