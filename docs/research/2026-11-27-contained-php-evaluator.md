# Contained PHP evaluator adapter

The Coding Intelligence lab now has an opt-in adapter for a reviewed,
disposable Linux evaluator guest. It uses a local Docker Unix socket and a
locally available probe image pinned by its exact `sha256:` image ID. The lab
never pulls an image or falls back to a local PHP execution path. An operator
must approve the guest, its isolation, and the image before calling the
adapter. The guest needs its own credential-free storage and no host mounts
or network access. Docker shares the guest kernel. The guest remains the
outer isolation boundary.

## Evaluation boundary

1. Build a secret-free fixture from an explicit map of relative paths and
   file bytes. Keep evaluator tests and expected results outside that map.
   The adapter stages fresh regular files, rejects traversal, common secret
   paths and test directories, and records a digest over all staged content.
   The caller remains responsible for reviewing included file contents.
2. Install the reviewed
   [PHP entry point](../../benchmarks/contained_php_probe.php) at
   `/tinybuilder/probe.php` in the approved image and make PHP available
   at `/usr/local/bin/php`. The image must have no declared volumes. A
   separately supplied trusted fixture bridge returns an observation
   callback. Keep this bridge outside the editable candidate manifest and
   keep its implementation free of hidden assertions or expected values.
3. Call `benchmarks.contained_php.observe` with an absolute path to the
   Docker binary, the exact image ID, the stage map, the trusted bridge bytes,
   one JSON input and the explicit `approved_guest=True` decision.
   Docker must report cgroup v2 resource controls and the built-in seccomp
   profile. The adapter inspects a fresh container before it starts, including
   its read-only root and fixture bind, isolated network, unprivileged user,
   disabled extra capabilities and CPU, RAM and PID budgets. A bounded tmpfs
   is available at `/tmp`.
4. Compare the untrusted observation with the expected result in a separate
   trusted evaluator process. Send a single hidden input to each fresh
   container. Use baseline, reference, known-wrong and regression controls.
   Treat container errors and cleanup failures as evaluator blockers.
5. Record only sanitized correctness, failure categories, hashes and
   timings. Keep raw model and container output out of persistent logs.
   Each invocation caps stdin/stdout, enforces a deadline and force-removes
   the container before checking that the daemon has no matching container.
   Stop the benchmark and discard the guest if cleanup cannot be verified.

The user-side fixture bridge and observable operations still need to be
written for each benchmark family. This permits black-box scoring without
putting PHPUnit or hidden expectations inside the candidate process. It
does not replace the existing restricted smoke-test lane or the read-only
release evaluator.

## Verified on the development host

The Windows host has WSL2 Ubuntu 22.04 installed and stopped. This check
found no Docker or Podman executable and no approved isolated Linux guest.
No container or model-generated PHP ran on this host. The model-free tests
check fail-closed preflight, staged paths, digest binding, policy inspection,
strict JSON, cleanup and the no-fallback boundary. They use a fake daemon.

```text
python -m unittest discover -s tests -p test_contained_php.py -v
python -m py_compile benchmarks/contained_php.py tests/test_contained_php.py
php -l benchmarks/contained_php_probe.php
```

Before broader model qualification, provision the approved guest and pinned
image. Run a known-safe smoke fixture and verify blocked network access,
read-only fixture and root, scratch limits, absent secrets, denial of extra
mounts, timeout and memory behavior, and force-removal on the actual daemon.
Then run the independent controls for a private held-out set. Guest-side
containment remains unverified until that smoke run.

[Docker container create](https://docs.docker.com/reference/cli/docker/container/create/) ·
[Docker container start](https://docs.docker.com/reference/cli/docker/container/start/) ·
[Default Docker seccomp profile](https://docs.docker.com/engine/security/seccomp/)
