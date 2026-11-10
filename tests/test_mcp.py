import json
import sys
import tempfile
import unittest
from pathlib import Path

from tinybuilder.mcp import MCPBridge

SERVER = r'''
import json, sys
for line in sys.stdin:
    req = json.loads(line)
    if "id" not in req: continue
    method = req.get("method")
    if method == "initialize":
        result = {"protocolVersion":"2025-06-18", "capabilities":{"tools":{}}, "serverInfo":{"name":"fake", "version":"1"}}
    elif method == "tools/list":
        result = {"tools":[{"name":"ping", "description":"test", "inputSchema":{"type":"object","properties":{"word":{"type":"string"}}}}]}
    elif method == "tools/call":
        result = {"content":[{"type":"text", "text":"pong:"+req["params"]["arguments"].get("word", "")}], "isError": False}
    else:
        result = {}
    print(json.dumps({"jsonrpc":"2.0", "id":req["id"], "result":result}), flush=True)
'''


class TestMCP(unittest.TestCase):
    def test_stdio_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "fake_server.py").write_text(SERVER)
            config = root / "mcp.json"
            config.write_text(json.dumps({"mcpServers": {"fake": {
                "command": sys.executable, "args": ["fake_server.py"]}}}))
            bridge = MCPBridge(root, config)
            try:
                self.assertEqual(bridge.specs[0]["function"]["name"], "mcp_fake__ping")
                self.assertEqual(bridge.call("mcp_fake__ping", {"word": "hello"}), "pong:hello")
            finally:
                bridge.close()
