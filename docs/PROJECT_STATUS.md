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
| Patch lab [#18](https://github.com/MrPunyapal/TinyBuilder/pull/18) | Retain draft for provenance; candidate superseded by #23 after integration review and explicit approval. |
| Coding research [#20](https://github.com/MrPunyapal/TinyBuilder/pull/20) | Retain original research draft; candidate successor #23 replays and extends its work. Verify overlap before supersession. |
| Deep Research [#21](https://github.com/MrPunyapal/TinyBuilder/pull/21) | Phase 1 archive and this canonical status refresh. Previous reviewed head `a0c4fe0b6ee254da6afbe8e0801350f332210f31` passed all four workflows; recheck revised head. |
| Agent onboarding [#22](https://github.com/MrPunyapal/TinyBuilder/pull/22) | Merged into main at `9d4343141bab4d710f7d16450105673c994d5c51`. Guidance CI passed. ChatGPT project settings and fresh local Codex automatic skill discovery remain unverified. |
| Integrated lab [#23](https://github.com/MrPunyapal/TinyBuilder/pull/23) | Local checkpoint `560e2ce7f04fb04fce288566cda5444a00232826`; remote follow-up `4559cec5f62590ebccd440885ec2b998462dbde8` reconciles main ancestry and accounts for blocked probe denominators. Revised CI and guest qualification pending. |
| Model specialization [#24](https://github.com/MrPunyapal/TinyBuilder/pull/24) | Phase 2 archive and maintainer corrections at `74aba166d1ad38d87621b518638180fdfe85ae44`; candidate dossier and isolated evaluation plan, no downloads or training authorized. |

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

Review and qualify the integrated evaluator on an explicitly approved,
disposable offline Linux VM (see Phase 2 roadmap). Complete structured
failure attribution and benchmark bridges, run trusted containment smoke
tests and broaden existing-model development scoring with exact-text plus
selective retrieval. Freeze settings and keep private evaluation independent.
Do not execute arbitrary generated PHP on the ordinary development host or
use the private set to tune. Defer new parser dependencies, model downloads
and training until evidence warrants. Recheck exact-head CI and complete
integration/security review before considering #23 and superseding #18/#20.
Recommended merge order: #21, #24, then #23 after its additional gates;
reconcile main and rerun applicable CI each time. No merge or publication
authorized. Native clean-host qualification stays separate.

See [Agent guide](AGENT_GUIDE.md) for stable mission and authority boundaries,
and [knowledge-maintenance](../.agents/skills/tinybuilder-knowledge-maintenance/SKILL.md)
for how to keep this snapshot useful without accumulating stale duplicates.
