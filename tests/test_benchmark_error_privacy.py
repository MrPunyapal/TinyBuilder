"""Model-error logging must never echo private exception contents."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.evaluate import task
from tinybuilder.model import ModelError


class RaisingModel:
    def __init__(self, error):
        self.error = error

    def complete(self, messages, tools, **kwargs):
        raise self.error


class ErrorPrivacyTests(unittest.TestCase):
    def test_model_http_error_body_is_not_printed_or_persisted(self):
        secret = "PRIVATE-MODEL-ERROR-TEXT"
        with tempfile.TemporaryDirectory() as directory:
            out = io.StringIO()
            with patch("benchmarks.evaluate.ChatModel",
                       return_value=RaisingModel(ModelError(secret, "http"))), \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(out):
                result = task("mock", Path(directory), "Inspect", tool_protocol="strict-json")
            self.assertIn("Model task failed: http", out.getvalue())
            self.assertNotIn(secret, out.getvalue())
            self.assertEqual(result["error"], "ModelError")
            self.assertEqual(result["error_kind"], "http")
            self.assertNotIn(secret, json.dumps(result))

    def test_local_exception_path_is_not_printed_or_persisted(self):
        private_path = "/private/unpublished-project/.env"
        with tempfile.TemporaryDirectory() as directory:
            out = io.StringIO()
            with patch("benchmarks.evaluate.ChatModel",
                       return_value=RaisingModel(OSError(private_path))), \
                 contextlib.redirect_stdout(io.StringIO()), \
                 contextlib.redirect_stderr(out):
                result = task("mock", Path(directory), "Inspect", tool_protocol="native")
            self.assertIn("Model task failed: execution", out.getvalue())
            self.assertNotIn(private_path, out.getvalue())
            self.assertEqual(result["error"], "OSError")
            self.assertNotIn(private_path, json.dumps(result))


if __name__ == "__main__":
    unittest.main()
