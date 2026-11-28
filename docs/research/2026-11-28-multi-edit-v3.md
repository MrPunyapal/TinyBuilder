# Coding Intelligence v3: inert multi-edit proposal engine

Status: experimental implementation, not live-model qualification or a product feature.
Base main `ce28337552933a671a95d1ad30baa07cfe7cc2b7`. Retrieval evidence at
[e447155](https://github.com/MrPunyapal/TinyBuilder/commit/e4471558a55e8cc0475c8ab8d9fc68bb8d008c14)
is public development evidence, not independent generalization. Previous single-edit
proposal success cannot establish complete multi-file repair ability; the
existing workbench returns only one ProposedEdit per call.

## First increment

The new Rust module `multi_edit` reuses the existing Project read boundary.
It accepts complete source snapshots and a separate controller-owned explicit
scope, not model-selected permissions. A batch is strict JSON with only an
edits array of path/old/new records. Paths must match the exact canonical
project-relative snapshot names, with no aliases. Existing files only.
Complete supporting files can be retained without granting edit permission.

Each exact, nonempty old fragment must occur once in the current virtual
source (overlapping matches are ambiguous). Replacements are ordered:
a later edit may refer to text produced by an earlier one. This also permits
later reasoning rounds to inspect the virtual state without disk mutation.
There is no fuzzy matching, automatic repair, implicit retrieval, execution,
file creation/deletion/rename, approval bypass or filesystem apply API.
A failed batch cannot change virtual state or consume its edit budget.
An empty net diff is rejected. The workspace borrows the selected Project
and rechecks original complete snapshots before and after staging and review,
including unchanged supporting files. This is not a race-proof filesystem
snapshot; do not use with hostile concurrent writers.

Initial conservative limits (proposed, not optimized): 8 evidence files,
16 cumulative edits, 32 KiB per virtual file, 128 KiB total source state,
8 KiB per old/new fragment, 64 KiB cumulative edit text, 64 KiB JSON per
batch, 64 KiB combined diff. These are byte limits, not model context limits.
Review gives one path-sorted combined diff and original/proposed SHA-256 per
changed file. Render diff using the existing terminal sanitizer; it is
untrusted preview text, not an executable patch or authorization token.

## Verification

```sh
cargo test --manifest-path rust/Cargo.toml --all-targets --locked
```

Deterministic unit tests cover multi-file and sequential same-file edits,
unchanged disk bytes, UTF-8/CRLF preservation, all-or-nothing virtual state,
explicit scope, malformed and duplicate JSON fields, missing/overlapping
anchors, stale targets and supporting evidence, links, no-op batches and
resource limits, including cumulative fragment bytes and combined evidence/virtual state. No generated PHP or real model execution. Existing
cross-platform Rust workflow tests all targets, including the new module.
Local compilation unavailable to remote author (no Cargo, GitHub DNS
unavailable in the execution container); exact-head hosted CI required.

## Next increment (not implemented)

After deterministic tests pass, connect a separate lab-only multi-edit
response schema and sequential controller to this engine. Freeze existing
single-edit baseline; compare batch and sequential decomposed inference
on the same public development tasks. Report complete proposal readiness
and failure attribution separately from semantic correctness. Do not send
expected target paths, answers or hidden tests to the model. Use approved
existing weights only, obey RAM gates. Execution requires independently
qualified containment; coordinate with Portable Evaluator v1. A future
explicit review/export/apply boundary needs its own design and tests;
do not pretend a series of single-file writes is a filesystem transaction.

## Knowledge closeout

This isolated module leaves retrieval v2, portable evaluator work,
the normal native CLI, read oracles, existing prompt/protocol and packaging
unchanged. Existing implementation and benchmark skills already cover
evidence-bound inert experiments and verification; no new skill required
until the procedure is integrated. No new dependencies, downloads, training,
host provisioning or publication. The numerical limits are first-increment
engineering choices, not measured optimal settings.
