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

Lab apply requires explicit permission plus per-patch approval, complete
fresh source evidence and exact unique replacement. Re-read after every
approved edit. Filesystem race and ACL/xattr preservation remain
unqualified. Keep creation and streaming deferred; the old streaming
transport must never bypass current connected-socket authentication.
Duplicate-query suppression is deferred to a separately measured
read-only change, rather than modifying the qualified baseline prompt.
