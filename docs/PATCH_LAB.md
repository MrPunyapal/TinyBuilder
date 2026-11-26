# Rust patch lab (not a 0.1 product feature)

Successor to PR #14, based on main d4ea614. Production CLI and exact read
qualification are unchanged. Never distribute these examples in portable
candidate packages. No new weights or training.

Build on a development host with Rust 1.88 or later:

    cargo build --manifest-path rust/Cargo.toml --release --locked --example diagnose_patch

Run against an existing trusted b12359 runtime and approved GGUF:

    diagnose_patch --runtime RUNTIME --model EXISTING_GGUF --expected-sha256 HASH --output NEW_REPORT_DIR

Three original Python/PHP/Rust cases compare prospective source bytes to
predeclared exact answers. Random untouched comments check preservation.
No source edits or generated code execution. Record genuine deterministic
evidence selection, not model-selected tool use. Failures retained; no
retries. This narrow diagnostic is not semantic coding qualification.

For semantic acceptance, freeze a separate evaluator-owned suite before
model trials. Use disposable isolated worktrees and pre-existing tests
that fail before repair, pass after the independently reviewed patch,
and reject known wrong repairs. Cover Laravel validation with actual
Pest/PHPUnit, boundary cases, syntax checks and unchanged unrelated files.
No arbitrary model-selected commands. Run only reviewed fixed test
commands in isolated disposable environments with no secrets/network.
Report all trials, failures, runtime/model/source hashes, test output
summaries and safety events. Do not change the 10/10 read gate.

For an independently scored Laravel validation repair, use a clean,
disposable Git checkout marked with `.tinybuilder-disposable` and existing
Composer dependencies. Run from the TinyBuilder checkout:

    python -m benchmarks.rust_patch_validation --baseline BASELINE --lab GROUNDED_LAB --runtime RUNTIME --model EXISTING_GGUF --expected-model-sha256 HASH --php PHP --output NEW_REPORT_DIR

The runner creates a detached worktree and checks the untouched suite,
the seeded failure, a correct reference repair and a plausible incorrect
repair before prompting for approval. The lab receives only
`routes/web.php` as complete evidence. Review the exact diff and approve
only the intended safe change in the test project. The runner keeps hidden
assertions out of the project during inference and scores approved changes
with PHP lint, Laravel route listing and the full PHPUnit suite. Add
`--select-line` to compare operator-selected replacement anchors on the
same benchmark. This mode leaves the choice of exact old text to the
evaluator and still requires a reviewed diff and explicit approval. Keep
`laravel-patch.json` with the report, including failed and declined trials.

Lab apply requires explicit permission plus per-patch approval, complete
fresh source evidence and exact unique replacement. Re-read after every
approved edit. Filesystem race and ACL/xattr preservation remain
unqualified. Keep creation and streaming deferred; the old streaming
transport must never bypass current connected-socket authentication.
Duplicate-query suppression is deferred to a separately measured
read-only change, rather than modifying the qualified baseline prompt.
