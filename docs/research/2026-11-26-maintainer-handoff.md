# Post-PR #15 maintainer handoff

Baseline main d4ea614d0da5bbe71e5a6cc28538ee2d878fbcc2. [Python](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45817823281), [native](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45817823146), [Rust](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45817823465) all passed. The prior workflow configuration did not package or audit main pushes; this change enables both and manual reruns. Exact new-head results are required. Historical developer-host 10/10 applies to the recorded build, not every binary. Public release remains on hold.

## PR dispositions
- #14: conflicting, historical 15 successful checks, no formal reviews, CodeRabbit skipped. Preserve feat/rust-agent-engine at 9467f503764b0b337ffc358c8dc46048c26a96dd. Source excerpts and read-only CLI already landed. Selectively port patch-lab diagnostics and evidence-bound edits from current main, not old transport or product mutation flags. Defer creation and streaming, require connected-socket ownership for any future authenticated stream. Close superseded PR only once successor is recorded.
- #16: additive, historical 11 successful checks, no formal reviews, CodeRabbit skipped. Preserve research/specialized-model at daf6cc8fa5104377ebb103208c56bf67f1b3b. Extract updated research notes; retain generator, tests and pilot workflow together on that branch. No training justified by the current narrow baseline.

## Order
1. Finish exact-artifact release checks and clean Windows x64/macOS ARM64/Linux x64 acceptance; independent security and redistribution review.
2. Integrate this documentation and evidence workflow change after fresh review/CI.
3. Run lab-only patch diagnostics on existing verified weights, then independently scored semantic repair tasks in disposable worktrees. Keep normal CLI read-only and the existing gate unchanged.
4. Consider future creation, streaming and specialization only with separate evidence and explicit scope approval.

No model downloads, training or publication. Do not treat CI smoke as real-model or clean-host qualification.
