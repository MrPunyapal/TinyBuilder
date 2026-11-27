# Laravel corpus adversarial controls

The [original controls](2026-11-27-coding-v1-experiment.md#corpus-controls)
remain the historical baseline. The public corpus now varies validation
inputs, ownership, query data and keys, pricing inputs and boundaries. The
Dispatch lineage is labeled a public challenge because its verifier is in
Git.

The verifier checks five deliberately narrow repairs, including fixed item
IDs, fixed tax and surcharge results, and a patch that handles only the
visible deadline example. The public deadline check fails on the seeded task
and passes on the reference. The narrow repair also passes that public check
but fails the broader independent verifier. This qualifies the feedback
fixture. A model-driven correction round remains unmeasured.

The clinic and parcel tests apply evaluator-owned policy changes in separate
PHP processes. Each known hard-coded implementation passes the original
value checks and fails after the policy changes. The corresponding reference
continues to pass. Reverting either required file independently also fails
for both public multi-file tasks.

## Trusted PHP runs

The first Windows run with Herd PHP 8.5.13 reported a failed deadline
reference. Retain that result. A separate CLI OPcache witness read 11 in a
long-lived PHP process, rewrote the source to return 22, then read 11 in a
second default PHP process. With `-d opcache.enable_cli=0`, the second process
read 22. Trusted replay with CLI OPcache disabled passed all 12 public
controls, including five narrow witnesses, both dynamic policy checks and
the public-feedback boundary witness. All three worktrees returned to their
recorded Git revisions after verification, with evaluator tests removed.
[Initial and verified control records](../../benchmarks/results/2026-11-27-corpus-adversarial-controls.json)

To rebuild from an existing disposable Laravel baseline with reviewed local
Composer dependencies, run the source-corpus evaluator with an unused
output directory. Disable CLI OPcache for the verifier process. The
initial artifact was preserved and its replay wrote a separate report.

```text
python -m unittest discover -s tests -p test_coding_v1_corpus.py -v
python -m benchmarks.coding_v1_corpus --baseline BASELINE --output NEW_OUT --php PHP_EXECUTABLE
```

## Private holdout custody

Two original local Git lineages with two task families disjoint from the
public corpus are registered outside the TinyBuilder repository. Their
tests and reference changes stay in a directory with an explicit
current-user-only Windows ACL. The public and private applications use
the same reviewed Laravel framework skeleton and local dependency lock.
The private controls verified both references and both incorrect repairs.
One case requires edits in two files and fails when either reference file
is independently reverted.

The local manifest fingerprints the private source and baseline commits,
runtime and model hashes, and initial comparison settings. Its SHA-256 is
`25daac001c55a8b3f637a62b6bd0b9880cb58756458cfcf1520b5bd695ea2fde`.
The trusted control artifact SHA-256 is
`df89e927a46fb1150bb5a7ba7aa8429efcf79c523135b8f9f2fb4669abad5f1c`.
The first private default-OPcache validation did not complete. The verified
replay completed with CLI OPcache disabled. The exact broader driver and
contained image digests must be frozen before running either existing model.
The trusted fixture controls provide no live model qualification.
