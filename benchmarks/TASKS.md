# Pinned, opt-in functional benchmark inventory

These are a **small starting set**, not a claimed 20–50-task benchmark.
Each task has independent acceptance checks. Adding new task families should
occur in reviewable increments with deterministic fixtures and negative controls.

| Task family | Public requirement | Evaluator controls | What counts as success |
| --- | --- | --- | --- |
| Composer smoke | Read hidden randomized package name and Laravel constraint | New Composer fixture per trial | Actual successful read plus exact unseen name and constraint |
| Health route | Add GET /health without changing existing routes | Hidden PHPUnit endpoint/home/sibling assertions | In-scope edit, reads, allowed tests after edit, full suite/route |
| Health repair | Fix seeded broken route and visible failing regression | Visible failure plus hidden endpoint/home/sibling assertions | Source/test reads before edit; no test edits; successful PHP suite |
| Contact validation | POST contact: required email and minimum-length message, JSON 422 | Failing visible/hidden tests and independently passing reference | Independent Laravel validation/route assertions and safe tool chronology |
| Route parameter | GET items/{id}: positive decimal integer -> exact JSON ID; otherwise 404 | Failing visible/hidden tests, including fractional/exponent rejection, and independently passing reference | Model must fix route only and pass independent PHP assertions |

Current Laravel pin used in the recorded Windows baseline and in the
optional manually-triggered reference workflow: application template
`laravel/laravel 13.11.0`, framework `laravel/framework 13.42.0`.
Transient dependencies still require the **generated composer.lock** identity
and committed baseline SHA for exact pairing within each campaign.

Real route-parameter reference controls have now passed on Windows and in the
[manual PHP reference workflow](../.github/workflows/laravel-controls.yml).
The [focused local follow-up](results/2026-11-16-parameter-followup.md) records actual
Ollama trials and a corrected false-positive oracle: accepting general numeric
strings is insufficient for the existing integer-only contract. Reference-control
passes do not count as model-generated task successes. The fresh corrected-oracle
3B parameter campaign passed 0/3 edits; the accompanying Composer smoke tasks
passed 2/3 with actual reads in all three.

No hidden tests, reference answers, model responses, or full project source
are embedded in public result summaries. The reference code lives in fixture
modules and is removed from each detached inference worktree before model
access. Never weaken independent acceptance to make a model pass.

Reference-only reports now include `baseline_commit` and
`composer_lock_sha256` metadata. The manually triggered PHP workflow displays
short fingerprints for cross-run comparison, not lockfile contents. This does
not make unpinned transitive dependency resolution deterministic; retain full
lockfile hashes for strict experiment pairing.
