"""Execute only checked-in trusted corpus controls, never model/candidate input.

The subprocess adapter exists in this test module only. It does not exercise
Docker, guest isolation or inference. No vendor or framework is needed.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from benchmarks.coding_v1_corpus import REPOSITORIES, WRONG_REPLACEMENTS, NARROW_WITNESSES
from benchmarks.contained_corpus import TAX_PATH, score_tax
from benchmarks.contained_php import Observation
from benchmarks.contained_public import TASKS, score_public

PHP = shutil.which("php")
IMAGE = "sha256:" + "1" * 64
ROOT = Path(__file__).resolve().parents[1]
SUPPORTED = {
    "patient_visibility": 9, "urgent_reminders": 2, "booking_availability": 14,
    "exempt_tax": 9, "priority_normalization": 4, "deadline_boundary": 10,
    "rural_quote": 6, "parcel_weight": 18,
}


def controls():
    for _, files, tasks in REPOSITORIES.values():
        for task in tasks:
            if task.name not in SUPPORTED:
                continue
            baseline, reference, wrong = {}, {}, {}
            for (cls, old, new), replacement in zip(task.changes, WRONG_REPLACEMENTS[task.name], strict=True):
                path = f"app/CodingV1/{cls}.php"
                original = files[cls]
                if original.count(old) != 1:
                    raise AssertionError("Trusted fixture changed")
                baseline[path] = original.encode()
                reference[path] = original.replace(old, new, 1).encode()
                wrong[path] = original.replace(old, replacement, 1).encode()
            variants = {"baseline": baseline, "reference": reference, "wrong": wrong}
            if task.name in NARROW_WITNESSES:
                variants["narrow"] = {
                    f"app/CodingV1/{cls}.php": files[cls].replace(old, new, 1).encode()
                    for (cls, old, _), new in zip(task.changes, NARROW_WITNESSES[task.name], strict=True)
                }
            if len(reference) > 1:
                for path in reference:
                    variants[f"revert:{path}"] = {**reference, path: baseline[path]}
            if task.policy:
                path = f"app/CodingV1/{task.policy.consumer_class}.php"
                old, new = (v.encode() for v in task.policy.hardcoded_reference)
                if reference[path].count(old) != 1:
                    raise AssertionError("Trusted policy fixture changed")
                variants["hardcoded"] = {**reference, path: reference[path].replace(old, new, 1)}
            yield task.name, variants


class TrustedBridgeInventoryTests(unittest.TestCase):
    def test_exact_public_pure_php_coverage(self):
        self.assertEqual(set(TASKS) | {"exempt_tax"}, set(SUPPORTED))
        self.assertEqual(sum(SUPPORTED.values()), 72)
        self.assertEqual({name for name, _ in controls()}, set(SUPPORTED))
        for name, spec in TASKS.items():
            self.assertEqual(len(spec.probes), SUPPORTED[name])


@unittest.skipUnless(PHP, "PHP unavailable; trusted bridge controls not executed")
class TrustedBridgeTests(unittest.TestCase):
    def test_reference_wrong_seeded_and_adversarial_controls(self):
        # No arbitrary bytes, command arguments or file paths enter this test
        # from users, a model, Git worktrees, environment or fixture transfer.
        for name, variants in controls():
            for variant, files in variants.items():
                with self.subTest(task=name, variant=variant):
                    allowed = [files]
                    if name in TASKS and TASKS[name].policy_variant:
                        path, content = TASKS[name].policy_variant
                        allowed.append({**files, path: content})

                    def trusted_observe(*, fixtures, request, trusted_bridge, **kwargs):
                        self.assertIn(fixtures, allowed)
                        with TemporaryDirectory(prefix="tinybuilder-trusted-test-") as temp:
                            root = Path(temp)
                            for relative, content in fixtures.items():
                                target = root / relative
                                target.parent.mkdir(parents=True, exist_ok=True)
                                target.write_bytes(content)
                            # Use relative paths only in trusted, checked-in bridge
                            # and entrypoint. The production paths remain unchanged.
                            bridge = trusted_bridge.replace(b"'/fixture/", b"__DIR__ . '/")
                            (root / "probe_entry.php").write_bytes(bridge)
                            entry = (ROOT / "benchmarks/contained_php_probe.php").read_bytes()
                            (root / "probe.php").write_bytes(entry.replace(b"'/fixture/", b"__DIR__ . '/"))
                            result = subprocess.run(
                                [PHP, "-n", str(root / "probe.php")], cwd=root,
                                input=json.dumps(request).encode(), capture_output=True, timeout=5,
                            )
                            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
                            manifest = {key: hashlib.sha256(value).hexdigest()
                                        for key, value in sorted(fixtures.items())}
                            digest = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
                            return Observation(json.loads(result.stdout), digest, IMAGE)

                    module = "contained_corpus" if name == "exempt_tax" else "contained_public"
                    with (patch(f"benchmarks.{module}.require_qualified_guest"),
                          patch(f"benchmarks.{module}.observe", side_effect=trusted_observe)):
                        kwargs = dict(docker=Path("/unused"), image_id=IMAGE, approved_guest=True)
                        if name == "exempt_tax":
                            report = score_tax(files[TAX_PATH], **kwargs)
                            passed = sum(report[phase]["passed"] for phase in ("behavior", "regression"))
                            failed = sum(report[phase]["failed"] for phase in ("behavior", "regression"))
                        else:
                            report = score_public(name, files, **kwargs)
                            passed, failed = report["passed"], report["failed"]
                    self.assertEqual(report["status"], "completed")
                    self.assertEqual(passed + failed, SUPPORTED[name])
                    if variant == "reference":
                        self.assertEqual(passed, SUPPORTED[name])
                    else:
                        self.assertGreater(failed, 0)
                        if variant == "hardcoded":
                            self.assertEqual(report["phases"]["behavior"]["failed"], 0)
                            self.assertGreater(report["phases"]["policy_mutation"]["failed"], 0)
