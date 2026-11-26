# Proposed verified Laravel-first training-data pipeline

Date: 2026-11-27. Design only; no dataset generated, no model downloads or training. See [full research](2026-11-27-model-specialization-deep-research.md) and [roadmap](2026-11-27-model-specialization-roadmap.md). Adapt [SWE-smith](https://arxiv.org/abs/2504.21798) and [SWE-agent](https://github.com/SWE-agent) principles, not copied implementations. Existing [benchmark skill](../../.agents/skills/tinybuilder-benchmark/SKILL.md) defines containment and executable controls.

## Pipeline and admission gates

1. **Rights before ingestion.** Prefer original apps with documented ownership and permissive licensing; check third-party dependencies/assets, contributor rights, exact revision/license, notices, data protection, teacher terms and training/redistribution rights separately. Public availability is not a license. Quarantine unclear or restricted material; no private repos, secrets, credentials, real customer data, unlicensed issue text or research-only model outputs without explicit clearance. Laravel documentation and package source are versioned references, not a scrape target. Preserve attribution and deletion lineage.
2. **Split before generation.** Assign repository roots, forks, template derivatives and task-family/operator clusters to train, development, or private evaluation before mutation. Reserve unfamiliar repo lineages and entire task subfamilies; no private prompts, hidden tests, patches, traces, or snippets in training/retrieval. Keep private fixtures outside Git under owner ACL. Dedup across splits by exact content hash, normalized PHP tokens/AST, near-duplicate similarity and manual lineage review. Freeze split manifests and audit overlap; quarantine uncertain matches. The public smoke cases are development regression controls only.
3. **Construct pinned environments.** Record repo SHA, PHP/Laravel versions from lockfiles, Composer dependency hashes, approved immutable image digest, OS, locale, seed, fixtures, database and verifier revision. Install dependencies only in approved setup; evaluation is offline, secret-free, disposable, with non-root isolation and bounded CPU/RAM/time/disk/output. Worktrees alone are not sandboxes. Use fixed reviewed argv; no model-authored test commands. Current contained evaluator requires live guest/image and safety validation.
4. **Task generation.** Start with original apps; cover request validation, routing/binding, authorization/policies, Eloquent scopes/relations, transactions/concurrency, mass assignment, migration/database correctness, feature additions and refactors, cross-file reasoning and genuine multi-file modifications. Construct baseline and reference independently of generator where possible. Mutation operators should produce behavior defects, not just syntax breakage; remove trivial target hints and avoid repetitive template variants.
5. **Executable oracle.** Known-good baseline passes. Seeded faulty baseline fails the intended hidden target check while preserving unrelated checks; reference fix passes all; at least one plausible wrong alternative fails. Record lint, Pest/PHPUnit behavior and regression outputs and exit codes independently; test variants for authorization bypass, tenant isolation, boundaries and unintended changes. Reject flaky/environment failures, weak oracles, test edits, leaked gold patches, stale revisions, unauthorized writes and no-op successes. Rerun deterministically, consider multiple seeds when needed. Trust behavior, not text equality to gold.
6. **Generate trajectories only when authorized.** Record permitted tool actions, bounded evidence, schema-valid proposal, verifier feedback and repaired attempt. Prefer minimal evidence selection; mask non-assistant labels for SFT when supported; don't teach model to emit tool responses, hidden assertions, private reasoning or unauthorized commands. Failed attempts followed by successful repair can be included as context with appropriate loss masking; standalone failed output is not a positive label. Rejection sample only with legal teacher/data rights; record every candidate and verifier decision. Near-miss negatives for DPO only if attributable and matched.
7. **Quality review and freeze.** Enforce schema, deterministic replay, licensing, split and secret checks. Human-review high-risk and representative examples, stratify by task family/lineage/complexity, maintain rejected ledger; publish aggregate counts including failures, hashes and dataset card. No benchmark contamination from teacher prompting. Version data and evaluator separately; purge derivatives by source ID if rights change.
8. **Export after approval.** Separate immutable raw manifests and reviewed artifacts from training JSONL projection. Store tool content only in approved research dataset when rights allow; no remote tool output or private transcripts persisted in product memory. Preserve revision and hashes of dataset and export script; use same projection for untouched-base comparisons. No hidden evaluator content in model context.

## Proposed internal manifest schema (illustrative, not implementation)

```json
{
  "schema_version": 1,
  "example_id": "stable-id",
  "source": {
    "kind": "original|permissive_repo|licensed_history|synthetic_mutation",
    "url": null,
    "commit": "git-sha",
    "repo_lineage_id": "lineage-id",
    "license_spdx": "MIT",
    "license_text_sha256": "hash",
    "rights_review": "pending|approved|rejected",
    "attribution": [],
    "derived_from": [],
    "teacher": null
  },
  "split": "train|dev|private_test",
  "task": {
    "family": "authorization",
    "subfamily": "tenant-policy",
    "operator_version": "mutation-id@revision",
    "complexity": "multi-file",
    "prompt": "user-visible task"
  },
  "environment": {
    "php": "from-runtime",
    "laravel": "from-lockfile",
    "composer_lock_sha256": "hash",
    "image_digest": "sha256:...",
    "verifier_revision": "git-sha",
    "seed": 0
  },
  "initial_state": {"commit": "sha", "file_manifest_sha256": "hash"},
  "allowed_tools": ["read_file", "search", "propose_edit", "run_reviewed_test"],
  "trajectory": [
    {"role": "assistant", "action": {"tool": "read_file", "args": {}}, "train": true},
    {"role": "tool", "artifact_id": "approved-result", "sha256": "hash", "train": false}
  ],
  "proposal": {"schema_version": "frozen-protocol", "snapshot_sha256": "hash", "files": []},
  "verification": {
    "baseline_pass": true,
    "seeded_target_fail": true,
    "reference_pass": true,
    "wrong_repair_rejected": true,
    "lint_pass": true,
    "behavior_pass": true,
    "regression_pass": true,
    "scope_pass": true,
    "runs": [],
    "hidden_oracle_id": "private-only-reference"
  },
  "attempts": [],
  "repair_rounds": 0,
  "dedup": {"exact": "hash", "normalized": "hash", "cluster": "cluster-id"},
  "quality_flags": [],
  "review_status": "pending|machine_verified|human_reviewed|rejected",
  "generator_revision": "sha"
}
```

The manifest is not the model-facing record. Use separate access-controlled oracle registry; omit hidden_oracle_id and expected results from export. Actual tool arguments, sanitized evidence, observed feedback and snapshot-bound edit actions must be recoverable for approved training, not only result digests. Record denied actions separately, no implicit permission expansion. Framework version strings in the original report are examples, not pinned dependencies.

## Proposed pilot and quality measures

Start with 30–50 trusted development tasks and 60–100 private qualification tasks, multiple independent repositories and task families, stratified genuine multi-file subset. The existing public fixtures are smoke only. Do not use the private set to tune prompts or choose checkpoints; use development split for selection and a locked confirmatory test for pre-registered comparisons. Track accepted/generated counts, rejection reasons, flaky rate, missing trials, task-family distribution, split overlaps, oracle strength, teacher provenance, human review fraction and token length. Require 100% known-good/seed/reference/wrong controls and provenance for admitted examples; zero known train/holdout overlap or unapproved data. Freeze a small verified trajectory set (hundreds, then low thousands only if useful). Never claim dataset quality or training gain before actual execution.

## External knowledge

Teach how to ask for relevant evidence, check composer.lock and installed package source, apply version-aware guidance, and repair after test feedback. Keep evolving framework docs, optional Boost/MCP and skills in bounded transient context, not persistent memory or training snapshots without rights. Use the [agent guide](../../docs/AGENT_GUIDE.md) for existing authority rules.

## Maintainer clarification

Keep research-license 3B outputs out of commercial-intended training and distillation unless exact teacher/output rights are cleared. Private fixtures remain outside Git, prompts, teacher generation and training exports. Development selects models and settings; the locked private set confirms a predeclared choice. Do not generate trajectories from weak, blocked or unqualified evaluators.
