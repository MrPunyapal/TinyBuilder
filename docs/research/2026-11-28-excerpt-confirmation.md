# Independent excerpt-alignment confirmation

The [development experiment](2026-11-28-excerpt-alignment.md) reached
10/10 spans with code weighting. This separate confirmation used the
unchanged retrieval code from `54045c7b63189928bb2698eb8398691e55198115`.
The [protocol](2026-11-28-excerpt-confirmation-protocol.md), fixtures and
scorer were committed at `8f614d75e6588cd0fdaa53d66d08ff0d0a9d3067`
before running any of its three arms. The existing 56-task confirmation
and ten development cases were preserved.

## Matched Windows results

| Frozen arm | Complete tasks | Required spans | Documentation spans | Context bytes | Truncated excerpts | Median / p95 | Peak working set |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original normalized | 18/24 | 22/28 | 12/12 | 527,642 | 43 | 3.21 / 3.86 ms | 6.74 MiB |
| Identifier-aligned | 21/24 | 25/28 | 11/12 | 527,686 | 43 | 3.66 / 4.13 ms | 6.77 MiB |
| Code-weighted | 19/24 | 23/28 | 8/12 | 527,772 | 43 | 3.61 / 4.05 ms | 6.77 MiB |

| Family | Original normalized | Identifier-aligned | Code-weighted |
| --- | ---: | ---: | ---: |
| Long implementation | 5/8 | 7/8 | 7/8 |
| Documentation-dependent | 8/8 | 7/8 | 5/8 |
| Mixed evidence | 1/4 | 3/4 | 3/4 |
| Short-file controls | 4/4 | 4/4 | 4/4 |

**Neither candidate passed.** The 90% span gate required 26/28.
Identifier alignment reached 25/28 (89.3%) and lost one documentation
span the baseline delivered. Code weighting reached 23/28 (82.1%)
and lost four such spans. Both candidates improved complete tasks
and passed the latency budget. Median overhead was 14.0% and 12.7%,
respectively. The small timing and working-set differences between
candidate arms establish no general performance ordering.

The six authored repositories contained 22 files. Each case had three
process starts per arm with three timed calls each. The table uses the
median and nearest-rank p95 across per-case medians. It excludes process
launch and reports the maximum process working-set high-water mark on
Windows. No retrieval arm returned an out-of-inventory path or violated a
file, line-byte or completeness check. Ordered paths and completeness
flags matched across all arms, all four short controls passed, and
fixture inventories were unchanged. The probe reports returned paths
and ranges. No filesystem syscall trace was collected.

## Failure evidence and disposition

- In `calibration-expiration`, both candidates chose an early Rust
  helper that mentioned calibration expiration. The baseline delivered
  the later two-line comment giving the operative rule.
- Both candidates also lost the late implementation for
  `reservation-barcode` to an earlier display helper.
- Code weighting displaced the required comment in
  `recovery-sequence`, `protected-coordinate`, and the mixed
  `carrier-handover` case. The last case requires two regions in one file
  that cannot fit in the same bounded excerpt. Code weighting flipped
  which span was delivered. All arms missed the complete task.

Keep identifier alignment as an opt-in research candidate for its
implementation and mixed-task gains. Reject code weighting as a general
default. Keep the baseline as the comparison reference. These outcomes
do not establish production behavior. No strategy was modified or tuned
during confirmation. No inference or fixture code was executed.
[Task-level report](../../benchmarks/results/2026-11-28-excerpt-confirmation.json)

## Reproduce

```text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example retrieval_lab
python -m benchmarks.excerpt_confirmation_measure --lab RETRIEVAL_LAB --output NEW_REPORT_JSON
python -m unittest discover -s tests -p test_excerpt_confirmation.py
```

Confirmation manifest SHA-256
`2b1af6fd4c665cc7041428df8963ad4ef2039c1a5ce6eac2fd939c8f8c2677b9`.
Windows probe SHA-256
`0e33949c27930c6f8d8abd29a0ff43e592be60edc544144c290981e1f3cf1e71`.
