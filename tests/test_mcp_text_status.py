"""MCP response text is data, not a LocalTools error status (no PHP/Ollama)."""

import json
import tempfile
import unittest
from pathlib import Path

from tinybuilder.agent import Agent
from tinybuilder.tools import LocalTools


class DocBridge:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error
        self.calls = []
        self.names = {"mcp_fake__documentation": (None, "documentation")}
        self.specs = [{"type": "function", "function": {
            "name": "mcp_fake__documentation", "description": "Get docs",
            "parameters": {"type": "object", "properties": {},
                           "additionalProperties": False}}}]

    def call(self, name, arguments):
        self.calls.append((name, arguments))
        if self.error is not None:
            raise RuntimeError(self.error)
        return self.content


class ToolThenFinal:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments
        self.round = 0

    def complete(self, messages, tools):
        self.round += 1
        if self.round == 1:
            return {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call-1", "type": "function", "function": {
                    "name": self.name, "arguments": json.dumps(self.arguments)}}]}
        return {"role": "assistant", "content": "Completed"


class MCPTextStatusTests(unittest.TestCase):
    def test_successful_mcp_text_does_not_masquerade_as_local_tool_error(self):
        for text in ("Permission denied: quoted manual", "Tool error: example output",
                     "File not found is a documentation phrase", "Invalid user input is described"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                bridge = DocBridge(content=text)
                events = []
                model = ToolThenFinal("mcp_fake__documentation", {})
                result = Agent(model, LocalTools(Path(directory)), mcp=bridge,
                               on_event=events.append).run("Read documentation")
                self.assertEqual(result, "Completed")
                self.assertEqual(bridge.calls, [("mcp_fake__documentation", {})])
                ends = [event for event in events if event["event"] == "tool_end"]
                self.assertEqual([(event["status"], event["reason"]) for event in ends],
                                 [("ok", "ok")])
                self.assertNotIn(text, json.dumps(events))
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_mcp_exception_is_still_reported_as_failure_without_leaking_it(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge = DocBridge(error="SENSITIVE_DOC_TEXT")
            events = []
            model = ToolThenFinal("mcp_fake__documentation", {})
            Agent(model, LocalTools(Path(directory)), mcp=bridge,
                  on_event=events.append).run("Read documentation")
            ends = [event for event in events if event["event"] == "tool_end"]
            self.assertEqual([(event["status"], event["reason"]) for event in ends],
                             [("error", "execution")])
            self.assertNotIn("SENSITIVE_DOC_TEXT", json.dumps(events))

    def test_disallowed_local_command_is_still_a_permission_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            events = []
            model = ToolThenFinal("run_command", {"argv": ["php", "artisan", "migrate:fresh"]})
            Agent(model, LocalTools(Path(directory), allow_exec=True,
                                    exec_commands=[["php", "artisan", "test"]]),
                  on_event=events.append).run("Run command")
            ends = [event for event in events if event["event"] == "tool_end"]
            self.assertEqual([(event["status"], event["reason"]) for event in ends],
                             [("error", "permission")])


if __name__ == "__main__":
    unittest.main()
