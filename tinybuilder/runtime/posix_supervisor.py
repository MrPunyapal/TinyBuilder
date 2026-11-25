"""POSIX parent-pipe supervisor; uses the system shell, not installed Python.

The shell is a new session/group leader. The constant script receives argv
positionally; no caller/model data is evaluated as shell syntax. The native
server has no parent-pipe or diagnostic-pipe access.
"""
import os
import subprocess

from .errors import RuntimeFailure


_SCRIPT = r'''
cleanup() {
    trap '' TERM INT HUP USR1
    kill -TERM 0
    /bin/sleep 1
    kill -KILL 0
}
trap cleanup TERM INT HUP USR1
(
    "$@" </dev/null >/dev/null 2>/dev/null
    code=$?
    printf '%s\n' "$code"
    kill -USR1 "$$"
) </dev/null &
# A private pipe is held open only by the application. EOF (including an
# unexpected parent exit) triggers cleanup while this group still has a leader.
IFS= read -r ignored || :
cleanup
'''


class PosixOwned:
    def __init__(self, process):
        self.process = process
        self._exit = None

    def poll(self):
        code = self.process.poll()
        if code is None:
            return None
        if self._exit is None:
            # Only a numeric shell status is ever written by the wrapper.
            # Nonblocking: never hang on a pipe even if a child misbehaves.
            try:
                os.set_blocking(self.process.stdout.fileno(), False)
                data = os.read(self.process.stdout.fileno(), 32).strip()
                value = int(data) if data.isdigit() else code
                self._exit = value if 0 <= value <= 255 else code
            except (OSError, ValueError):
                self._exit = code
        return self._exit

    def stop(self, grace):
        if not self.process.stdin.closed:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=max(2.0, grace + 1.5))
        except subprocess.TimeoutExpired:
            # Retain the handle for retry rather than signaling a recycled
            # process group from outside the supervisor.
            raise RuntimeFailure("cleanup_failed", stage="supervisor_wait") from None
        self.poll()
        self.process.stdout.close()


def spawn_posix(argv, cwd, env):
    process = subprocess.Popen(
        ["/bin/sh", "-c", _SCRIPT, "tinybuilder-runtime", *argv],
        cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True, shell=False)
    return PosixOwned(process)
