"""Opt-in application tool gate; existing CLI tools are unchanged."""
from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
from threading import Event
from typing import Callable

from ..tools import LocalTools
from .session import Permissions

MAX_FILE = 250_000
MAX_PREVIEW = 24_000


@dataclass(frozen=True)
class Approval:
    tool: str
    path: str | None = None
    diff: str | None = None
    argv: tuple[str, ...] = ()


class ApprovedTools(LocalTools):
    """Run only permitted, separately approved mutations.

    The worker calls approve synchronously. A frontend must marshal that
    request to its UI thread and unblock on cancellation; only literal True
    approves. Render path, argv and diff as untrusted plain text, not markup.
    This adds an operator gate, not filesystem or process sandboxing.
    """

    def __init__(self, root: Path, permissions: Permissions, cancel: Event,
                 approve: Callable[[Approval], bool]):
        super().__init__(root, **permissions.tool_options())
        self._permissions = permissions
        self._cancel = cancel
        self._approve = approve

    @staticmethod
    def _before(path):
        if not path.exists():
            return None
        with path.open("rb") as source:
            data = source.read(MAX_FILE + 1)
        if len(data) > MAX_FILE:
            raise ValueError("File too large to preview")
        return data

    def _write(self, args):
        if not self._permissions.allow_write:
            return "Permission denied: writes require explicit task permission"
        name, content = args["path"], args["content"]
        if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_FILE:
            return "Invalid or oversized replacement"
        path = self._path(name)
        if path == self.root or (path.exists() and not path.is_file()):
            return "Permission denied: choose a regular project file"
        before = self._before(path)
        old = (before or b"").decode("utf-8")
        # keepends=False makes line endings visible through explicit repr;
        # this also prevents terminal escapes from the source text.
        def lines(value):
            return [repr(line) + "\n" for line in value.splitlines(keepends=True)]
        diff = "".join(unified_diff(lines(old), lines(content),
                                    fromfile="before", tofile="after"))
        if len(diff) > MAX_PREVIEW:
            return "Permission denied: change too large for complete preview"
        relative = str(path.relative_to(self.root))
        request = Approval("write_file", path=relative,
                           diff=diff or "(no text differences)")
        if self._cancel.is_set() or self._approve(request) is not True or self._cancel.is_set():
            return "Permission denied: write not approved or cancelled"
        # Reject changes made while the approval was being displayed.
        # LocalTools revalidates the project path. This is not atomic against
        # a hostile process racing filesystem operations.
        if self._path(name) != path or self._before(path) != before:
            return "Permission denied: file changed; request a fresh preview"
        if self._cancel.is_set():
            return "Permission denied: operation cancelled"
        return super().call("write_file", {"path": relative, "content": content})

    def _command(self, args):
        argv = args["argv"]
        if (not isinstance(argv, list) or tuple(argv) not in self._permissions.exec_commands):
            return "Permission denied: command is not in the exact argv allowlist"
        request = Approval("run_command", argv=tuple(argv))
        if self._cancel.is_set() or self._approve(request) is not True or self._cancel.is_set():
            return "Permission denied: command not approved or cancelled"
        return super().call("run_command", {"argv": list(request.argv)})

    def call(self, name, args):
        if self._cancel.is_set():
            return "Permission denied: operation cancelled"
        try:
            if name == "write_file":
                return self._write(args)
            if name == "run_command":
                return self._command(args)
            return super().call(name, args)
        except Exception:
            # Never reflect approval callback or preview exceptions to model.
            return "Tool failed: approval or preview unavailable"
