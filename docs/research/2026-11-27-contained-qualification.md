# Contained coding qualification checkpoint

PR [#23](https://github.com/MrPunyapal/TinyBuilder/pull/23) continues from
maintainer checkpoint `4559cec5f62590ebccd440885ec2b998462dbde8`.
That head passed 20 GitHub checks and had one skip. Current main
`ff05f4ef232ebe161f69cbc8cf5dbe49b703fafd` passed its five workflows.
The branch incorporates the merged PR #21 and #24 content. Both read
qualification oracles and the product entry point match main byte for byte.

## Prepared and verified without a guest

- The adapter checks authoritative container state after attachment. Proven
  nonzero candidate exits, out-of-memory kills and malformed output have
  separate failure types. Unknown outcomes and failed cleanup block scoring.
- Tax, bookings, parcel intake and deadline scoring keep expected values
  outside the probe. The booking and parcel bridges exercise two-file changes,
  dynamic policy values and regression checks. Deadline feedback exposes
  one public observation. The independent ten-case oracle still rejects a
  narrow patch that only passes that public feedback.
- Trusted PHP 8.5.13 controls counted 14/14 booking, 18/18 parcel and 10/10
  deadline reference probes. Every seeded and known-wrong control failed
  at least one probe, and each one-file revert failed. These spot checks and
  the model-free daemon tests cover the bridges and attribution. The
  candidate PHP isolation environment needs a live check.

## Guest safety gate

The current Windows host is no longer a provisioning target. Its evaluator
VM was stopped and the local VirtualBox setup was removed. Use a separately
approved Linux evaluator when live qualification resumes. The Windows rollback
restart is deferred and does not block model-free lab work.

Do not resume the cancelled Windows VM setup or make further system-level
changes on the owner's personal PC. The earlier VirtualBox sizing and E:
placement were planning assumptions for the abandoned provisioning attempt,
not current instructions. For a separately approved disposable Linux
evaluator, verify its outer isolation, secret-free storage and no host
integration before invoking the trusted probes. Pin reviewed OS, Docker,
kernel and image identities. The image uses the checked-in probe entry
point at `/tinybuilder/probe.php`. Ordinary hosted CI may validate trusted
public code and mocks, but is not automatically approved to execute
model-generated PHP. No private fixture, model weight or candidate transfer
without separate approval. If a suitable environment is unavailable, the
live gate remains blocked.

```text
python -m benchmarks.qualify_contained_php --docker /usr/bin/docker --image-id EXACT_LOCAL_ID --approved-guest
```

The trusted probes verify non-root execution, no-new-privileges, active
seccomp, loopback-only networking, read-only root and fixture, bounded
scratch, absence of inherited environment variables, cgroup limits, an
enforced memory kill and timeout cleanup. Preserve the report even if one
check fails. Record real guest results before letting generated PHP run.
Reports preserve bounded blocked categories for approval, Docker and image
availability, policy, execution state, transport, timeouts and cleanup.
Raw daemon messages stay out of evidence. A failed removal command still
requires an independent container inventory. Missing inventory or a remaining
container blocks the trial. The existing candidate failures and denominators
stay separate.

Model-free regression check:

```text
python -m unittest discover -s tests -p "test*contained*.py"
```

## Evaluation sequence

Start with the existing models and exact-text/selective lexical settings on
development fixtures. Include a full two-file task and a feedback retry.
Freeze controller, corpus, limits, model and image digests before private
confirmation. The private two-task set remains a pilot. Its source,
assertions and expected values stay out of model context and Git. Hold
MiniCPM5-2B for a named decision after the existing-model baseline.

For a public development task, use only a secret-free disposable source
copy. Keep hidden tests in the separate scorer. The lab requires an explicit
write opt-in, retrieves context without receiving a path hint, checks its
proposed path against an evaluator-owned allowlist, and prompts for approval.
Repeat for a second proposal only within the frozen task budget. Transfer
candidate source bytes to the offline guest and run the family scorer there.
For feedback, send only the separate public probe observation to the model.

```text
grounded_lab --project DISPOSABLE --runtime RUNTIME --model EXISTING_GGUF edit --allow-write --selective-context --allowed-edit-path app/CodingV1/Booking.php --allowed-edit-path app/CodingV1/BookingRules.php "TASK"
python -m benchmarks.contained_public --task booking_availability --docker /usr/bin/docker --image-id EXACT_LOCAL_ID --candidate Booking.php --candidate BookingRules.php --approved-guest
```

## Remote maintainer review

At `0ecc06f6b853c83699110f17b918b4cbcfcd7ef6`, all seven retrieved
GitHub workflows passed. The branch includes all ten files introduced or
changed by merged research PRs #21 and #24 (nine identical blobs, with a
newer project-status snapshot). The native product entry point and both
read qualification oracles match main. Actual Git ancestry lagged main;
this follow-up reconciles it without force-pushing or discarding lab work.
All 18 #18 changed paths and all 14 #20 changed paths exist in the lab;
several are evolved rather than byte-identical. This inventory is not a
complete semantic supersession review. Preserve both original drafts until
that review and explicit approval. The Windows rollback status is reported
by local Codex, not independently verified remotely. No guest was qualified
and no system changes, model execution or training were performed here.

## Independent review checkpoint

Reviewed starting head `4caf8c8d9fe1f8e3f8222ba8db6efccc7a7f8eac`
against main `ff05f4ef232ebe161f69cbc8cf5dbe49b703fafd`. Independently
compared blob identities for the native product entry point, both read
oracles and native package workflow; all four matched. Shared runtime
completion handling retains the finish-reason gate. Agent edits require
complete fresh evidence and approval; grounded lab checks allowed paths.
Filesystem checks are not race-proof against a hostile concurrent writer.

Fixed a cross-project patch-binding weakness in [5a1bb8a](https://github.com/MrPunyapal/TinyBuilder/commit/5a1bb8ada7d10c614c2a574510449fb7e7634528):
a patch previously carried a relative path and content hash but no project
root. It now carries the originating canonical root; application to another
root is rejected. Added a model-free two-project regression test. This does
not establish hostile-filesystem containment. New exact-head CI is required.

Starting-head CI observed successful guidance, security, Python and native
deterministic workflows; native rewrite and packages were still running at
last inspection. No independent local test execution. PR #18 head is an
ancestor; #20 diverges and was replayed. All changed paths retained, but
full semantic supersession and complete integrated diff review remain open.
Do not close either draft or merge #23 yet. No new skill is warranted: the
existing implementation and benchmark skills already require scoped approval,
regression tests and containment. No model execution, private transfer,
training, host changes or publication performed. Next: verify new exact-head
CI, finish benchmark and replay review before an experimental merge decision.

## Independent review continuation — model-free safety closure

At [9167b70](https://github.com/MrPunyapal/TinyBuilder/commit/9167b70c788682771eb5e86759a50c0ddf717ff5),
two legacy execution paths were disabled. The old Laravel pilot discards
model previews as containment-blocked; trusted wrong-repair comparators
retain host scoring. Route validation requires trusted-controls-only and
never invokes model inference or runs generated PHP. Historical results,
fixture definitions and controls remain. The created container is now
verified against the approved image ID, executable and exact arguments.
[48bc76b](https://github.com/MrPunyapal/TinyBuilder/commit/48bc76b26b1a48935eec0cdc96740f882d27b9d2)
requires trusted live qualification before candidate submission in both
contained public scoring entrypoints. Failed preflight leaves zero attempts
and all probes remaining. Regression tests use mocks only. Outer guest
approval remains external; no model, Docker or guest was executed here.

Compared every #18 (18 paths) and #20 (14 paths) changed file against the
integrated branch; no missing paths. #18 ancestry is direct; #20 was replayed.
Original #20 cross-file fixture/benchmark, workflow fixture, benchmark result,
vision and historical cross-file/workflow reports and workflow tests match
byte-for-byte. Evolved controller preserves the original A/C arms and seat
policy order while adding comparison arms, token usage and finish attribution;
Python hash helper replaces Python-3.11-only digest, tests and protocol expand.
Original #18 diagnostics, workbench, agent, workflow, lab export and result
remain; scope and snapshot guards are strengthened. The old semantic execution
workflow is intentionally superseded, not a lost feature to restore. Full
Laravel contained scoring remains open. The review compared blobs and changed
source behavior, not independent re-execution of all historical experiments.
Keep original drafts for provenance until explicit approval to supersede.

Exact-head 99c1eec: [native deterministic](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45996517384)
passed all three platform jobs, [Python](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45996517260),
[guidance](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45996517240) and
[security](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45996517253) passed.
Native rewrite and package runs were cancelled on branch advancement. Later
commits need their own CI; direct clone from review container failed DNS, so
no independent local test claim. Experimental merge is conditional on final
exact-head CI and owner approval, not on a live model qualification claim.
No releases, training, paid compute, downloads, private transfer, Windows
system changes, or merges performed. Benchmark skill and active lab docs
updated; no new skill needed. Next: validate final-head hosted trusted CI;
then review an experimental-only merge, retaining the separate live gate.

## Public bridge expansion — trusted controls only

Expanded the dependency-free public contained scoring lane from four to
eight of the twelve corpus tasks: patient visibility (9 observations),
urgent reminders (2), priority normalization (4), rural quote (6), plus
existing tax (9), booking (14), deadline (10) and parcel (18). Total 72
planned observations across the reference suite. Every expected value stays
outside PHP. The new test executes only fixed repository-authored baseline,
reference, known-wrong, narrow, partial and hardcoded policy controls through
the actual reviewed PHP bridge and probe entrypoint with temporary relative
paths. It skips explicitly if PHP is absent. This is trusted code testing,
not a Docker or live model run; it may be run on ordinary hosted CI.

The remaining four tasks (contact validation, available stock, group
inventory, listing response) require real Laravel/Illuminate dependencies,
including SQLite for the database tasks. Do not replace them with imitation
framework stubs or weaken the original PHPUnit oracles. Implement and review
the framework bridge with an exact trusted dependency/lockfile and image
manifest, no host mounts or network, then run its trusted controls in the
separately approved evaluator. Full route-validation and private bridges
also remain pending. Do not provision the owner's personal PC.

At b237aa9, Python, native deterministic, guidance and candidate security
workflows passed; native rewrite and package workflows were running.
The current bridge expansion needs exact-head CI. Direct GitHub access
from the review container failed DNS; repository changes were made via
the connected GitHub API. No candidate, guest, model, or private data ran.

## Framework bridge implementation and source packaging correction

At 919bf89, checkout Python 3.13 passed all 278 tests, including actual
trusted PHP controls; the extracted sdist failed because it omitted
benchmarks/contained_php_probe.php (34 errors). Other five retrieved
workflows passed. The manifest now includes that exact trusted PHP asset;
no tests were skipped to mask the failure.

The framework bridge source now covers contact validation (7), stock
listing (3), group inventory (3), and listing response (2). Together with
72 dependency-free probes, all 12 public tasks have 87 planned observations.
The real Laravel/Illuminate bootstrap is required, not stubs. The image
must supply the reviewed app and Composer dependencies under
/tinybuilder/laravel. Framework tasks require an explicit reviewed
composer.lock SHA-256 and verify version 13.42.0, lock identity, SQLite,
validation and response capabilities with a trusted preflight before any
candidate bytes. The fixed Item dependency is staged from reviewed source,
not candidate input. Nested observation types are compared strictly.
A narrowly scoped trusted CI workflow uses the existing project Laravel
version pins; it resolves transitive dependencies and logs the lock digest,
which is development evidence, not an approved image or frozen release
lock. Tests run only repository-authored controls. No arbitrary candidate
execution, Docker, weights or private fixtures on CI.

Full HTTP route validation, independently held private fixtures, exact
reviewed offline image construction and live guest qualification remain
separate gates. An app that boots in ordinary CI may still fail in the
read-only container; live trusted preflight must establish that. Keep the
personal Windows host outside provisioning.

## Separate public HTTP route bridge

At 1554af7, the dedicated real Laravel trusted-control workflow
[46000801927](https://github.com/MrPunyapal/TinyBuilder/actions/runs/46000801927)
passed with no inference and no Docker execution. All 12 corpus tasks now
have implemented and trusted-control-tested bridges. Source-distribution
verification and remaining native CI were still running at this inspection.

The separate route_validation bridge uses a real Laravel HTTP kernel over
the candidate routes/web.php and trusted image app dependencies. Nine
observations cover malformed/missing fields, wrong message type, exact
minimum length, valid responses, home and a fixed sibling route. Expected
observations stay outside PHP. A trusted reference HTTP preflight runs
before any candidate can be blamed for app bootstrap, view or validation
failures. Uses test-only fixed settings, array cache/session, temporary
compiled views and no production secrets. This is a separate public
evaluation, not a change to the historical full PHPUnit oracle. Actual
read-only guest behavior still needs qualification.

Next physical-access step is only to reconcile and verify already present
trusted model/runtime identities and, if separately approved, conduct
inference-only proposal generation on disposable public source. Do not
execute those proposals, provision Windows, transfer private data or
download weights. The isolated evaluator needs separate approval; local
Codex access alone is not approval to run generated code.

## Local inference-only handoff preparation

The public source-only proposal campaign now generates 12 independent
project directories with the seeded public repository classes and a
manifest outside every model-facing root. It exposes task prompts,
allowed paths, per-task edit budgets and source hashes, not hidden
assertions, reference implementations or private fixtures. This is a
new explicitly labeled source-only proposal condition, not the original
full Laravel repository experiment or semantic qualification.

```text
python -m benchmarks.public_proposal_campaign prepare --output NEW_PUBLIC_CAMPAIGN_DIR
python -m benchmarks.public_proposal_campaign inspect --root PUBLIC_CAMPAIGN_DIR
```

Inspect reports planned task/probe totals, no-change, proposal-ready and
scope-rejected counts; it rejects unknown paths, missing sources, links,
reparse points, oversized files, out-of-scope changes and altered plan.
It never invokes a subprocess, a model or PHP, and never transfers files.
It cannot establish race-proof safety against hostile concurrent writers.
Do not use private source or an ordinary development project as its root.

For each task use only the task's own project root and prompt from the
outside plan. Existing grounded_lab remains the per-action approval
boundary: selective-context, exact-text edits, explicit allowed paths,
and no more than the recorded patch budget. Do not pass the entire
manifest or evaluator repository to the model. Record model/runtime
identity and all attempted, rejected and missing proposals locally.
After inference inspect the campaign. A proposal-ready status is not a
semantic pass, and all 87 semantic observations remain unattempted.
Candidate scoring still requires a separate qualified evaluator.
No system installation, weight download or candidate execution is part
of these commands.
