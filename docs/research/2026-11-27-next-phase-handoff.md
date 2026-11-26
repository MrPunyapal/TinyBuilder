# Coding Intelligence v1 continuation

## Code and tests at this checkpoint

- The Python 3.10 fix is `978dad55efb98a19a8a81d6815f60184096d21f9`.
  Both benchmark digest paths use bounded streaming reads. The focused
  regression tests ran on WSL Python 3.10.12. Python 3.10, 3.12 and 3.13
  passed on the fix commit. [CI](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45892510629)
- The integrated branch carries the exact PR #22 guidance and Ubuntu
  packaging update from current main. The original Windows prototype
  remains in its separate local worktree.
- [Source identifier experiment](2026-11-27-source-id-comparison.md) is
  frozen at `62463fbbc31e4806ad60257144bc75c40066d21a`. The first attempt
  stopped at a failing known reference before any inference. A separate
  trusted probe reproduced a Windows CLI OPcache stale-source hazard.
  `9585b26d61c04e7000e0dac29df20be986931a74` disables that cache for every
  rewritten-source PHPUnit control. The output from both attempts is
  retained independently.
- The [public corpus and private holdout controls](2026-11-27-corpus-adversarial-controls.md)
  passed 12/12 and 2/2 respectively on trusted code. Private source,
  assertions and references stay outside Git under the owner's ACL.
  The exact guest, image and broader driver still need to be frozen before
  any model evaluates the private set.
- The [contained evaluator](2026-11-27-contained-php-evaluator.md) passed
  ten model-free tests. It includes a public tax oracle with the same nine
  inputs as the PHPUnit controls. It needs a verified isolated Linux guest,
  an approved local image and live safety smoke tests. Structured blocked
  denominators and failure attribution are prerequisites for qualification.
- The [exact-main release rehearsal](2026-11-27-exact-main-release-rehearsal.md)
  verified all three candidate payloads. The Windows package passed 10/10
  genuine reads and lifecycle cleanup on the elevated development PC.
  Clean standard-user Windows, Ubuntu 22.04 and Apple Silicon acceptance
  remain open.

The corpus, containment and release verification ran in independently
scoped worktrees. The lead reviewed and integrated the changes. PHP caching
is disabled in the evaluator itself, so operators need no separate skill
procedure. Existing repository skills cover the remaining workflow, and
no permanent Codex profiles are needed. PR #21 still owns the canonical
project-status refresh.

## Continue without duplicating the run

The source-ID campaign uses the existing 1.5B and 3B weights sequentially.
The local first-attempt report sits in the `coding-v1-source-ids` output
folder under the release evidence root. The retry writes to
`coding-v1-source-ids-retry/pilot.json`. Check the retry output and active
processes before considering a rerun. Record all 18 planned trials or their
blocked status. Then rerun or collect integrated Python, Rust, acceptance
and guidance checks on the exact pushed commit.

Prepare one draft successor for review after recording the integrated
evidence. Keep PRs #18 and #20 for provenance until a maintainer approves
the successor. Keep native clean-host acceptance separate. Use only
existing weights and defer training.
