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

For the legacy Laravel route validation fixture, only reviewed trusted
controls may execute outside the separately qualified candidate evaluator.
Use a clean disposable checkout of trusted Laravel source and dependencies:

    python -m benchmarks.rust_patch_validation --baseline BASELINE --php PHP --output NEW_REPORT_DIR --trusted-controls-only

The runner retains the untouched, seeded, reference and incorrect-repair
controls. It does not invoke the model or evaluate a generated patch.
The old invocation that applied a model patch and then ran local PHPUnit
is historical, not an authorized execution path. See the
[contained qualification checkpoint](research/2026-11-27-contained-qualification.md).
Do not revive it merely because a human approves a diff. The contained
public scorer does not yet cover full Laravel route validation.

Lab apply requires explicit permission plus per-patch approval, complete
fresh source evidence and exact unique replacement. Patches are bound to
the originating canonical project root. Re-read after every
approved edit. Filesystem race and ACL/xattr preservation remain
unqualified. Keep creation and streaming deferred; the old streaming
transport must never bypass current connected-socket authentication.
Duplicate-query suppression is deferred to a separately measured
read-only change, rather than modifying the qualified baseline prompt.
