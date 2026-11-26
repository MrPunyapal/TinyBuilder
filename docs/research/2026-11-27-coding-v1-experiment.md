# Coding Intelligence v1 experiment

## Comparison settings

Run the three existing smoke cases with both locally available Qwen2.5-Coder
Q4_K_M weights on the pinned b12359 CPU runtime. Use one attempt per
model/case/arm, temperature zero and the same independent PHP evaluator. The
experiment code is pinned at `f866473386e854980def37d4f441298e790fc590`.
The seat case reverses the main edit and retrieval arm order for both models.

| Arm | Evidence | Edit representation |
| --- | --- | --- |
| A | Both relevant files supplied in full | Existing exact-text replacement |
| B | Same evidence as A | Model-selected path and one-based source line |
| C | Operator-selected target file and line | Existing operator-anchored replacement |
| L | Existing lexical retrieval | Same representation as B |
| S | Selective lexical retrieval, minimum rank 10 | Same representation as B |

A/B isolates the edit representation. L/S isolates the retrieval threshold.
C is a diagnostic reference with extra location information and a different
context. The evaluator checks required-file recall before inference. The
model receives only the task, the retrieved or supplied files, and the
proposal schema. The stricter retrieval mode remains in the lab.

The model-selected line protocol resolves a line against complete evidence.
The patch rechecks the source digest and preserves LF or CRLF. The proposal
requires separate approval to apply. Automated scoring runs only the existing
safe PHP subset on disposable fixtures.

## Measured results

All 30 predeclared Windows trials completed. PHP lint and independent Laravel
behavior and regression assertions passed for every repair counted below.
Both GGUF identities remained unchanged. The full report records startup,
latency, token counts and failure categories per model, case and arm.
[Sanitized results and hashes](../../benchmarks/results/2026-11-27-coding-v1.json)

| Model | A exact text | B model line | C operator line | L lexical | S selective |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1.5B | 0/3 | 0/3 | 1/3 | 0/3 | 0/3 |
| 3B research | 3/3 | 0/3 | 1/3 | 0/3 | 0/3 |

| Model | Startup | Peak server / sampled driver plus server | Median L / S latency | Median L / S prompt tokens |
| --- | ---: | ---: | ---: | ---: |
| 1.5B | 1.59 s | 2.69 / 2.68 GiB | 20.17 / 3.05 s | 1,796 / 236 (3 each) |
| 3B research | 3.51 s | 4.65 / 4.64 GiB | 37.53 / 6.46 s | 1,797.5 / 237.5 (2 each) |

Both lexical arms retrieved all required files in all 12 retrieval trials.
Selective ranking reduced observed median prompt use by about 87%. Both
arms used the same line protocol, which failed in every retrieval trial, so
the measured benefit is lower context and latency. These three cases do
not establish a repair-rate gain or recall on unfamiliar repositories.
The RTX 3050 reported zero VRAM use and zero utilization across 79
whole-device samples during lab execution.

The 1.5B failed at exact replacement matching twice and scope once in A.
All nine unassisted line trials were rejected by the protocol. The 3B line
trials reported three invalid locations, three protocol rejections, and three
incomplete runtime responses. The raw report labels those as `output_limit`.
The runtime discarded the server usage and finish-reason detail on those
responses, so the exact stopping reason and affected token counts are
unavailable. The C-arm evidence inventory lists the prepared context; the
actual request contained only its operator-selected file.

The independent contact replay reproduced both outcomes. The 1.5B
envelope parsed, then the replacement failed the single-line payload
rules. The 3B runtime returned another incomplete response. This separates
an edit payload rejection from observed PHP behavior. No replacement text
was retained. [Sanitized replay](../../benchmarks/results/2026-11-27-coding-v1-line-probe.json)

## Corpus controls

`benchmarks.coding_v1_corpus` creates three separate Git histories from the
same pinned Laravel skeleton. Clinic, Catalog, and Dispatch code is original.
Each contains four cases with independent PHPUnit behavior and regression
checks. The Eloquent cases use in-memory SQLite. Both two-file references
must fail when either change is individually reverted. The evaluator's test
sources stay outside the application repository except during trusted tests.
The runner restores each repository after the controls.

All 12 seeded baselines failed behavior and passed regression. All 12
trusted references passed both. All 12 plausible wrong repairs were
rejected by the assertions. Reverting either file independently in each
two-file reference made its behavior test fail. The three Git baselines
and local environment files were verified unchanged after the recheck.
[Corpus controls and baseline hashes](../../benchmarks/results/2026-11-27-coding-v1-corpus.json)

The Dispatch split is a holdout candidate with public evaluator sources. A
private holdout needs separate fixtures. The feedback case carries a public
failure summary for a future second-turn experiment. Executing arbitrary
model-generated PHP or evaluating generated multi-file patches requires a
separate contained runner.

## Next experiment

Keep exact-text edits as the comparison baseline for the 3B. Compare the
two lexical strategies with that protocol to measure repair-rate effects
without the line-payload bottleneck. Separately compare visible source
identifiers and a typed single-line payload on smoke fixtures. Record
approved incomplete-response metadata without retaining model text. Use
an isolated runner and private held-out repositories before promoting
structural extraction, adopting dependencies, or evaluating arbitrary
multi-file proposals. The measured failures do not justify model
downloads or training yet.

## Reproduction

```text
cargo build --manifest-path rust/Cargo.toml --release --locked --offline --example laravel_pilot
python -m benchmarks.laravel_pilot --suite coding-v1 --baseline BASELINE --lab LAB --runtime RUNTIME --php PHP --model LABEL_15 MODEL_15 SHA_15 --model LABEL_3 MODEL_3 SHA_3 --output NEW_CAMPAIGN_DIR
python -m benchmarks.coding_v1_corpus --baseline BASELINE --php PHP --output NEW_CORPUS_DIR
```

Use a marked disposable Laravel baseline with existing Composer dependencies.
Use the same runtime and GGUF digests recorded by the
[previous cross-file pilot](2026-11-27-cross-file-validation.md).
