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

## Release/0.1 scope

Read docs/RELEASE_0_1.md and docs/research/2026-11-26-release-audit.md before release work. Keep the normal native product CLI read-only. Python and mutation examples are reference/lab only. Preserve the exact model qualification oracle and all failed evidence; do not tag or publish without authorization.


## Agent onboarding and reusable skills

Start substantive project work with [Agent guide](docs/AGENT_GUIDE.md) and
[Project status](docs/PROJECT_STATUS.md). Verify the live repository/PR state
before planning or changing anything; historical chat and benchmark reports
are not current branch status. For simple questions, read only relevant context.

Use the relevant repository skill under `.agents/skills/`:
- [tinybuilder-onboard](.agents/skills/tinybuilder-onboard/SKILL.md): Fresh sessions and workstream reconciliation.
- [tinybuilder-maintainer](.agents/skills/tinybuilder-maintainer/SKILL.md): PR, architecture and roadmap decisions.
- [tinybuilder-implementation](.agents/skills/tinybuilder-implementation/SKILL.md): Incremental implementation, testing and safety.
- [tinybuilder-benchmark](.agents/skills/tinybuilder-benchmark/SKILL.md): Executable coding experiments and failure attribution.
- [tinybuilder-model-research](.agents/skills/tinybuilder-model-research/SKILL.md): Model, dataset and training research.
- [tinybuilder-release](.agents/skills/tinybuilder-release/SKILL.md): Native read-only release qualification.
- [tinybuilder-knowledge-maintenance](.agents/skills/tinybuilder-knowledge-maintenance/SKILL.md): Required closeout of substantive work.

**Knowledge maintenance is part of the definition of done.** After meaningful
research or engineering work, record evidence and current decisions, then
review affected skills and guidelines. Update an existing skill when a
reusable procedure changes; create a narrowly scoped skill when a genuinely
new recurring workflow is established. If no reusable change is warranted,
state why in the handoff. Preserve negative evidence and explicit approval
boundaries; never silently turn a hypothesis into policy. Do not persist
private user data or session transcripts. The closeout requirement does not
authorize writes: when the task is read-only, propose changes in the handoff
instead. Update the status snapshot only for material changes, not every chat.
Run `python .agents/check_guidance.py` when guidance changes.

[ChatGPT project instructions](docs/CHATGPT_PROJECT_INSTRUCTIONS.md) are a
portable copy for project settings, not an override of this file.
