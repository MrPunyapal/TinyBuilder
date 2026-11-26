# Workflow SLM lab — 2026-11-27

Decision: use deterministic orchestration first, then evaluate whether learning
stable coding actions into a small model improves resource use and repair
quality. This is a research continuation of draft PR #18 (8f1c45e), not a
release dependency. See [product vision](../VISION.md).

## Source review

[workflow-slm](https://github.com/arpitbbhayani/workflow-slm) suggests
workflow-specific instruction tuning, validated teacher traces, constrained
actions and distribution-shift tests. Its [report script](https://github.com/arpitbbhayani/workflow-slm/blob/master/src/exp/eval/report.py)
and [smoke pipeline](https://github.com/arpitbbhayani/workflow-slm/blob/master/src/exp/smoke.py)
contain predefined accuracy figures; smoke uses dummy adapters and fake clients.
The published report's teacher-forced branch scores do not substantiate the
claimed 95% threshold. The checked source tree had no LICENSE file or tracked
raw training/evaluation artifacts. Do not copy source, assume redistribution
rights or treat 93% as reproduced. This lab uses original TinyBuilder fixtures.

## Verified repository evidence, not independently rerun here

Main was 841a85fc4f12d10d38776b2bc9ff85232a6eab62. Draft PR #18 head
8f1c45e2233d93ea0958449cb53728a4085ea071 contains
[the local two-task pilot](../../benchmarks/results/2026-11-27-laravel-v1-pilot.json)
with 8/8 reported for each existing GGUF. All four arms use an evaluator-selected
line and tiny complete source files; these are not eight independent coding
problems. Earlier full route repair failures remain relevant.

## New pilot

Five original single-line cases with family-disjoint train (2), dev (1) and
public evaluation (2) splits. They cover Laravel validation and collections,
arithmetic, ownership logic and string normalization. The allowed replacement
subset is deliberately narrow; these are not realistic multi-file repair tasks.
The public evaluation set is a control, not a secret test set.

Run on a trusted, offline disposable Laravel Git checkout with existing
Composer dependencies, no secrets and reviewed PHP execution. Python 3.12+
for local lab QA; it remains outside the native product.

    python -m benchmarks.workflow_slm --baseline BASELINE --php PHP --output NEW_REFERENCE_DIR

This runs actual Laravel repair/regression controls using the existing
worktree evaluator, verifies the reference and rejects a plausible wrong
repair, removes each worktree and only then exports train.jsonl. The
controls.json report has zero model trials. Reference traces are deterministic
and explicitly not model-generated; their abstract action schema is a
research contract, not yet a runtime or SFT tokenizer format. Hidden tests,
dev/evaluation solutions, external data and user project content are excluded
from training output. Do not train on this tiny public pilot.

For model trials build the existing lab-only binary:

    cargo build --manifest-path rust/Cargo.toml --release --locked --example laravel_pilot

Use the existing approved models, runtime, and fixed hashes:

    python -m benchmarks.laravel_pilot --suite workflow-dev --baseline BASELINE --lab LAB --runtime RUNTIME --php PHP --model LABEL GGUF SHA256 --output NEW_DEV_DIR
    python -m benchmarks.laravel_pilot --suite workflow-eval --baseline BASELINE --lab LAB --runtime RUNTIME --php PHP --model LABEL GGUF SHA256 --output NEW_EVAL_DIR

Repeat --model LABEL GGUF SHA256 in the same invocation to compare both models.
Use dev for iteration; freeze prompts/settings before eval. Original suite is
still the default. Reports retain all requested arms and missing trials, reject
duplicate/unexpected rows and model-asserted passes, and include wrong-repair
controls for the new suites. The existing pilot retains its disposable worktrees
for inspection: remove with git worktree remove --force after review.

## Next experiment (not implemented yet)

Pre-register paired tasks and a private family/repository-held-out set,
including multi-file Eloquent, request validation, authorization and behavioral
regression tasks. Compare the same checkpoint in three modes:
1. Ordinary prompt-driven agent with identical tool access and budgets.
2. Explicit Rust workflow stages and bounded evidence, same checkpoint.
3. Same workflow with an adapter trained on licensed, independently verified
   trajectories, only after separate approval and hardware feasibility.

Measure behavioral pass@1, wrong-repair rejection, protocol/safety events,
actual model/adapter digests, context tokens, wall time and peak app/runtime
RAM/VRAM. Keep ordinary prompt vs workflow as a separate comparison from
the existing A-D evidence-selection diagnostic arms. Do not infer general
coding intelligence from this pilot. Refuse missing controls or missing
weights; never produce synthetic performance numbers. No weight downloads,
training, paid services, release or qualification-oracle changes.
