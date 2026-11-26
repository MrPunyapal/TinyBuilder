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
| Native 0.1 | Main `9d4343141bab4d710f7d16450105673c994d5c51` passed five workflows. Publication remains blocked by clean-machine acceptance and release review. |
| Patch lab [#18](https://github.com/MrPunyapal/TinyBuilder/pull/18) | Draft at `3f78a2971e4acbe58bfdb44055fe4e22b2f3dfb4`. Exact-head CI recorded 19 successful checks and one skip. |
| Coding research [#20](https://github.com/MrPunyapal/TinyBuilder/pull/20) | Draft preserved at `c536508bdb1345b380ac2c88e01640120e70d25e`. The Coding Intelligence v1 branch replays its experiment tree on the tested #18 base and adds the paired measurements and corpus controls. |
| Deep Research [#21](https://github.com/MrPunyapal/TinyBuilder/pull/21) | Draft at `7363b2dbd86d7fb7c6a5bc88820f83c836125f10`; archival review and decision notes, not approval to train. |
| Agent onboarding [#22](https://github.com/MrPunyapal/TinyBuilder/pull/22) | Merged into main. Apply ChatGPT project instructions separately. |

## Evidence to read first

- [Release requirements](RELEASE_0_1.md), [clean-machine acceptance](CLEAN_MACHINE_ACCEPTANCE.md)
  and [release audit](research/2026-11-26-release-audit.md). Windows developer
  host 10/10 read gate is not clean-machine qualification.
- [Research vision at #20 snapshot](https://github.com/MrPunyapal/TinyBuilder/blob/c536508bdb1345b380ac2c88e01640120e70d25e/docs/VISION.md).
- [Coding v1 decisions at #21 snapshot](https://github.com/MrPunyapal/TinyBuilder/blob/7363b2dbd86d7fb7c6a5bc88820f83c836125f10/docs/research/2026-11-27-coding-v1-decisions.md),
  [research summary](https://github.com/MrPunyapal/TinyBuilder/blob/7363b2dbd86d7fb7c6a5bc88820f83c836125f10/docs/research/2026-11-27-research-summary.md)
  and [proposed roadmap](https://github.com/MrPunyapal/TinyBuilder/blob/7363b2dbd86d7fb7c6a5bc88820f83c836125f10/docs/research/2026-11-27-implementation-roadmap.md).
  These are pending repository review; consult newer reviewed versions if available.
- [Cross-file validation report](https://github.com/MrPunyapal/TinyBuilder/blob/c536508bdb1345b380ac2c88e01640120e70d25e/docs/research/2026-11-27-cross-file-validation.md):
  repository-reported 1.5B 0/6, research 3B 5/6; one-line repairs using multiple
  source files, not general multi-file editing. Replacement matching and
  irrelevant retrieved context are the leading diagnosed bottlenecks.
- [Coding Intelligence v1 measured report](https://github.com/MrPunyapal/TinyBuilder/blob/8dec0b35f73560820fd709014ddef5064386b56c/docs/research/2026-11-27-coding-v1-experiment.md):
  the 3B passed 3/3 exact-text trials. Both models scored 0/3 each with
  model-selected lines and supplied evidence. Selective lexical ranking
  retained full required-file recall on the smoke cases and cut median
  prompt size about 87%. The 12-task corpus passed its independent controls
  and awaits contained evaluation of model-generated code.

## Next handoff

Compare baseline and selective lexical retrieval using the exact-text edit
protocol. Test explicit source identifiers separately before moving to a
private held-out split. Continue clean release qualification independently.
Repository approvals still govern merging, publication, and model changes.

See [Agent guide](AGENT_GUIDE.md) for stable mission and authority boundaries,
and [knowledge-maintenance](../.agents/skills/tinybuilder-knowledge-maintenance/SKILL.md)
for how to keep this snapshot useful without accumulating stale duplicates.
