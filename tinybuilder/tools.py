"""Constrained local project tools. Write and execution require explicit CLI flags."""

import json
import os
import subprocess
from pathlib import Path
from typing import Any

EXCLUDED = {".git", ".venv", "node_modules", "vendor", "__pycache__", ".next", ".idea"}
MAX_OBSERVATION = 16000


def tool(name: str, description: str, properties: dict, required: list[str]) -> dict[str, Any]:
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required,
                           "additionalProperties": False}}}


SPECS = [
    tool("list_files", "List relevant files under the project root (excluding vendor and build directories).",
         {"path": {"type": "string", "description": "Subdirectory relative to project root; use '.' for root"}}, ["path"]),
    tool("read_file", "Read a UTF-8 project source file (up to 16 KB).",
         {"path": {"type": "string"}}, ["path"]),
    tool("search_files", "Search project source files for a literal string.",
         {"query": {"type": "string"}}, ["query"]),
    tool("write_file", "Replace or create a UTF-8 project file. Requires --allow-write.",
         {"path": {"type": "string"}, "content": {"type": "string"}}, ["path", "content"]),
    tool("run_command", "Run a project command as argv without a shell. Requires --allow-exec.",
         {"argv": {"type": "array", "items": {"type": "string"}}}, ["argv"]),
]


class LocalTools:
    def __init__(self, root: Path, allow_write: bool = False, allow_exec: bool = False):
        self.root = Path(root).resolve(strict=True)
        self.allow_write = allow_write
        self.allow_exec = allow_exec

    def _path(self, relative: str) -> Path:
        if not isinstance(relative, str) or not relative.strip():
            raise ValueError("Non-empty relative path required")
        p = (self.root / relative).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError("Path is outside project root")
        return p

    def call(self, name: str, args: dict[str, Any]) -> str:
        try:
            if name == "list_files":
                root = self._path(args["path"])
                if not root.is_dir():
                    return "Directory not found"
                paths = []
                for current, directories, files in os.walk(root):
                    directories[:] = sorted(d for d in directories if d not in EXCLUDED
                                            and (Path(current) / d).resolve().is_relative_to(self.root))
                    for item in sorted(files):
                        p = Path(current) / item
                        if p.is_symlink() or not p.resolve().is_relative_to(self.root):
                            continue
                        paths.append(str(p.relative_to(self.root)))
                        if len(paths) == 150:
                            return "\n".join(paths) + "\n... truncated"
                return "\n".join(paths) or "(empty)"
            if name == "read_file":
                p = self._path(args["path"])
                if not p.is_file():
                    return "File not found"
                with p.open("rb") as f:
                    data = f.read(MAX_OBSERVATION + 1)
                return data[:MAX_OBSERVATION].decode("utf-8", "replace") + ("\n... truncated" if len(data) > MAX_OBSERVATION else "")
            if name == "search_files":
                query = args["query"]
                if not isinstance(query, str) or not query or len(query) > 200:
                    return "Invalid query"
                matches = []
                for current, directories, files in os.walk(self.root):
                    directories[:] = sorted(d for d in directories if d not in EXCLUDED and
                                            (Path(current) / d).resolve().is_relative_to(self.root))
                    for file in sorted(files):
                        p = Path(current) / file
                        if p.is_symlink() or not p.resolve().is_relative_to(self.root) or p.stat().st_size > 1_000_000:
                            continue
                        try:
                            with p.open(encoding="utf-8") as handle:
                                for idx, line in enumerate(handle, 1):
                                    if query in line:
                                        matches.append(f"{p.relative_to(self.root)}:{idx}: {line.strip()[:200]}")
                                        if len(matches) >= 30:
                                            return "\n".join(matches) + "\n... truncated"
                        except (UnicodeError, OSError):
                            continue
                return "\n".join(matches) or "No matches"
            if name == "write_file":
                if not self.allow_write:
                    return "Permission denied: start with --allow-write to permit file changes"
                p = self._path(args["path"])
                if p == self.root:
                    return "Cannot overwrite project root"
                content = args["content"]
                if not isinstance(content, str) or len(content.encode("utf-8")) > 250_000:
                    return "Invalid or oversized content (250 KB limit)"
                p.parent.mkdir(parents=True, exist_ok=True)
                # Revalidate after mkdir; refuse symlink escapes.
                p = self._path(args["path"])
                p.write_text(content, encoding="utf-8")
                return f"Wrote {p.relative_to(self.root)} ({len(content.encode('utf-8'))} bytes)"
            if name == "run_command":
                if not self.allow_exec:
                    return "Permission denied: start with --allow-exec to permit commands"
                argv = args["argv"]
                if not isinstance(argv, list) or not argv or len(argv) > 25 or not all(isinstance(a, str) and a for a in argv):
                    return "Invalid argv"
                # This is not a sandbox: --allow-exec grants local command execution.
                result = subprocess.run(argv, cwd=self.root, shell=False, capture_output=True,
                                        text=True, timeout=60, errors="replace", stdin=subprocess.DEVNULL)
                output = result.stdout + ("\n" + result.stderr if result.stderr else "")
                return f"Exit code: {result.returncode}\n{output[:MAX_OBSERVATION]}"
            return "Unknown tool: " + name
        except (KeyError, OSError, ValueError, subprocess.TimeoutExpired, TypeError) as exc:
            return f"Tool error: {type(exc).__name__}: {exc}"
