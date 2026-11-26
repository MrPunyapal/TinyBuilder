# Specialized TinyBuilder model — baseline-first research

2026-11-26. Separate research branch; never blocks a qualified 0.1.0.
Release candidate 4f04c503cbbdfc3e828192a9edb73566150925b1 passed five
deterministic workflows, but historical real model results are 0/10 for
the unchanged two-fact oracle and 0/3 live edit proposals. No weights,
training or paid compute authorized. No model is qualified.

## Candidate ladder

| Candidate | Upstream license | Why test | Runtime |
| --- | --- | --- | --- |
| [Qwen3-0.6B GGUF](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF) | Apache-2.0 | smallest official Qwen3 baseline | qwen3; test patched runtime |
| [Qwen2.5-Coder-1.5B-Instruct GGUF](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF) | Apache-2.0 | code-specialized existing provisional pin | qwen2; test patched runtime |
| [Qwen3-1.7B GGUF](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF) | Apache-2.0 | size-matched general control | qwen3; test patched runtime |
| [Qwen3-4B GGUF](https://huggingface.co/Qwen/Qwen3-4B-GGUF) | Apache-2.0 | larger accuracy control | qwen3; test patched runtime |
| [Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B), [2B](https://huggingface.co/Qwen/Qwen3.5-2B) | Apache-2.0 | newer small-model candidates | newer qwen3_5 architecture, verify GGUF converter/runtime/chat template before test |

These are candidates, not measured rankings. Current Qwen model cards confirm
license declarations, not complete downstream redistribution clearance.
Prefer official or ggml-org GGUF with immutable revision, exact bytes, SHA-256,
upstream license and provenance recorded. For Qwen3.5 the [ggml-org 0.8B
GGUF](https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF) is a conversion candidate,
not an automatically trusted download. b6500 must not be used for new
inference; upstream GGUF security advisories cover it. b12359 is a candidate,
not a blanket assurance. Do not use Qwen2.5-Coder-3B research-license weights
as default. No model artifact is added here.

## Reproducible evaluation

1. Freeze runtime digest, model digest, quantization, CPU backend, context
   settings, sampler, hardware, OS, chat template and code commit. Use
   same platform/hardware for matched model comparisons.
2. Predeclare diagnostics on fresh randomized fixtures using existing
   rust/examples/diagnose_read.rs (direct plain, direct JSON, baseline,
   split plain, split JSON). Direct evidence arms are controls only;
   keep transport, wrong facts, format, missing read and safety separate.
3. Pick engine before ten fresh trials using existing qualify_read.rs.
   Unchanged oracle requires exact hidden project name + description
   after genuine model-selected read, unchanged fixture, no write attempt.
   Do not select best of repeated campaigns, extract answer strings,
   substitute deterministic reads, or train on generated gate fixtures.
   Evaluate actual shipped workflow separately if different.
4. If diagnosis shows correct direct answers but failed tool selection,
   fix protocol/template before training. If direct evidence answers
   fail, compare larger baseline and quantization before considering SFT.
   Use additional held-out code understanding and safe refusal tasks;
   future coding claims require independent test runners in disposable
   worktrees, not exact source alone.
5. Record file size, total process-tree peak RSS/working set (not just weights),
   startup ms, first token and generation throughput with same runtime settings,
   raw trial counts, real read count, answer correctness, protocol and safety
   failures. Current buffered harness measures latency, not first-token time;
   report unavailable metrics as null, not inferred. No paid compute.

## Dataset pilot and governance

training/build_grounded_pilot.py generates synthetic, original examples only,
with train/dev/eval families disjoint. Each includes task, source evidence and
exact answer. Training file is Alpaca-shaped answer-stage supervision, not a
native tool-call training dataset. No project files, third-party code, private
traces or release-gate fixture content. Held-out pilot rows are reproducible
public controls, not a secret independent evaluation. Build a second private,
freshly authored evaluator set after freezing data and hyperparameters; never
give it to trainer. Partition by repository/task template rather than random
row split; remove near duplicates and provenance conflicts. Human-review every
pilot template, expand via licensed original or permissively licensed code
with attribution, and require independent executable oracles for edit tasks.
Do not train until approval and a failing baseline justify it.

## Efficient adaptation and export

[Soup](https://github.com/MakazhanAlpamys/Soup) offers a convenient orchestration
layer; validate actual installed version and schema with soup doctor --config,
do not run soup train automatically. Current training/soup.yaml is a tiny
format example; never treat it as production recipe. Compare PEFT LoRA and
QLoRA using the same examples, base revision, seed, optimizer and held-out
metric. LoRA on BF16/FP16 base is a baseline if hardware permits; QLoRA freezes
a 4-bit training base and trains adapters, trading memory for compute.
See [PEFT quantization guide](https://huggingface.co/docs/peft/developer_guides/quantization)
and [LoRA reference](https://huggingface.co/docs/peft/en/package_reference/lora).
Soup is optional, not a runtime dependency. On the reported 4GB laptop GPU,
memory feasibility is unverified; start with estimates and a consented dry
run, not an assumed fit. Stop if existing model qualifies.

If authorized and a trained adapter improves held-out tasks, preserve original
base and adapter separately, merge into compatible full-precision checkpoint
where feasible, export using pinned llama.cpp convert_hf_to_gguf.py and
llama-quantize (see [upstream quantization docs](https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/README.md)).
Compare F16/Q8_0/Q4_K_M with matched inputs and exact digest. Quantized inference
weight size differs from training memory; do not assume GGUF Q4 is QLoRA NF4.
Re-test templates, safety, quality and clean platform startup after quantization.
A trained model never changes the release acceptance oracle.
