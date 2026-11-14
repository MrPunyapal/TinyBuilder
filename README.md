# TinyBuilder

**Experimental local-first coding agent** built around small language models, real developer tools, Laravel Boost MCP and opt-in project preferences. Free and MIT licensed. Soup can be used later for fine-tuning; training is not needed to try the first version.

> Status: v0.1 research prototype, not a trained model or a proven replacement for frontier coding agents. A 0.5B model may fail at tool calling and multi-step edits even when tools provide good information. Evaluate before relying on it.

## Architecture

```
User CLI task
  → local OpenAI-compatible model (Ollama or llama.cpp)
  → tool loop (read/search/write files, run project commands)
  → optional MCP stdio bridge → Laravel Boost
  → tool observations discarded after the process ends

SQLite → explicit, user-owned project preferences/decisions only
Soup → optional offline fine-tuning stage, outside the runtime
```

All runtime Python dependencies are from the standard library. **No subscription or API key is required** when using a locally hosted model.

## Get started

Requires Python 3.10+ and a running local OpenAI-compatible model server. On a machine with Ollama:

```bash
# Download a small baseline (you can try a larger model to compare quality)
ollama pull qwen2.5-coder:0.5b

# Install the CLI from this repository
python -m pip install -e .

# Non-mutating diagnostics
tinybuilder doctor --project /path/to/laravel-app

# Read-only coding task (command execution and file changes are blocked)
tinybuilder chat "Inspect my routes and suggest a simple health endpoint" \
  --project /path/to/laravel-app \
  --model qwen2.5-coder:0.5b
```

By default TinyBuilder calls `http://127.0.0.1:11434/v1/chat/completions`, the Ollama OpenAI-compatible endpoint. For llama.cpp, pass `--base-url http://127.0.0.1:8080/v1` and your model name. Ollama must be running; Python alone does not run the model.

For an isolated Windows PowerShell install (Python 3.10+):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m tinybuilder doctor --project .
ollama pull qwen2.5-coder:1.5b
```

If `python` opens the Microsoft Store, use the absolute path to an installed Python
interpreter to create the environment. Activating the environment is optional when
using its executable directly. For POSIX shells use `.venv/bin/python` instead.

Use `chat --verbose` to observe JSON events on stderr: model rounds, tool names,
success/error status and duration. Arguments, file contents, model answers, tool
outputs and call IDs are excluded from these events. JSON printed in a model's
answer is **not** a tool call; look for `tool_end` events and verify resulting files.

On Windows, Herd may expose `php.bat` rather than `php.exe`. Python's shell-free
subprocess launcher cannot resolve the bare `php` batch wrapper. Put the actual
PHP executable directory first in the **current process** PATH before running
TinyBuilder, or configure MCP with the absolute `php.exe` path:

```powershell
$phpExe = php -r 'echo PHP_BINARY;'
$env:PATH = (Split-Path $phpExe) + ';' + $env:PATH
```

### Enable Laravel Boost (optional)

Inside an existing Laravel project:

```bash
composer require laravel/boost --dev
php artisan boost:install
```

Then point TinyBuilder at the included MCP configuration. The MCP subprocess runs **with the Laravel project as its working directory**:

```bash
tinybuilder chat "Use Boost to inspect my Laravel version and suggest a test" \
  --project /path/to/laravel-app \
  --mcp-config /path/to/tinybuilder/examples/mcp.json
```

Boost typically exposes `php artisan boost:mcp`, which is registered in `examples/mcp.json`. MCP tool schemas are discovered dynamically, so the commands it supports can vary with Laravel Boost versions and project setup. In native mode the agent also lists up to 24 sanitized, **exact discovered MCP tool names** in its transient task context. It does not invent a fixed Boost API, execute text pretending to be a tool call, or make MCP available in strict-JSON mode. This guidance does not prove a small model will select the tool. MCP servers are trusted local processes; configure only servers you trust.

### Allow changes or tests explicitly

Without flags, local file changes and commands are refused. Pass only the permissions needed:

```bash
tinybuilder chat "Add a migration, then review it" --project /path/to/laravel-app --allow-write

tinybuilder chat "Run the failing Pest test and explain the result" \
  --project /path/to/laravel-app --allow-exec
```

For disposable evaluations, restrict execution to exact argv arrays (repeat the
flag to permit additional commands):

```bash
tinybuilder chat 'Run the tests' --project /path/to/disposable-app --allow-exec \
  --exec-command '["php","artisan","test"]' --verbose
```

This restriction compares every argument before execution; it is not an OS sandbox.

**Security warning:** `--allow-exec` permits arbitrary local commands, not a sandbox. `--allow-write` allows editing and replacing project files. Read-only mode does **not** constrain side effects of independently configured MCP servers. Use a disposable Git worktree/container for untrusted tasks, and review changes with `git diff`. Tool output and source files can contain prompt-injection attempts; the agent labels them untrusted but this is not a security boundary.

### Explicit project memory

Only CLI commands write to persistent memory. The model cannot persist web pages, documents, MCP tool output or other internet-retrieved content.

```bash
tinybuilder memory set test_runner Pest --project /path/to/laravel-app
tinybuilder memory list --project /path/to/laravel-app
tinybuilder memory delete test_runner --project /path/to/laravel-app
```

Memory is stored at `~/.tinybuilder/memory.sqlite` by default, scoped by absolute project path. It is a normal SQLite file; safeguard it if you store private preferences or decisions. No conversation history or online documentation is persisted by the runtime.

### Experimental strict JSON tool protocol (opt-in)

The stock Qwen2.5-Coder 0.5B, 1.5B and 3B Ollama tags produced **zero native tool calls** in the [recorded Windows evaluation](benchmarks/results/2026-11-11-windows.md). They sometimes printed JSON-looking examples in text; these were not actions. This does **not** establish that changing the protocol will make those models reliable.

Native tool calling remains the **default**. As an experimental comparison, `--tool-protocol strict-json` asks the model to emit a **single JSON object** (not fenced Markdown), with an exact action shape:

```json
{"type":"tool","name":"read_file","arguments":{"path":"composer.json"}}
```

Or a final response:

```json
{"type":"final","content":"Facts verified from the tool observation."}
```

The parser accepts **only** the five known local tools (`list_files`, `read_file`, `search_files`, `write_file`, `run_command`). It validates all fields and local argument types before dispatch, rejects ambiguous/malformed/mixed/oversized responses and duplicate keys, and retries a bad response only once. It never interprets fenced JSON or prose as an action. This mode intentionally excludes MCP servers; use native mode for Boost. Permission flags and exact argv allowlists still apply.

PowerShell read-only smoke test, with Ollama running and the model already downloaded:

```powershell
.\.venv\Scripts\python.exe -m tinybuilder chat 'Read composer.json using tools, then report its package name.' --project $app --model qwen2.5-coder:1.5b --tool-protocol strict-json --verbose
```

For an explicitly disposable project only, add `--allow-write` to permit edits. For a test command, also use `--allow-exec --exec-command '["php","artisan","test"]'`. Do not give an unrestricted execution flag to untrusted projects. Validate edits with `git diff` and actual Laravel tests; a model's final text is not evidence of work.

Sanitized `--verbose` events distinguish rejected protocols/arguments, permission denials and failed execution without exposing source contents or generated action arguments. HTTP response errors do not include returned server error bodies.

The prompt-only strict JSON mode was evaluated locally and still often produced
forbidden Markdown fences. A separate opt-in profile uses a compact prompt and
requests server-side JSON-schema generation via `response_format`, supported by
[local Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs):

```powershell
.\.venv\Scripts\python.exe -m tinybuilder chat 'Read composer.json and report its exact package name and Laravel constraint.' --project $app --model qwen2.5-coder:3b --tool-protocol strict-json --strict-json-profile constrained --verbose
```

This profile requires a server supporting JSON-schema responses. There is no
silent fallback or extraction from prose. The same independent parser, permission
checks, command allowlist and retry limit still apply even if the server ignores
the schema. The default native and prompt-only strict JSON modes are unchanged.
Constrained syntax does not establish factual correctness or task completion;
see the [local protocol comparison](benchmarks/results/2026-11-11-protocol-comparison.md).

## Optional Soup experiments

`training/soup.yaml` is a **starter recipe**, based on Soup's documented SFT format, not a validated, benchmarked model. Its two-row `sample-traces.jsonl` exists to show the expected format and is far too small for useful fine-tuning. Use an isolated environment to install and validate Soup:

```bash
python -m pip install "soup-cli[train]"
soup doctor --config training/soup.yaml
# Train only after creating a real, permissioned, quality-controlled dataset.
soup train --config training/soup.yaml
```

You can train tool-use trajectories with Soup, but copying generated answers from a flagship model does not by itself make a tiny model capable of executing real-world Laravel tasks. Respect dataset licenses and model-provider usage terms.

## Test

```bash
python -m unittest discover -s tests -v
```

This test suite uses a fake model and fake MCP server. It verifies the tool loop and MCP wire protocol **without** downloading model weights, installing PHP, or calling external services. Run the separate, opt-in local-model/Laravel evaluation with `benchmarks/evaluate.py`; see [benchmarks/README.md](benchmarks/README.md) for setup and measured results.

## What is deliberately not built yet?

- No custom-trained small model or claims of reliable autonomous coding.
- No polished OpenCode plugin or hosted OpenAI-compatible proxy. OpenCode already supports local providers; direct editor integration remains a separate milestone.
- No browser/web-search tool yet. Laravel Boost provides current Laravel documentation when the server is installed and online; generic web retrieval is a separate adapter.
- No Docker sandbox, human-in-the-loop per-command approval UI or multi-user authentication.
- No validated Soup training run on an RTX 3050 or end-to-end agent-success benchmark.

## Roadmap

1. Benchmark 20–50 real reproducible Laravel tasks against unmodified 0.5B, 1B and 3B baselines. Track actual task completion, test pass rates and tool failures.
2. Add command-specific approvals, a sandbox, safe Git worktrees and robust context truncation.
3. Add optional ephemeral web search/docs adapters without saving retrieved content.
4. Collect permissioned, filtered *successful tool-use trajectories* and run controlled Soup LoRA experiments.
5. Add OpenCode integration and a local OpenAI-compatible agent endpoint, once the CLI's task-solving performance justifies it.

Contributions welcome. See [benchmarks/README.md](benchmarks/README.md) for the experimental standard.

### Opt-in progress guidance and repeated evaluation

The [retest guide](benchmarks/RETEST.md) explains the experimental completion checklist (`--progress-guidance checklist`), repeated hidden-name runs (`--trials`), route-preservation variants, and failing-test repair evaluation. All are opt-in; the previously measured constrained 3B profile remains unchanged without these flags. Results on local Ollama/Laravel hardware require separate verification.
