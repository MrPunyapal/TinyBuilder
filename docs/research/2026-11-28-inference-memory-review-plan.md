# Inference memory and multi-file diagnostic plan

Status as of 2026-11-28. Model-free design for review.

Phase 4 identified that the grounded protocol takes exactly one
`path` / `old` / `new` replacement per proposal. The previous two
multi-file retrieval trials supplied both required files in each task,
but the proposal interface could produce only one replacement. Their
outcomes do not isolate the model's multi-file reasoning. The maintainer
owns the multi-edit implementation. No protocol or runtime changes are part
of this experiment design. [Prior trials](2026-11-27-retrieval-intelligence-v2.md)

## Matched experiment arms

| Comparison | Hold fixed | Change |
| --- | --- | --- |
| Allocated context | Model, pinned b12359 runtime, CPU backend, task, evidence and output budget | 2,048 vs 4,096 `--ctx-size` |
| Runtime lifetime | Model, context allocation, task order, request bytes and independent per-request state | One fresh authenticated server per task vs one owned server per model/context block |
| Edit representation | Task, evidence budget, model and reviewed edit scope | Single exact-text edit, bounded batch, sequential exact-text |
| Planning | Same sequential edit budget and reviewed source scope | No plan, compact model plan, human-curated plan without repair answers |
| State | Same task and edit budget | Compact task-local evidence and accepted decisions vs bounded accumulated conversation within that task |

Begin with a read-only resource control using the same reviewed public
development prompts. Keep confirmation fixtures out of prompt tuning.
Use byte-identical requests between identical-lifetime controls and
ensure they fit the 2,048-token allocation, including the fixed output
budget. Run overflow probes separately and record any blocked request or
incomplete finish. `Runtime::start_bounded` accepts both context sizes.
The current proposal runner launches a fresh grounded lab per task. The
resident arm needs a reviewed benchmark driver around one `Runtime` and
multiple `complete_with_usage` requests, with fresh task prompts and no
implicit reuse of response state. A separate prefix-cache experiment
would need its own explicit condition.

For sequential edits, request a new exact-text proposal after any approved
change, using fresh snapshots or the maintainer's reviewed virtual source
view. Review the exact diff at each action boundary. Denial or stale
evidence must stop that edit. A resource-only run can withhold every
approval and compare planning and proposal generation. Semantic patch
measurement requires a qualified evaluator and separate authorization.
The [Phase 3 sandbox draft](https://github.com/MrPunyapal/TinyBuilder/pull/25)
tracks containment independently.

Record the frozen task, model, binary and runtime manifest hashes, request
settings, prompt/completion tokens, cold readiness, warm per-request time,
sampled process-tree peak RAM, available RAM before each trial, timeouts,
ownership cleanup, approval events and all blocked/remaining attempts.
Record GPU memory only when measured. Alternate order within matched blocks
and run one model workload at a time. Preserve the existing 2,800 MiB 1.5B
and 3,500 MiB 3B initial Windows preflight floors for this proposed campaign.
Use no host changes or process termination outside the started runtime.

The current checkpoint contains no new inference or semantic score.
Review the manifest, approval design and memory thresholds before any
live run.
