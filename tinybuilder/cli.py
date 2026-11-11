"""User-facing CLI for local agent, diagnostics, and explicit preference storage."""

import argparse
import json
import os
import sys
from pathlib import Path

from .agent import Agent
from .context import project_summary
from .memory import MemoryStore
from .model import ChatModel, ModelError
from .mcp import MCPBridge, MCPError
from .tools import LocalTools


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tinybuilder", description="Experimental tiny, local-first coding agent")
    sub = p.add_subparsers(dest="command", required=True)
    chat = sub.add_parser("chat", help="Run a single coding task through a local model")
    chat.add_argument("task", help="Coding request, quoted as one argument")
    chat.add_argument("--project", default=".", help="Project directory")
    chat.add_argument("--base-url", default="http://127.0.0.1:11434/v1", help="OpenAI-compatible base URL")
    chat.add_argument("--model", default="qwen2.5-coder:0.5b")
    chat.add_argument("--api-key", default=None, help="Prefer TINYBUILDER_API_KEY environment variable")
    chat.add_argument("--mcp-config", default=None, help="Path to MCP servers JSON config")
    chat.add_argument("--allow-write", action="store_true", help="Permit modifying project files")
    chat.add_argument("--allow-exec", action="store_true", help="Permit arbitrary local argv commands (NOT sandboxed)")
    chat.add_argument("--exec-command", action="append", default=None, metavar="JSON_ARGV",
                      help="Restrict --allow-exec to exact argv; repeat for multiple commands")
    chat.add_argument("--verbose", action="store_true", help="Emit sanitized events on stderr")
    chat.add_argument("--tool-protocol", choices=("native", "strict-json"), default="native",
                      help="native OpenAI tool calls (default), or experimental opt-in strict JSON actions")
    chat.add_argument("--max-steps", type=int, default=8)
    chat.add_argument("--memory-db", default="~/.tinybuilder/memory.sqlite")

    doctor = sub.add_parser("doctor", help="Inspect project and optional MCP configuration")
    doctor.add_argument("--project", default=".")
    doctor.add_argument("--mcp-config", default=None)

    mem = sub.add_parser("memory", help="Explicit user-owned preferences and project decisions")
    mem.add_argument("action", choices=("set", "get", "list", "delete"))
    mem.add_argument("key", nargs="?")
    mem.add_argument("value", nargs="?")
    mem.add_argument("--project", default=".")
    mem.add_argument("--memory-db", default="~/.tinybuilder/memory.sqlite")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print(f"Not a directory: {project}", file=sys.stderr)
        return 2
    if args.command == "doctor":
        print(project_summary(project))
        print("Laravel Boost MCP: " + ("likely installed" if (project / "vendor/laravel/boost").exists() else "not detected"))
        if args.mcp_config:
            print("MCP config: " + ("found" if Path(args.mcp_config).is_file() else "missing"))
        return 0
    if args.command == "memory":
        store = MemoryStore(Path(args.memory_db))
        scope = str(project)
        if args.action in ("set", "get", "delete") and not args.key:
            print("A key is required", file=sys.stderr)
            return 2
        if args.action == "set":
            if args.value is None:
                print("A value is required", file=sys.stderr)
                return 2
            store.set(scope, args.key, args.value)
            print("Saved explicit user preference/project decision")
        elif args.action == "get":
            print(store.get(scope, args.key) or "(not found)")
        elif args.action == "delete":
            store.delete(scope, args.key)
            print("Deleted")
        else:
            for key, value in store.all(scope).items():
                print(f"{key}: {value}")
        return 0
    if args.tool_protocol == "strict-json" and args.mcp_config:
        print("Error: --tool-protocol strict-json supports local tools only; omit --mcp-config or use native", file=sys.stderr)
        return 2
    if args.max_steps < 1 or args.max_steps > 50:
        print("--max-steps must be between 1 and 50", file=sys.stderr)
        return 2
    try:
        commands = [json.loads(command) for command in args.exec_command] if args.exec_command else None
        if commands is not None and (not args.allow_exec or any(
                not isinstance(command, list) or not command or len(command) > 25 or
                not all(isinstance(part, str) and part for part in command) for command in commands)):
            raise ValueError("--exec-command requires --allow-exec and non-empty JSON argv arrays")
    except (ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    store = MemoryStore(Path(args.memory_db))
    local = LocalTools(project, allow_write=args.allow_write, allow_exec=args.allow_exec,
                       exec_commands=commands)
    model = ChatModel(args.base_url, args.model,
                      api_key=args.api_key if args.api_key is not None else os.environ.get("TINYBUILDER_API_KEY", ""))
    bridge = None
    try:
        if args.mcp_config:
            bridge = MCPBridge(project, Path(args.mcp_config).expanduser().resolve())
            print(f"Connected MCP tools: {len(bridge.specs)}", file=sys.stderr)
        def event(data):
            print(json.dumps(data), file=sys.stderr, flush=True)
        agent = Agent(model, local, bridge, store.all(str(project)), args.max_steps,
                      on_event=event if args.verbose else None, tool_protocol=args.tool_protocol)
        print(agent.run(args.task))
        return 0
    except (ModelError, MCPError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if bridge:
            bridge.close()


if __name__ == "__main__":
    raise SystemExit(main())
