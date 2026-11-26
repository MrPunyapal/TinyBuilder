# TinyBuilder Laravel Benchmark v1

## Planned scope

Target 30 original or appropriately licensed cases, five in each family.

| Family | Candidate fixture types |
| --- | --- |
| Request validation | Required/optional fields, nested arrays, boundary values, field errors, update rules |
| Eloquent | Filtering, belongs-to, many-to-many, scopes, pagination |
| Authorization | Ownership, policy decisions, guest behavior, roles, tenant isolation |
| Business logic | Discounts, rounding, state transitions, allocations, totals |
| Routing and controllers | Route match, binding, response contracts, redirects, error handling |
| Cross-file reasoning | Controller/request, policy/model, model/relation, service and fixture contracts |

For each case, record fixture origin and license, freeze an evaluator-owned
test suite and declared edit scope, prove the behavioral assertion fails
with the seeded bug, and prove a separately authored reference passes both
behavior and regression assertions. Include safe but wrong comparator
repairs for representative cases. Use new repositories and task families
for the final held-out set. This public pilot is development evidence and
belongs outside the held-out set. Pin sampler, runtime, weights, repository
and evaluator before comparable runs.

## Two-case pilot

This run uses original tests for Laravel's email validator and a checkout
discount helper. Each case lives in its own detached Laravel worktree.
Existing vendored dependencies are copied locally. The evaluator inserts
its PHPUnit tests after the model process has exited, runs fixed test
commands, and restores the exact seeded source between arms. Its only
allowed edit is a single line in the designated fixture. PHP lint checks
syntax. The runner executes only case-specific safe expressions, then
scores independent behavior and regression assertions. Valid alternatives
outside that subset are recorded separately. No project test file is
available for modification during inference.

| Arm | Evidence path |
| --- | --- |
| A | Supplied source, with neither retrieval nor a reference answer |
| B | Known repair path read from the repository |
| C | Deterministic repository retrieval and complete selected-file evidence |
| D | The model selects a real file from the pilot directory listing, followed by validated patch-lab proposal and evaluator-controlled apply |

All four arms share the preselected source line and proposal shape. A and B
supply the same effective source via different paths. D exercises file
choice and the actual evidence-bound proposal validator. It is a bounded
lab workflow and does not measure autonomous patch localization. Model
actions can neither write files nor execute commands. Score outputs as
pass, context retrieval, protocol, syntax, reasoning, regression, timeout,
runtime, evaluator failure, safety or unsupported/out-of-scope. Preserve
all trial denominators and any early stop.

```text
cargo build --manifest-path rust/Cargo.toml --locked --release --example laravel_pilot
python -m benchmarks.laravel_pilot --baseline DISPOSABLE_LARAVEL --lab LAB_EXE --runtime TRUSTED_RUNTIME --php PHP_EXE --model QWEN_1_5B PATH_TO_GGUF SHA256 --model QWEN_3B PATH_TO_GGUF SHA256 --output NEW_DIR
```

Use the pre-existing marker, dependencies and Git protections described in
[PATCH_LAB.md](PATCH_LAB.md). The runner uses no weight downloader. It retains
sanitized events and scores in `pilot.json`.

## Observations — 2026-11-27

Windows i7-12700H CPU b12359, Laravel disposable baseline
`b8f1471d477b127cc62674e9f37110e2dc80d8c4`. Both GGUF headers report file type
15 (Q4_K_M) and configured model context length 32,768. The runtime used
its default slot configuration. Requests used temperature zero with 128
selection and 512 replacement tokens. Each request received one complete
fixture file with exact selected line. No prompt or score was tuned after
seeing model results.

| Model | A | B | C | D | Total | Server peak working set |
| --- | --- | --- | --- | --- | --- | --- |
| Qwen2.5-Coder 1.5B Q4_K_M | 2/2 | 2/2 | 2/2 | 2/2 | 8/8 | 2.50 GiB |
| Qwen2.5-Coder 3B Q4_K_M, research control | 2/2 | 2/2 | 2/2 | 2/2 | 8/8 | 4.29 GiB |

Both selected-read arms emitted verified read evidence before proposing
changes. The failed preliminary parallel-control run stopped before
inference. Its email reference exit was 1 on that attempt. An isolated
replay of the same control passed. The serial campaign used the same
fixtures and prompts and verified both broken controls at `[1,0]` and
both references at `[0,0]`, in behavioral/regression order. Preserve that
initial infrastructure failure alongside the [serial pilot report](../benchmarks/results/2026-11-27-laravel-v1-pilot.json).
Earlier 0/4 live Laravel repair results remain in the
[release audit](research/2026-11-26-release-audit.md#rust-patch-lab-experiments--2026-11-26).
Results support broader independent testing of the existing models.
Fine-tuning research can wait until a frozen held-out suite shows repeatable
reasoning failures after controlling for protocol, evidence and transport.
