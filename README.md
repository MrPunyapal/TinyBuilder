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

Boost typically exposes `php artisan boost:mcp`, which is registered in `examples/mcp.json`. MCP tool schemas are discovered dynamically, so the commands it supports can vary with Laravel Boost versions and project setup. MCP servers are trusted local processes; configure only servers you trust.

### Allow changes or tests explicitly

Without flags, local file changes and commands are refused. Pass only the permissions needed:

```bash
tinybuilder chat "Add a migration, then review it" --project /path/to/laravel-app --allow-write

tinybuilder chat "Run the failing Pest test and explain the result" \
  --project /path/to/laravel-app --allow-exec
```

**Security warning:** `--allow-exec` permits arbitrary local commands, not a sandbox. `--allow-write` allows editing and replacing project files. Read-only mode does **not** constrain side effects of independently configured MCP servers. Use a disposable Git worktree/container for untrusted tasks, and review changes with `git diff`. Tool output and source files can contain prompt-injection attempts; the agent labels them untrusted but this is not a security boundary.

### Explicit project memory

Only CLI commands write to persistent memory. The model cannot persist web pages, documents, MCP tool output or other internet-retrieved content.

```bash
tinybuilder memory set test_runner Pest --project /path/to/laravel-app
tinybuilder memory list --project /path/to/laravel-app
tinybuilder memory delete test_runner --project /path/to/laravel-app
```

Memory is stored at `~/.tinybuilder/memory.sqlite` by default, scoped by absolute project path. It is a normal SQLite file; safeguard it if you store private preferences or decisions. No conversation history or online documentation is persisted by the runtime.

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

This test suite uses a fake model and fake MCP server. It verifies the basic tool loop and MCP wire protocol **without** downloading model weights, installing PHP, or calling external services. Real Laravel task-solving benchmarks are not yet implemented; see `benchmarks/README.md`.

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
