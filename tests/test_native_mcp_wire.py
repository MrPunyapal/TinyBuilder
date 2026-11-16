"""Deterministic native/MCP wire regression tests; scripted subprocess, no Ollama."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from tinybuilder.agent import Agent
from tinybuilder.mcp import MCPBridge, MCPError
from tinybuilder.protocol import ProtocolError
from tinybuilder.tools import LocalTools


SERVER = r'''import json, sys
mode = sys.argv[1]
for line in sys.stdin:
    request = json.loads(line)
    if "id" not in request: continue
    method = request["method"]
    if method == "initialize":
        result = {"protocolVersion":"2025-06-18", "capabilities":{"tools":{}}}
    elif method == "tools/list":
        schema = ({"type":"array"} if mode == "bad_schema"
                  else {"type":"object","properties":{"word":{"type":"string"}}})
        if mode == "invalid_name":
            result = {"tools":[{"name":42,"inputSchema":schema}]}
        elif mode == "too_many":
            result = {"tools":[{"name":"item"+str(i),"inputSchema":schema}
                               for i in range(129)]}
        else:
            result = {"tools":[{"name":"echo","inputSchema":schema,
                                "description":"Read-only echo tool"}]}
    elif method == "tools/call":
        result = {"content":[{"type":"text",
                              "text":"private-reply:" + request["params"]["arguments"].get("word", "")}]}
    else:
        result = {}
    print(json.dumps({"jsonrpc":"2.0","id":request["id"],"result":result}), flush=True)
'''


class NativeModel:
    def __init__(self, bad_batch=False):
        self.requests = []
        self.bad_batch = bad_batch

    def complete(self, messages, tools, **kwargs):
        self.requests.append((list(messages), list(tools)))
        if len(self.requests) == 1:
            calls = [{"id":"echo-1","type":"function",
                      "function":{"name":"mcp_safe__echo","arguments":{"word":"hello"}}}]
            if self.bad_batch:
                calls.append({"id":"invalid-local","type":"function",
                              "function":{"name":"read_file",
                                          "arguments":{"path":{"type":"string"}}}})
            return {"role":"assistant","content":None,"tool_calls":calls}
        return {"role":"assistant","content":"Done"}


class NativeMcpWireTests(unittest.TestCase):
    def bridge(self, root, mode="ok"):
        (root / "fake_mcp.py").write_text(SERVER)
        config = root / "servers.json"
        config.write_text(json.dumps({"mcpServers":{"safe":{"command":sys.executable,
                                                   "args":["fake_mcp.py",mode]}}}))
        return MCPBridge(root, config)

    def test_real_stdio_roundtrip_with_scripted_native_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bridge = self.bridge(root)
            model = NativeModel()
            events = []
            try:
                answer = Agent(model, LocalTools(root), mcp=bridge,
                               on_event=events.append).run("Call echo")
                self.assertEqual(answer, "Done")
                advertised = [t["function"]["name"] for t in model.requests[0][1]]
                self.assertIn("mcp_safe__echo", advertised)
                self.assertIn("mcp_safe__echo", model.requests[0][0][0]["content"])
                self.assertEqual(model.requests[1][0][-1]["role"], "tool")
                self.assertIn("private-reply:hello", model.requests[1][0][-1]["content"])
                self.assertEqual([(x["tool"],x["status"]) for x in events
                                  if x["event"]=="tool_end"], [("mcp_safe__echo","ok")])
                self.assertNotIn("private-reply", json.dumps(events))
            finally:
                bridge.close()

    def test_invalid_native_batch_executes_no_mcp_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bridge = self.bridge(root)
            events = []
            try:
                with self.assertRaises(ProtocolError):
                    Agent(NativeModel(bad_batch=True), LocalTools(root), mcp=bridge,
                          on_event=events.append).run("Call echo")
                self.assertFalse(any(x["event"]=="tool_start" for x in events))
            finally:
                bridge.close()

    def test_malformed_server_tool_catalog_rejected_before_model(self):
        for mode in ("bad_schema", "invalid_name", "too_many"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "fake_mcp.py").write_text(SERVER)
                config = root / "servers.json"
                config.write_text(json.dumps({"mcpServers":{"safe":{"command":sys.executable,
                                                       "args":["fake_mcp.py",mode]}}}))
                with self.assertRaises(MCPError):
                    MCPBridge(root, config)


if __name__ == "__main__":
    unittest.main()
