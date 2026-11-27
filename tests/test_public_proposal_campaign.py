"""Model-free workspace preparation and scope checks."""
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import tempfile
import unittest

from benchmarks.public_proposal_campaign import MANIFEST, prepare, inspect, plan, _same_open_file, _signature


class PublicProposalCampaignTests(unittest.TestCase):
    def test_public_plan_is_source_only_and_matches_all_corpus_tasks(self):
        manifest = plan()
        self.assertEqual(manifest["planned_tasks"], 12)
        self.assertEqual(manifest["planned_observations"], 87)
        self.assertFalse(manifest["semantic_qualification"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "campaign"
            self.assertEqual(prepare(root), manifest)
            self.assertEqual(json.loads((root / MANIFEST).read_text()), manifest)
            for task in manifest["tasks"]:
                project = root / task["project"]
                paths = {path.relative_to(project).as_posix() for path in project.rglob("*") if path.is_file()}
                self.assertEqual(paths, set(task["seed_sha256"]))
                self.assertTrue(all(path.endswith(".php") for path in paths))
                self.assertNotIn("reference", task)
                self.assertNotIn("expected", task)
            report = inspect(root)
            self.assertEqual(report["counts"], {"proposal_ready": 0, "no_change": 12, "scope_rejected": 0})
            self.assertEqual(report["attempted_semantic_observations"], 0)
            with self.assertRaises(FileExistsError):
                prepare(root)

    def test_changed_allowed_file_is_only_a_proposal_not_a_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "campaign"
            manifest = prepare(root)
            row = next(task for task in manifest["tasks"] if task["task"] == "booking_availability")
            path = row["allowed_edit_paths"][0]
            project = root / row["project"]
            (project / path).write_bytes(b"<?php // unexecuted candidate")
            report = inspect(root)
            result = next(task for task in report["tasks"] if task["task"] == row["task"])
            self.assertEqual(result["status"], "proposal_ready")
            self.assertEqual(result["changed_paths"], [path])
            self.assertEqual(set(result["candidate_sha256"]), set(row["allowed_edit_paths"]))
            self.assertFalse(report["semantic_qualification"])
            unrelated = next(path for path in row["seed_sha256"] if path not in row["allowed_edit_paths"])
            (project / unrelated).write_bytes(b"<?php // unrelated")
            result = next(task for task in inspect(root)["tasks"] if task["task"] == row["task"])
            self.assertEqual(result["reason"], "unapproved_source_change")

    def test_unknown_file_and_tampered_manifest_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "campaign"
            manifest = prepare(root)
            row = manifest["tasks"][0]
            (root / row["project"] / "unexpected.php").write_bytes(b"<?php")
            report = inspect(root)
            self.assertEqual(report["counts"]["scope_rejected"], 1)
            self.assertEqual(report["tasks"][0]["reason"], "unexpected_path")
            manifest["tasks"][0]["prompt"] = "tampered"
            (root / MANIFEST).write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "manifest_differs"):
                inspect(root)

    def test_linked_or_missing_candidate_is_not_opened(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "campaign"
            row = prepare(root)["tasks"][0]
            path = root / row["project"] / row["allowed_edit_paths"][0]
            path.unlink()
            self.assertEqual(inspect(root)["tasks"][0]["status"], "scope_rejected")
            target = Path(temp) / "outside"
            target.write_text("private")
            try:
                path.symlink_to(target)
            except (OSError, NotImplementedError):
                return
            self.assertEqual(inspect(root)["tasks"][0]["reason"], "link_or_reparse_point")

    def test_plan_bytes_reject_duplicate_fields_and_boolean_integer_alias(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "campaign"
            prepare(root)
            path = root / MANIFEST
            original = path.read_bytes()
            path.write_bytes(original.replace(b'"version": 1', b'"version": true'))
            with self.assertRaisesRegex(ValueError, "manifest_differs"):
                inspect(root)
            path.write_bytes(original.replace(b'"version": 1', b'"version": 2, "version": 1'))
            with self.assertRaisesRegex(ValueError, "manifest_differs"):
                inspect(root)

    def test_cross_provider_ctime_semantics_do_not_confuse_file_identity(self):
        info = dict(st_dev=4, st_ino=7, st_mode=stat.S_IFREG | 0o600,
                    st_nlink=1, st_size=8, st_mtime_ns=100, st_ctime_ns=10)
        path = SimpleNamespace(**info)
        opened = SimpleNamespace(**{**info, "st_ctime_ns": 200})
        self.assertTrue(_same_open_file(path, opened))
        self.assertNotEqual(_signature(path), _signature(opened))
        for changed in ({"st_ino": 9}, {"st_ino": 0}, {"st_nlink": 2},
                        {"st_size": 9}, {"st_mtime_ns": 101},
                        {"st_file_attributes": 0x400}):
            self.assertFalse(_same_open_file(path, SimpleNamespace(**{**info, **changed})))
