# Retrieval v2.1 excerpt alignment

PR [#26](https://github.com/MrPunyapal/TinyBuilder/pull/26) keeps the
seven frozen retrieval strategies and the 56-prompt confirmation.
That confirmation missed two required long-file spans despite selecting
their files. Its queries and spans were kept out of this experiment.

Ten development cases were frozen at
`b512e0604b0f05e758c4b3360118682669a997e2` before either alternative ran.
Eight use long files with distant symbols or competing text. Two use
short files, including one with support from a second file. The scorer
owns the expected source line. The probe receives only a project root,
question and strategy flags.

The baseline ranks with normalized identifiers and scores excerpt lines
using literal matches on the first four query terms. Those rules differ
in case, identifier boundaries and term count. The aligned arm uses the
same bounded, distinct normalized identifiers for both stages, including
a UTF-8 byte anchor for oversized lines.

The initial aligned arm missed a billing case when a comment matched
several terms and the declaration matched one. A separate arm gives
code-line matches four times the weight of matches on lines beginning
with ordinary comment markers. This heuristic can misclassify attributes
or multi-line comments and undervalue documentation when code also
mentions the term. A test verifies that comment-only matches remain
eligible.

| Arm | Required spans | Context bytes | Bytes outside required lines | Median retrieval | Overhead | Peak working set |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen normalized | 5/10 | 98,185 | 97,966 | 2.55 ms | — | 6.66 MiB |
| Identifier-aligned | 9/10 | 98,208 | 97,804 | 2.72 ms | 6.9% | 6.57 MiB |
| Identifier-aligned, code weighted | 10/10 | 98,235 | 97,797 | 2.97 ms | 16.6% | 6.54 MiB |

The [initial run](../../benchmarks/results/2026-11-28-excerpt-alignment-initial.json)
measured 5/10 versus 9/10 with 10.0% median overhead. The table uses the
[matched run](../../benchmarks/results/2026-11-28-excerpt-alignment-matched.json).
Each value aggregates ten case medians from nine in-process retrievals
per case, alternating arm order on Windows. Small working-set differences
do not establish a memory improvement. Bytes outside the required lines
include useful surrounding code, so that count is an upper bound for
irrelevant context.

All arms returned identical ordered paths and complete-file flags for
each case. Short-file results matched exactly. Partial reads stayed
explicitly incomplete and within the existing 12 KiB/file limit. No
out-of-inventory path was returned. Boundary controls cover parent
paths, restricted files and hard links with both aligned arms.

**Decision for review:** keep both options experimental. The
code-weighted arm met the development target, including less than 20%
median latency overhead. A fresh confirmation with documentation queries
and larger source inventories is needed before promotion. PR #27 owns
multi-edit semantics and PR #28 owns containment.

```text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example retrieval_lab
python -m benchmarks.excerpt_alignment_measure --lab RETRIEVAL_LAB --output NEW_REPORT_JSON
cargo test --manifest-path rust/Cargo.toml --all-targets --locked --offline
```

Matched Windows probe SHA-256
`935efbc378cab4787bda29453ba6aae473bec2b4b5f331a0a547a387f940869c`.
