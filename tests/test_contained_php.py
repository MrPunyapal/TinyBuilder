import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from benchmarks import contained_php as runner


IMAGE = "sha256:" + "a" * 64
INFO = {
    "OSType": "linux", "CgroupVersion": "2", "CgroupDriver": "systemd",
    "MemoryLimit": True, "SwapLimit": True, "CpuCfsQuota": True, "PidsLimit": True,
    "SecurityOptions": ["name=seccomp,profile=builtin"],
}


def configuration(stage):
    return {
        "HostConfig": {
            "NetworkMode": "none", "ReadonlyRootfs": True, "Privileged": False,
            "IpcMode": "private", "CgroupnsMode": "private", "PidMode": "",
            "PidsLimit": 32, "NanoCpus": 1_000_000_000, "Memory": 512 * 1024 * 1024,
            "MemorySwap": 512 * 1024 * 1024, "CapDrop": ["ALL"],
            "SecurityOpt": ["no-new-privileges"], "Tmpfs": {"/tmp": runner.TMPFS},
        },
        "Config": {"User": "65534:65534"},
        "Mounts": [{"Type": "bind", "Source": str(stage), "Destination": "/fixture", "RW": False}],
    }


class FakeDocker:
    def __init__(self, *, start_error=None, cleanup_residue=False, policy_change=None,
                 response=b'{"value":9}', attach_status=0, state_change=None):
        self.calls = []
        self.start_error = start_error
        self.cleanup_residue = cleanup_residue
        self.policy_change = policy_change
        self.response = response
        self.attach_status = attach_status
        self.state_change = state_change

    def __call__(self, argv, cwd, deadline_seconds, *, data):
        self.calls.append(argv[5:])
        args = self.calls[-1]
        if args[0] == "info":
            return 0, json.dumps(INFO).encode()
        if args[:2] == ["image", "inspect"]:
            return 0, json.dumps({"id": IMAGE, "volumes": None}).encode()
        if args[:2] == ["container", "create"]:
            return 0, b"id"
        if args[:2] == ["container", "inspect"]:
            if args[3] == "{{json .State}}":
                state = {"Status": "exited", "Running": False, "Error": "",
                         "ExitCode": self.attach_status, "OOMKilled": False}
                state.update(self.state_change or {})
                return 0, json.dumps(state).encode()
            policy = configuration(cwd / "fixture")
            if self.policy_change:
                self.policy_change(policy)
            return 0, json.dumps(policy).encode()
        if args[:2] == ["container", "start"]:
            if self.start_error:
                raise self.start_error
            assert json.loads(data) == {"input": 8}
            return self.attach_status, self.response
        if args[:2] == ["container", "rm"]:
            return 0, b""
        if args[:2] == ["container", "ls"]:
            return 0, b"survivor" if self.cleanup_residue else b""
        raise AssertionError("Unexpected Docker command")


def run_fake(engine, **overrides):
    parameters = dict(docker=Path("/usr/bin/docker"), image_id=IMAGE,
                      fixtures={"app/Service.php": b"<?php"}, request={"input": 8},
                      trusted_bridge=b"<?php return fn($request) => ['value'=>9];", approved_guest=True)
    parameters.update(overrides)
    with patch.object(runner, "_approved_runtime"), patch.object(runner, "_call", engine):
        return runner.observe(**parameters)


class ContainedPHPTests(unittest.TestCase):
    def test_requires_explicit_approved_linux_guest_without_fallback(self):
        for approved, platform in ((False, "linux"), (True, "win32")):
            with self.subTest(approved=approved, platform=platform):
                with patch.object(runner.sys, "platform", platform), patch.object(runner, "_call") as call:
                    with self.assertRaisesRegex(runner.EvaluationBlocked, "approved disposable Linux guest"):
                        runner.observe(docker=Path("/usr/bin/docker"), image_id=IMAGE,
                                       fixtures={}, request={}, trusted_bridge=b"", approved_guest=approved)
                    call.assert_not_called()

    def test_rejects_secret_test_escape_and_reserved_bridge_paths_before_launch(self):
        for path in ("../bad.php", "app/.env", "/root.php", "tests/Hidden.php",
                     "vendor/auth.json", "app/x.pem", "app\\x.php", "PROBE_ENTRY.php"):
            with self.subTest(path=path):
                engine = FakeDocker()
                with self.assertRaises(ValueError):
                    run_fake(engine, fixtures={path: b"hidden"})
                self.assertEqual(engine.calls, [])

    def test_fixture_digest_is_order_independent_and_binds_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            one = runner._stage(root / "one", {"app/A.php": b"A", "app/B.php": b"B"})
            two = runner._stage(root / "two", {"app/B.php": b"B", "app/A.php": b"A"})
            changed = runner._stage(root / "changed", {"app/B.php": b"B", "app/A.php": b"a"})
        self.assertEqual(one, two)
        self.assertNotEqual(one, changed)

    def test_approved_lifecycle_is_offline_bounded_and_returns_only_an_observation(self):
        engine = FakeDocker()
        observed = run_fake(engine)
        self.assertEqual(observed.response, {"value": 9})
        self.assertEqual(observed.image_id, IMAGE)
        self.assertEqual(len(observed.fixture_sha256), 64)
        create = next(call for call in engine.calls if call[:2] == ["container", "create"])
        for flag in ("--pull=never", "--network=none", "--read-only", "--user=65534:65534",
                     "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=32",
                     "--cpus=1", "--memory=512m", "--memory-swap=512m", "--log-driver=none"):
            self.assertIn(flag, create)
        self.assertNotIn("--privileged", create)
        self.assertEqual([call[:2] for call in engine.calls[-4:]],
                         [["container", "start"], ["container", "inspect"], ["container", "rm"], ["container", "ls"]])
        self.assertIsNone(getattr(observed, "passed", None))

    def test_broader_container_policy_is_blocked_before_start(self):
        for change in (
            lambda cfg: cfg["HostConfig"].update(NetworkMode="host"),
            lambda cfg: cfg["Mounts"][0].update(RW=True),
            lambda cfg: cfg["Mounts"].append({"Type": "bind", "Destination": "/unexpected"}),
            lambda cfg: cfg["HostConfig"].update(Tmpfs={"/tmp": "rw"}),
            lambda cfg: cfg["HostConfig"].update(Privileged=True),
        ):
            engine = FakeDocker(policy_change=change)
            with self.assertRaisesRegex(runner.EvaluationBlocked, "enforce evaluator policy"):
                run_fake(engine)
            self.assertNotIn(["container", "start"], [call[:2] for call in engine.calls])
            self.assertEqual([call[:2] for call in engine.calls[-2:]],
                             [["container", "rm"], ["container", "ls"]])

    def test_timeout_cleanup_and_unverified_cleanup_are_fail_closed(self):
        engine = FakeDocker(start_error=runner.EvaluationBlocked("container command deadline exceeded"))
        with self.assertRaisesRegex(runner.EvaluationBlocked, "deadline"):
            run_fake(engine)
        self.assertEqual([call[:2] for call in engine.calls[-2:]],
                         [["container", "rm"], ["container", "ls"]])
        with self.assertRaisesRegex(runner.EvaluationBlocked, "cleanup"):
            run_fake(FakeDocker(cleanup_residue=True))

    def test_untrusted_observation_must_be_strict_single_json(self):
        for raw in (b'{"value":1,"value":2}', b'9 10', b'{"x":NaN}', b'{"x":1e999}', b"\xff"):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(runner.CandidateFailure, "candidate_output"):
                    run_fake(FakeDocker(response=raw))

    def test_candidate_exit_requires_authoritative_state_and_successful_cleanup(self):
        with self.assertRaisesRegex(runner.CandidateFailure, "candidate_exit"):
            run_fake(FakeDocker(attach_status=17))
        with self.assertRaisesRegex(runner.CandidateFailure, "candidate_resource"):
            run_fake(FakeDocker(attach_status=137, state_change={"OOMKilled": True}))
        for change in ({"Status": "created"}, {"Error": "daemon error"}, {"ExitCode": 0}):
            with self.subTest(change=change), self.assertRaises(runner.EvaluationBlocked):
                run_fake(FakeDocker(attach_status=17, state_change=change))
        with self.assertRaisesRegex(runner.EvaluationBlocked, "cleanup"):
            run_fake(FakeDocker(attach_status=17, cleanup_residue=True))


if __name__ == "__main__":
    unittest.main()
