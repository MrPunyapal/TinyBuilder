---
name: tinybuilder-benchmark
description: Design, run or review independent TinyBuilder coding, retrieval, protocol, patch and resource experiments.
---
# Benchmark

Read current lab docs and reuse existing evaluator. Freeze task/environment
manifest, repository lineage splits, hashes, model/runtime/template, settings
and budgets before evaluation. Use trusted disposable worktrees plus suitable
execution containment, no secrets/network and reviewed fixed verifiers.
Independent baseline must fail target checks, reference repair must pass,
plausible wrong repair must fail and regressions must be checked. Hide
evaluator tests/gold repairs; accept alternatives based on behavior. Avoid
target-path/line hints except clearly labeled diagnostic controls.

Compare one variable at a time: supplied vs retrieved context, edit
representation, model, controller. Track retrieval recall, parse vs semantic
action choice, scope, replacement matching, behavior, regressions, environment
and runtime failures separately. Record all attempts, missing trials, hashes,
tokens, latency, peak RAM/VRAM where measured; unavailable metrics are null.
Fake tests qualify infrastructure only. Do not alter the release oracle.
Keep reports sanitized and record negative results. Use knowledge-maintenance.

Before running generated PHP, verify the offline outer guest and run the
[trusted isolation probes](../../../docs/research/2026-11-27-contained-qualification.md).
Count an exit as a candidate failure only when the container state proves it
and cleanup succeeds. Keep unverified transport, timeouts and cleanup
failures in the blocked denominator. The public scoring entrypoints rerun
trusted qualification before candidate submission; a failed preflight leaves
all candidate trials remaining. Never bypass this via the low-level observe
API, legacy worktree runner, regex expression filter or human patch approval.
Legacy route validation is trusted-controls-only; legacy pilot proposals
are containment-blocked. Preserve historical results without rerunning them.

The owner's personal Windows PC is not an evaluator provisioning target.
Follow the host-protection rule in AGENTS.md. Ordinary CI may run reviewed
trusted controls only; do not treat hosted Linux or a Docker socket as proof
of an approved outer isolation boundary. Keep private fixtures and model
outputs local unless the user separately approves a specific transfer. If a
separate qualified evaluator is unavailable, record a blocker and continue
model-free work; no host fallback.

For the public source-only proposal condition, use
`python -m benchmarks.public_proposal_campaign prepare --output NEW_DIR`,
then inspect after explicitly approved lab proposals. Keep the plan and
scorer outside every model-facing root. Scope readiness is not a pass;
never turn it into a semantic score or use it for private fixtures.
