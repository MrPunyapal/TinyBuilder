"""Small MCP stdio client: JSON-RPC over newline-delimited UTF-8 messages."""

import json
import queue
import re
import subprocess
import threading
from pathlib import Path
from typing import Any


class MCPError(RuntimeError):
    pass


class MCPServer:
    def __init__(self, name: str, command: str, args: list[str], cwd: Path, timeout: int = 25):
        self.name = name
        self.timeout = timeout
        self.proc = subprocess.Popen([command, *args], cwd=cwd, text=True, encoding="utf-8",
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, bufsize=1)
        self.pending: queue.Queue[str | None] = queue.Queue()
        self.counter = 0
        threading.Thread(target=self._reader, daemon=True).start()
        self._request("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "tinybuilder", "version": "0.1.0"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _reader(self):
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            self.pending.put(line)
        self.pending.put(None)

    def _send(self, data: dict):
        assert self.proc.stdin is not None
        self.proc.stdin.write(json.dumps(data, separators=(",", ":")) + "\n")
        self.proc.stdin.flush()

    def _request(self, method: str, params: dict) -> Any:
        self.counter += 1
        ident = self.counter
        self._send({"jsonrpc": "2.0", "id": ident, "method": method, "params": params})
        # Bounded number of asynchronous notifications/diagnostics while waiting.
        for _ in range(200):
            try:
                line = self.pending.get(timeout=self.timeout)
            except queue.Empty as exc:
                raise MCPError(f"MCP {self.name}: timeout waiting for {method}") from exc
            if line is None:
                raise MCPError(f"MCP {self.name}: server exited")
            try:
                response = json.loads(line)
            except ValueError:
                continue
            if response.get("id") != ident:
                continue
            if "error" in response:
                raise MCPError(f"MCP {self.name}: {response['error']}")
            return response.get("result", {})
        raise MCPError(f"MCP {self.name}: too many unsolicited messages")

    def tools(self) -> list[dict]:
        return self._request("tools/list", {}).get("tools", [])

    def call(self, name: str, arguments: dict) -> str:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        parts = result.get("content", [])
        chunks = [str(p.get("text", "")) for p in parts if isinstance(p, dict) and p.get("type") == "text"]
        output = "\n".join(chunks) or json.dumps(result, ensure_ascii=False)
        return output[:16000] + ("\n... truncated" if len(output) > 16000 else "")

    def close(self):
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        if self.proc.stdin is not None:
            self.proc.stdin.close()
        if self.proc.stdout is not None:
            self.proc.stdout.close()


class MCPBridge:
    def __init__(self, root: Path, config_path: Path):
        self.servers: list[MCPServer] = []
        self.specs: list[dict] = []
        self.names: dict[str, tuple[MCPServer, str]] = {}
        data = json.loads(config_path.read_text(encoding="utf-8"))
        try:
            for server_name, spec in data.get("mcpServers", {}).items():
                if not isinstance(spec, dict) or not isinstance(spec.get("command"), str):
                    raise MCPError(f"Invalid MCP server config: {server_name}")
                server = MCPServer(server_name, spec["command"], spec.get("args", []), root)
                self.servers.append(server)
                for item in server.tools():
                    original = item["name"]
                    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", f"mcp_{server_name}__{original}")[:64]
                    if clean in self.names:
                        raise MCPError(f"Duplicate MCP tool name: {clean}")
                    self.names[clean] = (server, original)
                    self.specs.append({"type": "function", "function": {
                        "name": clean,
                        "description": (item.get("description") or f"MCP {server_name}: {original}")[:800],
                        "parameters": item.get("inputSchema") or {"type": "object", "properties": {}}
                    }})
        except Exception:
            self.close()
            raise

    def call(self, name: str, arguments: dict) -> str:
        server, original = self.names[name]
        return server.call(original, arguments)

    def close(self):
        for server in self.servers:
            server.close()
