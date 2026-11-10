import json
import tempfile
import unittest
from pathlib import Path

from tinybuilder.agent import Agent
from tinybuilder.tools import LocalTools


class FakeModel:
    def __init__(self):
        self.calls = []

    def complete(self, messages, tools):
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            return {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call_1", "type": "function", "function": {
                    "name": "read_file", "arguments": json.dumps({"path": "composer.json"})}}]}
        return {"role": "assistant", "content": "Project inspected.", "tool_calls": []}


class TestAgent(unittest.TestCase):
    def test_tool_loop_and_no_storage(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "composer.json").write_text('{"require":{"laravel/framework":"^12.0"}}')
            model = FakeModel()
            agent = Agent(model, LocalTools(root), preferences={"test runner": "Pest"})
            self.assertEqual(agent.run("Inspect the project"), "Project inspected.")
            first_messages = model.calls[0][0]
            self.assertIn("Laravel", first_messages[0]["content"])
            self.assertIn("Pest", first_messages[0]["content"])
            second_messages = model.calls[1][0]
            self.assertEqual(second_messages[-1]["role"], "tool")
            self.assertIn("laravel/framework", second_messages[-1]["content"])
            self.assertEqual(len(list(root.iterdir())), 1)
