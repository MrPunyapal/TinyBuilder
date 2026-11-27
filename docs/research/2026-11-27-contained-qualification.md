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
