"""Exercise the contained evaluator with reviewed PHP before sending candidate code."""
import argparse
import json
from pathlib import Path
from time import monotonic

from .contained_php import CandidateFailure, EvaluationBlocked, ProbeDeadlineExceeded, PROBE_TIMEOUT, VERSION, observe


QUALIFICATION_BRIDGE = br"""<?php
declare(strict_types=1);
return static function (array $input): array {
    if ($input['mode'] === 'timeout') {
        sleep(25);
        return ['unexpected' => true];
    }
    if ($input['mode'] === 'memory') {
        if (ini_set('memory_limit', '-1') === false) {
            return ['unexpected' => true];
        }
        return ['unexpected' => strlen(str_repeat('x', 640 * 1024 * 1024))];
    }
    $status = file_get_contents('/proc/self/status');
    $mounts = [];
    foreach (file('/proc/self/mountinfo', FILE_IGNORE_NEW_LINES) as $line) {
        $parts = explode(' ', $line);
        $mounts[$parts[4]] = explode(',', $parts[5]);
    }
    $tmp = '/tmp/tinybuilder-isolation-probe';
    $scratch = file_put_contents($tmp, 'test') === 4 && file_get_contents($tmp) === 'test' && unlink($tmp);
    $checks = [
        'nonroot' => preg_match('/^Uid:\s+65534\s+65534\s+65534\s+65534$/m', $status) === 1,
        'no_new_privileges' => preg_match('/^NoNewPrivs:\s+1$/m', $status) === 1,
        'seccomp' => preg_match('/^Seccomp:\s+2$/m', $status) === 1,
        'loopback_only' => array_values(array_diff(scandir('/sys/class/net'), ['.', '..'])) === ['lo'],
        'readonly_root' => in_array('ro', $mounts['/'] ?? [], true),
        'readonly_fixture' => in_array('ro', $mounts['/fixture'] ?? [], true)
            && @file_put_contents('/fixture/fixture-marker', 'change') === false
            && file_get_contents('/fixture/fixture-marker') === 'original',
        'scratch' => $scratch
            && count(array_intersect(['rw', 'nosuid', 'nodev', 'noexec'], $mounts['/tmp'] ?? [])) === 4
            && disk_total_space('/tmp') <= 33554432,
        'memory_limit' => trim(file_get_contents('/sys/fs/cgroup/memory.max')) === '536870912',
        'pid_limit' => trim(file_get_contents('/sys/fs/cgroup/pids.max')) === '32',
        'cpu_limit' => trim(file_get_contents('/sys/fs/cgroup/cpu.max')) === '100000 100000',
        'sanitized_environment' => array_diff(array_keys(getenv()), ['HOME', 'PATH']) === [],
    ];
    return $checks;
};
"""
CHECKS = (
    "nonroot", "no_new_privileges", "seccomp", "loopback_only", "readonly_root",
    "readonly_fixture", "scratch", "memory_limit", "pid_limit", "cpu_limit",
    "sanitized_environment",
)


def qualify(docker: Path, image_id: str, approved_guest: bool) -> dict:
    report = {"status": "blocked", "image_id": image_id, "blocked_reason": None,
              "checks": dict.fromkeys(CHECKS)}
    report["checks"].update(memory_enforced=None, timeout_and_cleanup=None)

    def probe(mode):
        return observe(docker=docker, image_id=image_id, fixtures={"fixture-marker": b"original"},
                       request={"mode": mode}, trusted_bridge=QUALIFICATION_BRIDGE,
                       approved_guest=approved_guest)

    try:
        first = probe("inspect")
        if (first.image_id != image_id or first.protocol != VERSION
                or not isinstance(first.response, dict) or set(first.response) != set(CHECKS)):
            report["blocked_reason"] = "qualification_observation_unverified"
            return report
        report["fixture_sha256"] = first.fixture_sha256
        report["checks"].update({key: first.response[key] is True for key in CHECKS})
        if not all(report["checks"][key] for key in CHECKS):
            report["blocked_reason"] = "qualification_policy_failed"
            return report
        try:
            probe("memory")
        except CandidateFailure as error:
            report["checks"]["memory_enforced"] = error.reason == "candidate_resource"
        else:
            report["checks"]["memory_enforced"] = False
        start = monotonic()
        try:
            probe("timeout")
        except ProbeDeadlineExceeded:
            # observe() propagates cleanup failure instead of the original timeout.
            report["checks"]["timeout_and_cleanup"] = monotonic() - start >= PROBE_TIMEOUT - 1
        else:
            report["checks"]["timeout_and_cleanup"] = False
    except (EvaluationBlocked, CandidateFailure) as error:
        report["blocked_reason"] = error.reason
        return report
    except OSError:
        report["blocked_reason"] = "qualification_environment_error"
        return report
    if all(report["checks"].values()):
        report["status"] = "qualified"
    else:
        report["blocked_reason"] = "qualification_enforcement_failed"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", type=Path, required=True)
    parser.add_argument("--image-id", required=True)
    parser.add_argument("--approved-guest", action="store_true", required=True)
    args = parser.parse_args()
    report = qualify(args.docker, args.image_id, args.approved_guest)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "qualified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
