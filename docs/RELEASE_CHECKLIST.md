# Public experimental-preview release checklist

**Status: HOLD — public preview not signed off.** The repository can be
prepared for distribution without claiming reliable autonomous coding.

## Package and documentation

- [ ] Exact release-candidate SHA recorded; working tree clean.
- [ ] Python tests and compilation pass on the candidate.
- [ ] GitHub CI passes Python 3.10, 3.12, 3.13.
- [ ] Wheel and source distribution built; both inspected for forbidden files.
- [ ] Wheel installed in an isolated fresh environment; CLI help/doctor pass.
- [ ] Fresh Windows PowerShell setup passes without maintainer assistance.
- [ ] Read-only task produces genuine successful tool events and correct facts.
- [ ] Default permission and exact argv behavior tested.
- [ ] Known risks, unsupported scenarios and model licenses disclosed.
- [ ] Maintainer explicitly authorizes any release tag, PyPI upload, or
      official GitHub release.

## Real model and Laravel validation

- [ ] Clean marked disposable Laravel app and PHP reference/negative controls.
- [ ] Model-generated edits pass independent full Laravel assertions, allowed
      file scope, pre-edit reads and post-final-edit tests.
- [ ] Native Boost MCP transport/direct calls verified; model-driven use
      either proven or explicitly labeled experimental/unproven.
- [ ] Actual trial counts and resource limitations reported without
      extrapolating three trials into general reliability.

## Known evidence — not new experiments

The [November 15 local Codex report](../benchmarks/results/2026-11-15-local-codex-validation.md)
records genuine 3B Ollama `read_file` events and passing evaluator-owned
Laravel controls. However, 3B still passed **0/3 validation edits** in both
completed twelve-round conditions, and made no model-selected MCP call across
three native MCP trials. The eight-round paired comparison was incomplete.

An earlier [November 13 report](../benchmarks/results/2026-11-13-local-release-validation.md)
records health/repair task successes on the then-current setup. Those are
different scenarios and cannot substitute for final candidate validation.

**Decision:** no stable-release claim, package-index publication or official
tag without explicit maintainer sign-off. A clearly labeled public preview
may be considered only after installation/security gates and limitations
are independently reviewed.

For local retesting, follow [RETEST.md](../benchmarks/RETEST.md) using a fresh
marked disposable Laravel baseline, fresh output directories, and real
Ollama/PHP test evidence.
