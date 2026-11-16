"""MCP error paths must not leak remote text or leave subprocesses running.

These tests use a local scripted fake MCP server, never real Laravel or Ollama.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tinybuilder.mcp import MCPBridge, MCPError


SERVER = '''import json, sys
mode = sys.argv[1]
for line in sys.stdin:
    request = json.loads(line)
    if 'id' not in request:
        continue
    method = request['method']
    if (mode == 'initialize' or
            mode == 'list' and method == 'tools/list' or
            mode == 'call' and method == 'tools/call'):
        response = {'jsonrpc': '2.0', 'id': request['id'],
                    'error': {'code': -32000, 'message': 'PRIVATE-MCP-ERROR-BODY'}}
    elif method == 'tools/list':
        response = {'jsonrpc': '2.0', 'id': request['id'],
                    'result': {'tools': [{'name': 'sample',
                                         'inputSchema': {'type': 'object', 'properties': {}}}]}}
    elif method == 'tools/call':
        response = {'jsonrpc': '2.0', 'id': request['id'], 'result': {'content': []}}
    else:
        response = {'jsonrpc': '2.0', 'id': request['id'], 'result': {'capabilities': {}}}
    print(json.dumps(response), flush=True)
'''


class TestPrivateMcpErrors(unittest.TestCase):
    def fixture(self, root, mode):
        (root / 'fake.py').write_text(SERVER, encoding='utf-8')
        config = root / 'mcp.json'
        config.write_text(json.dumps({
            'mcpServers': {'local': {'command': sys.executable, 'args': ['fake.py', mode]}}
        }), encoding='utf-8')
        return config

    def test_initialize_failure_sanitized_and_child_terminated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self.fixture(root, 'initialize')
            spawned = []
            actual_popen = subprocess.Popen

            def capture_spawn(*args, **kwargs):
                process = actual_popen(*args, **kwargs)
                spawned.append(process)
                return process

            try:
                with patch('tinybuilder.mcp.subprocess.Popen', side_effect=capture_spawn):
                    with self.assertRaises(MCPError) as error:
                        MCPBridge(root, config)
                self.assertNotIn('PRIVATE-MCP-ERROR-BODY', str(error.exception))
                self.assertEqual(len(spawned), 1)
                self.assertIsNotNone(spawned[0].poll(),
                                     'Failed MCP initialization must terminate its child')
            finally:
                for process in spawned:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=3)

    def test_tools_list_error_does_not_echo_remote_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(MCPError) as error:
                MCPBridge(root, self.fixture(root, 'list'))
            self.assertNotIn('PRIVATE-MCP-ERROR-BODY', str(error.exception))

    def test_tool_call_rpc_error_does_not_echo_remote_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bridge = MCPBridge(root, self.fixture(root, 'call'))
            try:
                with self.assertRaises(MCPError) as error:
                    bridge.call('mcp_local__sample', {})
                self.assertNotIn('PRIVATE-MCP-ERROR-BODY', str(error.exception))
            finally:
                bridge.close()


if __name__ == '__main__':
    unittest.main()
