---
name: tinybuilder-implementation
description: Implement and review incremental TinyBuilder changes, reuse the Rust core, preserve release and security boundaries, and verify regressions.
---
# Implementation

Start with [onboarding](../tinybuilder-onboard/SKILL.md) and scope the change to
one active workstream. Inspect existing code and tests before introducing
abstractions or dependencies. Prefer a small experiment or extension to a
parallel rewrite; distinguish development tooling from shipped runtime.
Preserve public interfaces, the 0.1 read-only gate, pinned runtime trust checks,
and user data. No implicit downloads, execution, network access or new
privileges. Verify stale evidence and exact action approval before mutation.

For native changes run appropriate locked Rust tests (for example
`cargo test --manifest-path rust/Cargo.toml --all-targets --locked`);
for Python QA run the root AGENTS.md checks. For guidance changes run
`python .agents/check_guidance.py`. Add model-free regression/adversarial
tests for changed behavior and record exact commands. Real model and Laravel
claims need the [benchmark skill](../tinybuilder-benchmark/SKILL.md).
Retain failures and report unavailable test environments. Review the exact
diff, confirm no unintended files or permissions changed and use
[knowledge-maintenance](../tinybuilder-knowledge-maintenance/SKILL.md).
