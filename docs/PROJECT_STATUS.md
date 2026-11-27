# TinyBuilder project status

Dated snapshot: 2026-11-27. Verified remotely at authoring, not live status.
Before acting, recheck [main](https://github.com/MrPunyapal/TinyBuilder/tree/main),
[open PRs](https://github.com/MrPunyapal/TinyBuilder/pulls) and exact-head CI.
Only local Codex can inspect its uncommitted work. Update this page when a
milestone, owner, blocker or evidence changes materially.

## Current milestone: Coding Intelligence v1

Improve retrieval coverage on public tasks before collecting more proposals.
The first [local public campaign](research/2026-11-27-public-proposal-measurements.md)
produced one review-ready proposal per model. Eleven of twelve tasks per
model stopped at retrieval. Semantic qualification still requires a
separately approved isolated Linux evaluator. Use the existing 1.5B and
research-only 3B weights. Candidate downloads, training, and personal
Windows provisioning remain deferred.

| Workstream | Snapshot and next action |
| --- | --- |
| Native 0.1 | Main `ce28337552933a671a95d1ad30baa07cfe7cc2b7`; the product remains read-only and clean-host acceptance is open. |
| Patch lab [#18](https://github.com/MrPunyapal/TinyBuilder/pull/18) | Merged through ancestry at `3f78a2971e4acbe58bfdb44055fe4e22b2f3dfb4`. |
| Coding research [#20](https://github.com/MrPunyapal/TinyBuilder/pull/20) | Closed as superseded. Its evidence remains available through the original PR and the integrated lab. |
| Deep Research [#21](https://github.com/MrPunyapal/TinyBuilder/pull/21) | Merged at `4be34b7f737e29c1436fcb269dfd10295457740d`. |
| Agent onboarding [#22](https://github.com/MrPunyapal/TinyBuilder/pull/22) | Merged into main at `9d4343141bab4d710f7d16450105673c994d5c51`. Guidance CI passed. ChatGPT project settings and fresh local Codex automatic skill discovery remain unverified. |
| Integrated lab [#23](https://github.com/MrPunyapal/TinyBuilder/pull/23) | Merged at `ce28337552933a671a95d1ad30baa07cfe7cc2b7`. All seven workflows passed at the reviewed head `e1e68ae894e322641bb431de81c236081d8920cb`. Guest qualification remains open. |
| Model specialization [#24](https://github.com/MrPunyapal/TinyBuilder/pull/24) | Merged at `ff05f4ef232ebe161f69cbc8cf5dbe49b703fafd`; candidate dossiers only, no model downloads or training. Historical VM recommendation superseded on the personal Windows host. |

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
- [Coding Intelligence v1 matched experiment](https://github.com/MrPunyapal/TinyBuilder/blob/8dec0b35f73560820fd709014ddef5064386b56c/docs/research/2026-11-27-coding-v1-experiment.md):
  30 repository-reported trials, 3B exact-text 3/3, both models' model-selected
  line repairs 0/3 with supplied evidence, one operator-selected repair per
  model. Both retrieval strategies used the failing line protocol; selective
  lexical retrieval retained required files in all 12 retrieval trials and
  reduced observed median prompt tokens about 87%, not an established repair
  gain. Keep exact text as lab baseline; test retrieval under it separately.
  Incomplete responses lack usage/finish details; do not infer stop reason.
  [Corpus control evidence](https://github.com/MrPunyapal/TinyBuilder/blob/8dec0b35f73560820fd709014ddef5064386b56c/benchmarks/results/2026-11-27-coding-v1-corpus.json):
  12 tasks across three original applications with separate Git histories
  sharing a Laravel skeleton; seeded/wrong repairs fail and references pass.
  This is oracle validation, not model qualification or a private holdout.
  Broader contained model evaluation remains open; see subsequent private controls below.
  [Integrated branch Python CI](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45890427075).

- [Exact-text retrieval ablation](https://github.com/MrPunyapal/TinyBuilder/blob/560e2ce7f04fb04fce288566cda5444a00232826/docs/research/2026-11-27-exact-retrieval-ablation.md):
  12 trials, required-file recall 12/12; 3B 3/3 per arm, 1.5B 0/3 per arm;
  median prompts 1,818 to 258. Narrow development fixtures only.
- [Source-ID comparison](https://github.com/MrPunyapal/TinyBuilder/blob/560e2ce7f04fb04fce288566cda5444a00232826/docs/research/2026-11-27-source-id-comparison.md):
  18 trials; source ID 0/3 each, all six PHP lint rejections; exact text 3/3
  for 3B, 0/3 for 1.5B. The initial blocked run is retained. Do not promote
  source IDs or repeat the same smoke ablation by default.
- [Adversarial corpus controls](https://github.com/MrPunyapal/TinyBuilder/blob/560e2ce7f04fb04fce288566cda5444a00232826/docs/research/2026-11-27-corpus-adversarial-controls.md):
  12 public and two private trusted-control tasks passed; no private live
  model score. [Contained evaluator](https://github.com/MrPunyapal/TinyBuilder/blob/4559cec5f62590ebccd440885ec2b998462dbde8/docs/research/2026-11-27-contained-php-evaluator.md):
  model-free infrastructure only, live guest unqualified, blocked probes
  now reported conservatively; candidate/infrastructure exit attribution open.
- [Phase 2 roadmap and maintainer decision](https://github.com/MrPunyapal/TinyBuilder/blob/74aba166d1ad38d87621b518638180fdfe85ae44/docs/research/2026-11-27-model-specialization-roadmap.md):
  conditional MiniCPM5-2B, Qwen3.5-2B and Granite 4.2-3B dossiers; Qwen3.5-4B
  only if justified. No measured ranking or local QLoRA feasibility.
- [Exact-main rehearsal](https://github.com/MrPunyapal/TinyBuilder/blob/560e2ce7f04fb04fce288566cda5444a00232826/docs/research/2026-11-27-exact-main-release-rehearsal.md):
  local agent reports three verified inner archives and Windows 10/10 genuine
  reads on an elevated development PC. Clean-host gates remain open.

## Next handoff

Recheck exact-head CI. The integrated lab retains the original proposal paths,
historical evidence and controls. Legacy generated-code execution is disabled.
All twelve public corpus tasks have bridge source (87 reference observations):
eight dependency-free and four real Laravel-dependent. Exact-lock and capability
preflight is required for the latter. Trusted control CI must pass; live guest
and private bridges remain separate gates. A separate real-HTTP route
validation bridge adds nine probes without changing the original PHPUnit
oracle; its trusted CI must pass. The public source-only campaign prepares
isolated model-facing source roots. The separate measurement runner makes
review-only model calls and records scope-only proposal readiness.
Measure retrieval coverage on public prompts before repeating inference.
Do not provision or modify the owner's personal Windows host; live guest
qualification remains blocked. Ordinary CI is not an isolation approval.
Do not execute arbitrary generated PHP on the ordinary host or transfer
private data without approval. Freeze development evaluation before private
confirmation; retain exact text plus selective lexical retrieval. Do not
repeat the completed smoke campaigns, download weights or train without
evidence and approval. Keep native clean-host qualification separate.

See [Agent guide](AGENT_GUIDE.md) for stable mission and authority boundaries,
and [knowledge-maintenance](../.agents/skills/tinybuilder-knowledge-maintenance/SKILL.md)
for how to keep this snapshot useful without accumulating stale duplicates.
