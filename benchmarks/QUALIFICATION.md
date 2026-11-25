# Qualification campaign (experimental, no default selected)

The historical smoke profile and all historical reports remain unchanged. The
new opt-in `--smoke-profile hidden-facts-v1` measures exact package-name and
description retrieval; Laravel dependency versions were visible in automatic
context. Both new facts are independently randomized, absent from project summary
and prompt, and must be returned exactly on separate lines after a successful
composer.json read. Any attempted write or command disqualifies the new read
profile even if permission denial prevented side effects. Historical scoring is unchanged. Paired seeds are local-only; do not publish them. Ten trials
are required before proposing a default; 10/10 is a proposed read-only gate, not
proof of general coding ability. Do not compare historical and new scores.

## Integration and commands

Run only against an existing approved model. The evaluator uses historical Ollama
unless BOTH `TB_BENCH_MANAGED_URL` and `TB_BENCH_MANAGED_KEY` are supplied.
For standalone qualification always pass `--require-managed` so omitted variables
cannot silently select historical Ollama. Managed mode requires the backend PR's ManagedConnection and ChatModel.from_managed;
no automatic fallback. Use an authenticated loopback server owned by the runtime
manager, not a remote provider. Do not print credentials. Set these variables in
the local process only. The CLI consumes (removes) both variables before running
any subprocess, including controls; credentials are scoped in memory and reset
on exit. Prefer the in-process connection handoff in the CPU campaign below.
Use the runtime-generated model alias, not a credential or a file path.

    python -m unittest discover -s tests -v
    python -m compileall -q tinybuilder benchmarks
    python benchmarks/evaluate.py --require-managed --smoke-profile hidden-facts-v1 --models ALIAS --trials 10 --fixture-seed LOCAL_32_HEX --tool-protocol strict-json --strict-json-profile constrained --progress-guidance checklist --max-steps 8 --output NEW_DIRECTORY

Replace placeholders. Use a cryptographically random local seed. Stop on transport,
identity, safety or fixture failure; inspect complete reports even on exit 1.
Run existing parameter/validation controls-only before edit trials. See LOCAL_NEXT.md.
Do not change oracle criteria mid-campaign.

## Candidate shortlist (metadata research, not functional evidence)

| Tier | Candidate | Primary source / conversion |
| --- | --- | --- |
| CPU 8 GB / Apple 8 GB | Qwen2.5-Coder 1.5B Q4_K_M | [publisher GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF), Apache 2.0 |
| CPU 16 GB / RTX 3050 4 GB / Apple 16 GB | Qwen3 4B Q4_K_M | [publisher GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF), Apache 2.0 |
| blocked on runtime upgrade | Qwen3.5 2B / 4B | [2B](https://huggingface.co/Qwen/Qwen3.5-2B), [4B](https://huggingface.co/Qwen/Qwen3.5-4B); confirm conversion and pinned runtime support |
| same tiers, independent family | Phi-4 mini instruct | [Microsoft model](https://huggingface.co/microsoft/Phi-4-mini-instruct), MIT; verify conversion |
| higher memory | Qwen3 8B | [publisher GGUF](https://huggingface.co/Qwen/Qwen3-8B-GGUF), Apache 2.0 |
| historical comparison only | Qwen2.5-Coder 3B | [publisher model](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct), Qwen Research License; not an unrestricted default |

These tiers are hypotheses, not measured RAM/VRAM requirements. Q4 weights alone
do not determine process memory. Two priority artifacts have publisher LFS
metadata recorded below; other candidates remain unpinned. Do not use this table
as a download catalog. Before inference, verify the chosen original model
and conversion license, immutable revision, LFS digest and byte size against
publisher metadata; hash the actual existing local file and compare. No downloads
or real model tests were performed. Third-party conversions require separate
provenance review.

## Verified publisher artifact pointers (metadata only)

| File | Immutable upload revision | Bytes | SHA-256 |
| --- | --- | ---: | --- |
| qwen2.5-coder-1.5b-instruct-q4_k_m.gguf | [2ab9f8f42af02fc212effaef7c4850c885e965f4](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/commit/2ab9f8f42af02fc212effaef7c4850c885e965f4) | 1117320768 | cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046 |
| Qwen3-4B-Q4_K_M.gguf | [a9a60d009fa7ff9606305047c2bf77ac25dbec49](https://huggingface.co/Qwen/Qwen3-4B-GGUF/commit/a9a60d009fa7ff9606305047c2bf77ac25dbec49) | 2497280256 | 7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5 |

Both publisher GGUF cards advertise Apache 2.0. Review applicable license and
notices at the chosen revision before redistribution. These are remote metadata
identities, not locally hashed files or model compatibility evidence.

## b6500 compatibility and coordination review

The pinned [b6500 architecture registry](https://github.com/ggml-org/llama.cpp/blob/b6500/src/llama-arch.cpp)
contains qwen2 and qwen3 (also phi3), but not qwen35 or qwen35moe.
[Upstream Qwen3.5 support #19468](https://github.com/ggml-org/llama.cpp/pull/19468)
was added later. Qwen3.5 is **excluded** from the b6500 campaign.
Qwen2.5-Coder 1.5B and Qwen3 4B are architecture-level candidates only;
actual GGUF load, template, schema and inference remain unverified.
Phi-4 Mini and Qwen3 8B remain research-only until immutable conversion
metadata and local compatibility are checked. Historical 3B is restricted.

PR #2 head e0f9997b0e2ed78a68c59ffeea4d08d653a946dd exposes the exact
ManagedConnection(base_url, model_alias, api_key) and ChatModel.from_managed
contract. PR #10 head 7c01dfab47dcd440338b8723a38597345a1b6ba1 provides
RuntimeManager.start(model_path, backend="cpu", timeout=180) returning the
same fields. No production code duplication is needed. PR #6's parameter
test edits resolve temp root paths for macOS; our two result assertions touch
different lines. Keep both edits at integration.

## CPU-first local campaign

After HQ integrates the runtime and backend, run one candidate per process.
No downloaded models or runtimes are authorized by this document. The
following command starts only the staged runtime and existing verified model,
with a fresh seed and exactly ten read trials. Use the same private seed
across candidates if comparing matched inputs; do not publish it.

    python benchmarks/qualify_cpu.py --candidate qwen2.5-coder-1.5b --runtime /absolute/staged/runtime --model /absolute/existing.gguf --output /absolute/new-output

Repeat once for qwen3-4b only if its verified file already exists and memory
permits. Pass --fixture-seed with the same private 32-hex seed for pairing.
The runner verifies exact bytes and SHA-256, delegates runtime startup and
cleanup, passes credentials only in memory, and records cold readiness plus
campaign duration in campaign.json. Do not log runtime connection objects or
process command lines. Use external hardware sampling on the owned server
process without capturing its arguments. Warm authenticated readiness and
TTFT/tokens/sec/RAM/VRAM remain manual/unsupported where not exposed; record
null instead of fabricating. Record actual context and sampling defaults
from the pinned runtime; this manager does not expose context overrides.
One candidate at a time, CPU only, no accelerator fallback. Stop on OOM,
failed startup, transport/authentication, security violations, or incomplete
reports. A failed factual trial is not selectively retried.

Laravel negative/reference controls are a separate, optional follow-up
using the existing controls-only CLI and a marked disposable baseline.
Only after the 10-read gate passes, and after both reference controls pass,
perform three trials each for parameter and validation if approved. Use
the same pinned runtime and effective settings; do not rerun historical
health/repair or Boost campaigns. Do not expose the session key via shell
arguments; use the same in-process main(argv, connection=connection)
interface for edit evaluation.

## Measurement protocol

Freeze code SHA, runtime binary hash/version, model hash/bytes/revision, OS,
hardware/driver, backend, model alias, context size, offload, sampling settings,
round limit, oracle version, Laravel baseline SHA/lock hash and fixture seed.
The existing nonstreaming client uses temperature 0.1; do not claim TTFT from
total request time. Record effective settings, not desired settings. Record
cold server launch to ready, warm readiness, TTFT if supported, generation
tokens/sec from server telemetry, peak process-tree RAM and sampled VRAM with
sampling interval and attribution method, plus full task wall time through
independent acceptance (Laravel full_duration_seconds includes worktree setup and
controls, unlike the per-agent duration_seconds). Unsupported metrics are null with explanation.
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
