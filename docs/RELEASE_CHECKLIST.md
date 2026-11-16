# Public experimental-preview release checklist

**PUBLIC EXPERIMENTAL PREVIEW READY** — local validation completed on
2026-11-16. See the [Windows validation report](../benchmarks/results/2026-11-16-windows-preview-validation.md).
This recommendation covers the documented experimental CLI, with unreliable
validation edits and unproven model-selected MCP use disclosed. Official package,
tag, and release publication still requires separate authorization.

## Package and documentation

- [x] Runtime candidate recorded: `0bd6ede8787c0951a7b52383676f273ad84554d7`; documentation publication is identified in the handoff.
- [x] 120 Python tests and compilation pass on Windows.
- [x] GitHub CI passes Python 3.10, 3.12, 3.13, including extracted-source tests.
- [x] Wheel and source distribution built; both inspected for forbidden files.
- [x] Wheel installed in an isolated fresh environment; CLI help/doctor pass.
- [x] Fresh Windows clone/setup passes with the documented installed-Python fallback.
- [x] Read-only task produces genuine successful tool events and correct facts.
- [x] Default permission and exact argv behavior tested.
- [x] Known risks, unsupported scenarios and model licenses disclosed.
- [ ] Maintainer explicitly authorizes any release tag, PyPI upload, or
      official GitHub release.

The unchecked publication item is intentionally deferred; no official artifacts
were published by this validation task.

## Real model and Laravel validation

- [x] Clean marked disposable Laravel app and PHP reference/negative controls.
- [x] Model-generated health/repair edits pass independent full Laravel assertions,
      allowed scope, pre-edit reads and post-final-edit tests (3/3 each).
      Request-validation edits remain 0/3 in every tested condition.
- [x] Native Boost MCP transport/direct calls verified; model-driven use
      either proven or explicitly labeled experimental/unproven.
- [x] Actual trial counts and resource limitations reported without
      extrapolating three trials into general reliability.

## Known evidence — not new experiments

The [November 16 report](../benchmarks/results/2026-11-16-windows-preview-validation.md)
records two complete matched validation comparisons: eight and twelve rounds,
three trials per prompt arm. All Composer inspections passed, but all validation
edits failed PHP parsing and independent acceptance. Current health and repair
scenarios each passed 3/3 real model-generated changes. Direct read-only Boost
MCP worked; model-selected native calls remained 0/3. These limits prevent claims
of reliable autonomous coding, while installation, safety, and minimum real-model
checks support a clearly labeled experimental preview.

The [November 15 local Codex report](../benchmarks/results/2026-11-15-local-codex-validation.md)
records genuine 3B Ollama `read_file` events and passing evaluator-owned
Laravel controls. However, 3B still passed **0/3 validation edits** in both
completed twelve-round conditions, and made no model-selected MCP call across
three native MCP trials. The eight-round paired comparison was incomplete.

An earlier [November 13 report](../benchmarks/results/2026-11-13-local-release-validation.md)
records health/repair task successes on the then-current setup. Those are
different scenarios and cannot substitute for final candidate validation.

**Decision:** share only the documented experimental preview. No package-index
publication or official tag/release without explicit maintainer sign-off. The
three-trial task results do not establish broad autonomous coding reliability.

For local retesting, follow [RETEST.md](../benchmarks/RETEST.md) using a fresh
marked disposable Laravel baseline, fresh output directories, and real
Ollama/PHP test evidence.

## Additional scenario verification

The route-parameter benchmark is a newly added fourth opt-in Laravel edit
scenario. Its deterministic Python and fake-artisan regression checks are not
proof of real PHP semantics. Before treating it as a meaningful model task,
run the manual real-Laravel reference workflow and/or local
`--scenario parameter --controls-only` first, then independent Ollama trials.
Do not retroactively change the recorded 2026-11-16 model pass counts.
