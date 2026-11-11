import json
import tempfile
import unittest
from pathlib import Path

from tinybuilder.agent import Agent
from tinybuilder.protocol import (ProtocolError, parse_strict_action,
                                  validate_local_arguments, validate_native_calls)
from tinybuilder.tools import LocalTools


class SequenceModel:
    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []
        self.formats = []

    def complete(self, messages, tools, **kwargs):
        self.requests.append((list(messages), list(tools)))
        self.formats.append(kwargs.get("response_format"))
        return self.answers.pop(0)


def action(name, **arguments):
    return {"content": json.dumps({"type": "tool", "name": name, "arguments": arguments})}


class TestProtocol(unittest.TestCase):
    def test_constrained_server_output_still_rejects_fences_and_unknown_tools(self):
        with tempfile.TemporaryDirectory() as d:
            model = SequenceModel({"content": '```json\n{"type":"final","content":"secret"}\n```'},
                                  {"content": '{"type":"tool","name":"secret-unknown","arguments":{}}'})
            events = []
            with self.assertRaises(ProtocolError):
                Agent(model, LocalTools(Path(d), allow_write=True), tool_protocol="strict-json",
                      strict_json_profile="constrained", on_event=events.append).run("inspect")
            self.assertTrue(all(format_["type"] == "json_schema" for format_ in model.formats))
            self.assertFalse(any(e["event"] == "tool_start" for e in events))
            self.assertNotIn("secret", json.dumps(events))
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_constrained_profile_preserves_permissions_and_exact_argv(self):
        for allow_write, allow_exec in [(False, False), (True, True)]:
            with self.subTest(allow_write=allow_write), tempfile.TemporaryDirectory() as d:
                model = SequenceModel(action("write_file", path="new.php", content="example"),
                                      action("run_command", argv=["php", "artisan", "migrate:fresh"]),
                                      {"content": '{"type":"final","content":"Done"}'})
                events = []
                Agent(model, LocalTools(Path(d), allow_write=allow_write, allow_exec=allow_exec,
                                       exec_commands=[["php", "artisan", "test"]]),
                      tool_protocol="strict-json", strict_json_profile="constrained",
                      on_event=events.append).run("inspect")
                ends = [e for e in events if e["event"] == "tool_end"]
                self.assertEqual(ends[0]["status"], "ok" if allow_write else "error")
                self.assertEqual(ends[1]["reason"], "permission")
                self.assertEqual((Path(d) / "new.php").exists(), allow_write)

    def test_strict_schema_accepts_correct_tool_and_final(self):
        self.assertEqual(parse_strict_action(action("read_file", path="composer.json")["content"])["name"], "read_file")
        self.assertEqual(parse_strict_action('{"type":"final","content":"OK"}')["content"], "OK")

    def test_reject_fences_prose_multiple_objects_duplicates_oversize_and_mixed(self):
        invalid = [
            '```json\n{"type":"tool","name":"read_file","arguments":{"path":"x"}}\n```',
            'I will call: {"type":"tool","name":"read_file","arguments":{"path":"x"}}',
            '{"type":"final","content":"ok"}{"type":"final","content":"bad"}',
            '{"type":"final","type":"tool","content":"ok"}',
            '{"type":"final","content":"ok","arguments":{}}',
            '{"type":"final","content":"' + 'x' * 65_000 + '"}',
            '[]',
            '{"type":"tool","name":"read_file","arguments":{"path":"x"},"content":"oops"}',
            '{"type":"tool","name":"read_file","arguments":{"path":"x"}}\nI did it',
        ]
        for value in invalid:
            with self.subTest(value=value[:40]), self.assertRaises(ProtocolError):
                parse_strict_action(value)

    def test_reject_unknown_tool_and_schema_examples_as_args(self):
        for name, arguments in [
            ("read_composer_json", {"path": "composer.json"}),
            ("read_file", {"path": {"type": "string"}}),
            ("read_file", {"path": "x", "extra": "surprise"}),
            ("read_file", {}),
            ("write_file", {"path": "x", "content": 34}),
            ("run_command", {"argv": "php artisan test"}),
            ("run_command", {"argv": ["php", "", "test"]}),
            ("run_command", {"argv": ["php"] * 26}),
        ]:
            with self.subTest(name=name, arguments=arguments), self.assertRaises(ProtocolError):
                parse_strict_action(json.dumps({"type": "tool", "name": name, "arguments": arguments}))

    def test_native_malformed_batch_is_atomic(self):
        batch = [
            {"function": {"name": "write_file", "arguments": '{"path":"x","content":"bad"}'}},
            {"function": {"name": "read_file", "arguments": '{"path":{"type":"string"}}'}},
        ]
        with self.assertRaises(ProtocolError):
            validate_native_calls(batch)

    def test_native_ollama_object_arguments_are_accepted(self):
        calls = validate_native_calls([{"function": {"name": "read_file", "arguments": {"path": "composer.json"}}}])
        self.assertEqual(calls[0]["function"]["name"], "read_file")
        self.assertEqual(json.loads(calls[0]["function"]["arguments"]), {"path": "composer.json"})

    def test_strict_json_multi_round_read_write_final(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            (project / "routes").mkdir()
            (project / "routes/web.php").write_text("<?php\n")
            model = SequenceModel(action("read_file", path="routes/web.php"),
                                  action("write_file", path="routes/web.php", content="<?php\n// test\n"),
                                  {"content": '{"type":"final","content":"Changed routes/web.php"}'})
            events = []
            agent = Agent(model, LocalTools(project, allow_write=True), max_steps=5,
                          on_event=events.append, tool_protocol="strict-json")
            self.assertEqual(agent.run("make a comment"), "Changed routes/web.php")
            self.assertEqual((project / "routes/web.php").read_text(), "<?php\n// test\n")
            ends = [e for e in events if e["event"] == "tool_end"]
            self.assertEqual([(e["tool"], e["status"]) for e in ends],
                             [("read_file", "ok"), ("write_file", "ok")])
            self.assertTrue(all(not tools for _, tools in model.requests))
            self.assertEqual(model.requests[1][0][-1]["role"], "user")

    def test_strict_json_read_only_denies_write_and_exec(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            events = []
            model = SequenceModel(action("write_file", path="new.php", content="unsafe"),
                                  action("run_command", argv=["php", "artisan", "test"]),
                                  {"content": '{"type":"final","content":"Tools denied"}'})
            agent = Agent(model, LocalTools(project), max_steps=3,
                          on_event=events.append, tool_protocol="strict-json")
            self.assertEqual(agent.run("test"), "Tools denied")
            self.assertFalse((project / "new.php").exists())
            ends = [e for e in events if e["event"] == "tool_end"]
            self.assertEqual([e["reason"] for e in ends], ["permission", "permission"])

    def test_strict_json_exact_argv_allowlist_cannot_be_bypassed(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)
            events = []
            model = SequenceModel(action("run_command", argv=["php", "artisan", "migrate:fresh"]),
                                  {"content": '{"type":"final","content":"Denied"}'})
            Agent(model, LocalTools(project, allow_exec=True, exec_commands=[["php", "artisan", "test"]]),
                  max_steps=2, on_event=events.append, tool_protocol="strict-json").run("run it")
            self.assertEqual([e["reason"] for e in events if e["event"] == "tool_end"], ["permission"])

    def test_strict_json_retry_only_twice_and_no_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            model = SequenceModel({"content": '```json\n{"type":"tool","name":"read_file","arguments":{"path":"x"}}\n```'},
                                  {"content": 'I read file'})
            events = []
            with self.assertRaisesRegex(ProtocolError, "model_failed_strict_json"):
                Agent(model, LocalTools(Path(d), allow_write=True), max_steps=7,
                      on_event=events.append, tool_protocol="strict-json").run("inspect")
            self.assertEqual(len(model.requests), 2)
            self.assertFalse(any(e["event"] == "tool_start" for e in events))
            self.assertEqual(len([e for e in events if e["event"] == "protocol_error"]), 2)

    def test_native_fenced_json_is_never_executed(self):
        with tempfile.TemporaryDirectory() as d:
            text = '```json\n{"name":"write_file","arguments":{"path":"unsafe","content":"x"}}\n```'
            model = SequenceModel({"content": text})
            events = []
            result = Agent(model, LocalTools(Path(d), allow_write=True),
                           on_event=events.append).run("test")
            self.assertEqual(result, text)
            self.assertFalse((Path(d) / "unsafe").exists())
            self.assertFalse(any(e["event"] == "tool_end" for e in events))
            self.assertTrue(any(e["event"] == "model_end" and e["tool_calls"] == 0 for e in events))

    def test_native_unknown_name_is_not_executed(self):
        with tempfile.TemporaryDirectory() as d:
            model = SequenceModel({"tool_calls": [{"function": {"name": "invented", "arguments": "{}"}}]},
                                  {"content": "Unavailable"})
            events = []
            result = Agent(model, LocalTools(Path(d)), on_event=events.append).run("inspect")
            self.assertEqual(result, "Unavailable")
            self.assertEqual([e["reason"] for e in events if e["event"] == "tool_end"], ["unknown_tool"])
            self.assertNotIn("invented", json.dumps(events))

    def test_no_tool_start_on_mixed_valid_and_invalid_native_batch(self):
        with tempfile.TemporaryDirectory() as d:
            model = SequenceModel({"tool_calls": [{"function": {"name": "write_file", "arguments": {"path":"a","content":"x"}}},
                                                   {"function": {"name":"read_file", "arguments": {"path":{"type":"string"}}}}]})
            events = []
            with self.assertRaises(ProtocolError):
                Agent(model, LocalTools(Path(d), allow_write=True), on_event=events.append).run("test")
            self.assertFalse((Path(d) / "a").exists())
            self.assertFalse(any(e["event"] == "tool_start" for e in events))


if __name__ == "__main__":
    unittest.main()
