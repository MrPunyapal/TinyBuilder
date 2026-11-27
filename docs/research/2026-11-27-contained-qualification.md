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

Use the approved VirtualBox Base environment with an Ubuntu Server x64
guest, 2 vCPUs, 3–4 GiB RAM and a 25–40 GB dynamic disk on E:. Patch and
provision the clean guest, record Docker and kernel versions, and pin the
local probe image by exact ID. The image uses the checked-in probe entry
point at `/tinybuilder/probe.php`. Do not reuse host credentials or share
personal drives. Disable guest network adapters, clipboard, drag-and-drop
and shared folders before running trusted qualification. Verify these
outer controls independently of Docker settings.

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
