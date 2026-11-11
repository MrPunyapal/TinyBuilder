# TinyBuilder developer guidance

Goal: a free, fully open-source, local-first coding agent that uses a small model to reason over real project files, local tools and live documentation. Do not claim or assume a 200–500 MB model matches flagship coding models: benchmark functional tasks to establish capability.

Important constraints:
- Model weights, live documentation, user/project memory and runtime are distinct components. A 400 MB model file does not mean a 400 MB resident process.
- Do not write external documentation, web/MCP tool outputs or conversation transcripts to SQLite. SQLite saves only explicit developer/project preferences via `tinybuilder memory` commands.
- MCP results and web results are transient context. If adding web search, do not cache remotely retrieved content on disk.
- File writes and command execution must remain opt-in and should move toward per-action human approval and containment; do not silently widen permissions.
- Do not silently call paid APIs or download multi-GB weights in tests. Keep baseline CI deterministic and cheap.
- Keep Soup isolated from inference/agent runtime. Validate changes to `training/soup.yaml` against the installed Soup schema.
- Laravel Boost's MCP command is `php artisan boost:mcp` inside an existing Laravel app. Handle missing Boost gracefully.
- Focus the next engineering milestone on a repeatable benchmark harness using disposable Git worktrees and real Pest/PHPUnit pass/fail signals. Only train when baseline failures and evaluation data justify it.

- Tool protocol fallback is explicitly opt-in (`--tool-protocol strict-json`), limited to known local tools, with strict JSON and argument validation. Never parse arbitrary markdown/prose/fenced JSON as actions. Preserve native calls and all permission/argv controls.

Quick local checks:

```
python -m unittest discover -s tests -v
python -m compileall -q tinybuilder
python -m tinybuilder doctor --project .
```
