# Coding intelligence: research direction and next experiment (2026-11-27)

Supersedes workflow specialization as the primary objective, not the historical
evidence. See [VISION](../VISION.md). TinyBuilder should solve unfamiliar coding
tasks, not mimic a fixed SOP. The release contract and unchanged read oracle
remain separate.

## Research references (ideas only; no code imported)

- [little-coder](https://github.com/itayinbarr/little-coder): investigate small-model
  harness interventions, bounded tool results and model-specific evaluation.
  Its published reproduction uses a 9.7B Q4 model, not our 1.5B baseline.
- [Aider repository map](https://aider.chat/docs/repomap.html): compare concise
  symbol/dependency ranking within a fixed token budget against lexical search.
- [SWE-smith](https://github.com/SWE-bench/SWE-smith): executable tasks and
  training data; adapt the concept to original/license-reviewed PHP repositories.
- [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent): measure the
  simplest useful agent loop; do not adopt unrestricted shell execution.
- [SWE-Master](https://github.com/RUCAIBox/SWE-Master): study test-feedback
  post-training and trajectory curation; its 32B results do not establish 1.5B
  feasibility.
- [Laravel Boost](https://laravel.com/docs/13.x/boost): package-aware docs,
  guidelines, skills and MCP; prefer optional integration to reimplementation.
- [OpenCode](https://github.com/anomalyco/opencode): examine TUI and extension
  boundaries; no need to replace Rust.
- [llama.cpp](https://github.com/ggml-org/llama.cpp): runtime, constrained
  decoding and quantization. Maintain pinned and independently reviewed builds.
- [workflow-slm](https://github.com/arpitbbhayani/workflow-slm): verified
  trajectories and specialization are hypotheses; see earlier source audit.

These are an initial source survey, not reproduced benchmark claims or license
clearance. Deep research should inspect actual code, experiment artifacts,
licenses, hardware requirements and matched comparisons.

## Cross-file diagnostic

See the [Windows validation and measured results](2026-11-27-cross-file-validation.md).

Three original two-file cases: contact validation, seat eligibility and role
authorization. They use project policy definitions and independent PHP tests.
No model-selected commands or edits to user files. The model selects an exact
replacement and its target; no selected line is supplied in the prompt.
The evaluator's allowable single-line subset is intentionally narrow.

    cargo build --manifest-path rust/Cargo.toml --release --locked --example laravel_pilot

    python -m benchmarks.laravel_pilot --suite coding-cross-file --baseline BASELINE --lab LAB --runtime RUNTIME --php PHP --model LABEL GGUF SHA256 --output NEW_DIR

A supplies complete relevant source as a reasoning control; C uses real
lexical retrieval without a target-path hint. Both use the same proposal schema
and token cap. The evaluator checks both files are present and complete before
inference; a missing file is a retrieval failure. Wrong target, malformed
proposal, scope, syntax, reasoning, regression and runtime failures must remain
visible. Do not compare directly with older selected-line arms or claim that
this tests arbitrary multi-file editing. Existing pilot worktrees are retained
for inspection. Run only in an offline trusted disposable environment.

Next: anonymized private repository/family-held-out tasks with less explicit
symbol hints, multi-file changes, failing-test feedback, feature work and
version-dependent documentation. Build a matched comparison of baseline
lexical retrieval vs bounded structural retrieval; report actual context
tokens and process-tree memory, not estimated results. Model training is
deferred until a credible baseline and approval.
