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
failures in the blocked denominator.
