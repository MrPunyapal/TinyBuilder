# Qualification campaign (experimental, no default selected)

The historical smoke profile and all historical reports remain unchanged. The
new opt-in `--smoke-profile hidden-facts-v1` measures exact package-name and
description retrieval; Laravel dependency versions were visible in automatic
context. Both new facts are independently randomized, absent from project summary
and prompt, and must be returned exactly on separate lines after a successful
composer.json read. Paired seeds are local-only; do not publish them. Ten trials
are required before proposing a default; 10/10 is a proposed read-only gate, not
proof of general coding ability. Do not compare historical and new scores.

## Integration and commands

Run only against an existing approved model. The evaluator uses historical Ollama
unless BOTH `TB_BENCH_MANAGED_URL` and `TB_BENCH_MANAGED_KEY` are supplied.
Managed mode requires the backend PR's ManagedConnection and ChatModel.from_managed;
no automatic fallback. Use an authenticated loopback server owned by the runtime
manager, not a remote provider. Do not print credentials. Set these variables in
the local process only and unset them afterwards. Use a public model alias.

    python -m unittest discover -s tests -v
    python -m compileall -q tinybuilder benchmarks
    python benchmarks/evaluate.py --smoke-profile hidden-facts-v1 --models ALIAS --trials 10 --fixture-seed LOCAL_32_HEX --tool-protocol strict-json --strict-json-profile constrained --progress-guidance checklist --max-steps 8 --output NEW_DIRECTORY

Replace placeholders. Use a cryptographically random local seed. Stop on transport,
identity, safety or fixture failure; inspect complete reports even on exit 1.
Run existing parameter/validation controls-only before edit trials. See LOCAL_NEXT.md.
Do not change oracle criteria mid-campaign.

## Candidate shortlist (metadata research, not functional evidence)

| Tier | Candidate | Primary source / conversion |
| --- | --- | --- |
| CPU 8 GB / Apple 8 GB | Qwen2.5-Coder 1.5B Q4_K_M | [publisher GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF), Apache 2.0 |
| CPU 16 GB / RTX 3050 4 GB / Apple 16 GB | Qwen3 4B Q4_K_M | [publisher GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF), Apache 2.0 |
| same tiers, newer alternatives | Qwen3.5 2B / 4B | [2B](https://huggingface.co/Qwen/Qwen3.5-2B), [4B](https://huggingface.co/Qwen/Qwen3.5-4B); confirm conversion and pinned runtime support |
| same tiers, independent family | Phi-4 mini instruct | [Microsoft model](https://huggingface.co/microsoft/Phi-4-mini-instruct), MIT; verify conversion |
| higher memory | Qwen3 8B | [publisher GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF), Apache 2.0 |
| historical comparison only | Qwen2.5-Coder 3B | [publisher model](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct), Qwen Research License; not an unrestricted default |

These tiers are hypotheses, not measured RAM/VRAM requirements. Q4 weights alone
do not determine process memory. Exact immutable revisions, byte sizes and LFS
SHA-256 were not obtained from the metadata API in this review. Do not use this
table as a download catalog. Before inference, verify the chosen original model
and conversion license, immutable revision, LFS digest and byte size against
publisher metadata; hash the actual existing local file and compare. No downloads
or real model tests were performed. Third-party conversions require separate
provenance review.

## Measurement protocol

Freeze code SHA, runtime binary hash/version, model hash/bytes/revision, OS,
hardware/driver, backend, model alias, context size, offload, sampling settings,
round limit, oracle version, Laravel baseline SHA/lock hash and fixture seed.
The existing nonstreaming client uses temperature 0.1; do not claim TTFT from
total request time. Record effective settings, not desired settings. Record
cold server launch to ready, warm readiness, TTFT if supported, generation
tokens/sec from server telemetry, peak process-tree RAM and sampled VRAM with
sampling interval and attribution method, plus full task wall time through
independent acceptance. Unsupported metrics are null with explanation.
Keep logs, seeds, hidden values, credentials, model answers and patches local.
Publish only sanitized counts, durations, identities and failure categories.

Record requested/completed/failed/aborted trials separately. Distinguish load,
transport, structured actions, executed tools, exact facts, and independent
code acceptance. Never count reference controls or mocks as model successes.
Retain original integer and validation assertions. Five existing task families
remain a small inventory; add distinct cross-file, repair and edge-case fixtures
incrementally toward 20–50, not by counting randomized repetitions as new tasks.

## Oracle correction

Parameter tasks formerly populated baseline_health_exit using the parameter
hidden negative control. The field is now null outside health/repair; the
parameter-specific visible negative and reference fields remain intact. No edit
acceptance assertion was changed. Existing reports are not rewritten.
