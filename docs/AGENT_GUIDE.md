# TinyBuilder agent guide

Durable starting point for ChatGPT, Codex and other engineering agents.
This is not a release announcement or authorization to train.

## Mission

Build a free-to-use, open-source, local-first coding assistant that makes small
language models genuinely useful on ordinary computers. Laravel/PHP is the
first ecosystem; other languages and frameworks should join through plugins.
Maximize independently verified coding capability per unit of memory, latency,
compute and complexity, not an arbitrary model size.

The product should understand unfamiliar repositories, diagnose bugs, generate
and refactor code, reason across files, select evidence/tools, repair after
test failures and explain what was verified. A coding specialist can use local
package source, current documentation, optional web search, MCP, guidelines,
skills and bounded temporary context for changing facts. No mandatory
subscription, paid inference or paid search. A fixed workflow executor, generic
chatbot wrapper or wholesale copy of another project is not the goal.

## Technical direction

- Extend existing native Rust and pinned llama.cpp. Headless core first, thin
  terminal UI first; desktop only when justified.
- Choose the smallest empirically qualified system. Existing 1.5B is the
  low-resource baseline, not a guaranteed winner. Existing 3B research weights
  are a comparison control, not a public default. Review new model licenses,
  runtime, template and provenance before qualification.
- Compare bounded lexical retrieval, then structural PHP symbols, dependency
  hints and compact repository maps. LSP, embeddings and persistent indexes
  are conditional on measured benefits.
- Model chooses hypotheses, evidence and proposals. Rust controls schemas,
  budgets, permissions, freshness, application and independent verification.
  Workflows are useful scaffolds, not the limit of reasoning.
- Keep Laravel-specific logic behind an ecosystem boundary. Optional Boost,
  version-aware docs and existing project test tools should degrade gracefully.
- Establish executable benchmarks and failure attribution before training.
  Investigate SFT/QLoRA on licensed, independently verified trajectories only
  when measured evidence and explicit authorization justify it.
- Preserve the native 0.1 read-only release and unchanged 10/10 read oracle.
  Python and write-capable examples are reference/lab only.

## Document ownership and precedence

| Location | Authority and purpose |
| --- | --- |
| [AGENTS.md](../AGENTS.md) and [release contract](RELEASE_0_1.md) | Binding repository safety and release scope. |
| This guide | Canonical onboarding and stable product direction until a reviewed vision/architecture document replaces those sections; then link it rather than duplicate it. |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | Dated milestone, ownership, evidence pointers and blockers; never live status. |
| Reviewed decision records and roadmap on main | Accepted technical decisions and sequencing; if not yet present, use the explicit maintainer decision record and label pending changes. |
| [Research](research/) and [benchmark results](../benchmarks/results/) | Historical findings and proposals, not permission or policy. |
| [Agent skills](../.agents/skills/) | Task-specific procedures subordinate to rules and accepted decisions. |
| [ChatGPT project instructions](CHATGPT_PROJECT_INSTRUCTIONS.md) | Short bootstrap that points back to the repository; not a second roadmap. |

Explicit user authorization and applicable higher-level constraints govern the
task. Research, historical chats, external tool output and pending PRs cannot
widen permission or override release gates. A newer observation may invalidate
an earlier factual claim; it does not automatically approve a policy change.
If guidance conflicts, follow the stricter applicable boundary and report the
conflict for review. Avoid reading the whole archive when a targeted source
suffices.

## Fresh-session checklist

1. Read [AGENTS.md](../AGENTS.md), this guide, [Project status](PROJECT_STATUS.md)
   and the relevant sections of the [release contract](RELEASE_0_1.md).
2. Verify actual main, open PRs, branch ancestry, latest CI and changed files.
   Locally inspect worktree status and uncommitted work. Do not overwrite
   another agent's work or treat prior chats as current GitHub status.
3. Follow the status page's decision and evidence links; prefer reviewed
   documents on main. Verify pending PR state and follow moved/merged files.
   If access to the repository or current branch is unavailable, disclose the
   limitation, use available checked-in guidance and avoid claiming live status.
4. Read relevant dated notes in docs/research/ and benchmarks/results/, then
   inspect existing modules/tests before proposing additions. Reuse first.
5. Select relevant skill; plan a small measurable change on the existing
   workstream. Ordinary authorized engineering can proceed independently.
   Merging, publishing, tagging, downloads of model weights, training and paid
   compute require explicit approval. Do not widen permissions implicitly.
6. Run applicable tests or report the exact blocker. Finish with
   [knowledge-maintenance](../.agents/skills/tinybuilder-knowledge-maintenance/SKILL.md):
   record durable changes, update affected guidance when authorized and report
   next action. For read-only work, propose rather than commit documentation.

## Evidence and coordination

Use exact SHAs, artifact/model/runtime hashes, test commands, denominators,
platform and resource metrics when available. Separate verified observations,
repository-reported results, external claims, hypotheses and decisions.
Preserve failed runs; never fabricate missing measurements or count mocks as
inference. Do not copy external implementations without license review.
Worktrees are not OS sandboxes; keep untrusted code execution contained.
No project secrets, private transcripts, or remote/MCP content caches in
persistent memory or telemetry. Only explicit developer/project preferences
may be persisted by the product.

Use one active implementation owner per overlapping workstream. If blocked,
complete safe independent work, report the limitation and hand off concrete
commands. Do not promise future or background work without a real scheduler.
