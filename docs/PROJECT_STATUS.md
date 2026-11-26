# TinyBuilder project status

Dated snapshot: 2026-11-27. Verified remotely at authoring, not live status.
Before acting, recheck [main](https://github.com/MrPunyapal/TinyBuilder/tree/main),
[open PRs](https://github.com/MrPunyapal/TinyBuilder/pulls) and exact-head CI.
Only local Codex can inspect its uncommitted work. Update this page when a
milestone, owner, blocker or evidence changes materially.

## Current milestone: Coding Intelligence v1

Improve the edit representation and repository context before selecting or
training a new model. Use existing 1.5B and 3B GGUFs in matched diagnostics;
expand from narrow fixtures to independent behavioral tests across repositories.
No new downloads or training authorized. The research roadmap is not a
release contract.

| Workstream | Snapshot and next action |
| --- | --- |
| Native 0.1 | Main `9d4343141bab4d710f7d16450105673c994d5c51`; read-only, not qualified for publication. All five retrieved push workflows passed. Fresh candidate artifacts available for all three platforms; continue clean-machine acceptance and release review. |
| Patch lab [#18](https://github.com/MrPunyapal/TinyBuilder/pull/18) | Draft at `3f78a2971e4acbe58bfdb44055fe4e22b2f3dfb4`; all retrieved workflows passed at this head. Reconcile with current main and review evaluator changes before approval. |
| Coding research [#20](https://github.com/MrPunyapal/TinyBuilder/pull/20) | Draft at `c536508bdb1345b380ac2c88e01640120e70d25e`; retrieved Python push workflow passed; full native qualification not established. Local Codex has the Coding Intelligence v1 handoff; reconcile stacked ancestry and preserve evidence. Uncommitted local progress unknown. |
| Deep Research [#21](https://github.com/MrPunyapal/TinyBuilder/pull/21) | Archival review and decision notes complete at `7363b2dbd86d7fb7c6a5bc88820f83c836125f10`; retrieved CI passed. Documentation branch synchronization and status refresh proposed here; no approval to merge or train implied. |
| Agent onboarding [#22](https://github.com/MrPunyapal/TinyBuilder/pull/22) | Merged into main at `9d4343141bab4d710f7d16450105673c994d5c51`. Guidance CI passed. ChatGPT project settings and fresh local Codex automatic skill discovery remain unverified. |

## Evidence to read first

- [Release requirements](RELEASE_0_1.md), [clean-machine acceptance](CLEAN_MACHINE_ACCEPTANCE.md)
  and [release audit](research/2026-11-26-release-audit.md). Windows developer
  host 10/10 read gate is not clean-machine qualification.
- Exact-main CI: [native packages](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45889820700),
  [candidate security evidence](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45889820607),
  [native deterministic checks](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45889820617),
  [Python checks](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45889820603),
  [agent guidance checks](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45889820615).
  All five succeeded. The package workflow lists non-expired Windows x64,
  Apple Silicon macOS and Linux x64 candidate artifacts; the maintainer did
  not download or inspect their inner archives. Use trusted artifact.json,
  inner archive SHA-256 and exact commit for offline acceptance; an outer
  Actions artifact digest is not the inner archive digest. No live model or
  clean-machine run was performed during this remote review.
- [Research vision at #20 snapshot](https://github.com/MrPunyapal/TinyBuilder/blob/c536508bdb1345b380ac2c88e01640120e70d25e/docs/VISION.md).
- [Coding v1 decisions at #21 snapshot](https://github.com/MrPunyapal/TinyBuilder/blob/7363b2dbd86d7fb7c6a5bc88820f83c836125f10/docs/research/2026-11-27-coding-v1-decisions.md),
  [research summary](https://github.com/MrPunyapal/TinyBuilder/blob/7363b2dbd86d7fb7c6a5bc88820f83c836125f10/docs/research/2026-11-27-research-summary.md)
  and [proposed roadmap](https://github.com/MrPunyapal/TinyBuilder/blob/7363b2dbd86d7fb7c6a5bc88820f83c836125f10/docs/research/2026-11-27-implementation-roadmap.md).
  These are pending repository review; consult newer reviewed versions if available.
- [Cross-file validation report](https://github.com/MrPunyapal/TinyBuilder/blob/c536508bdb1345b380ac2c88e01640120e70d25e/docs/research/2026-11-27-cross-file-validation.md):
  repository-reported 1.5B 0/6, research 3B 5/6; one-line repairs using multiple
  source files, not general multi-file editing. Replacement matching and
  irrelevant retrieved context are the leading diagnosed bottlenecks.

## Next handoff

Check the local agent's latest results before assigning new work. Reconcile
existing branches; compare model-selected source-range edits with exact-text
replacements and compare selective lexical retrieval with the current baseline.
Report all attempts and independently verified behavior. Keep clean release
qualification separate. Use the current release candidates for clean-host
acceptance when available; do not transfer earlier development-host passes
onto a new exact candidate. Do not merge or publish without approval.

See [Agent guide](AGENT_GUIDE.md) for stable mission and authority boundaries,
and [knowledge-maintenance](../.agents/skills/tinybuilder-knowledge-maintenance/SKILL.md)
for how to keep this snapshot useful without accumulating stale duplicates.
