"""Private process adapter. No shell, inherited server flags or raw logs."""
import errno
import os
import signal
import subprocess
from pathlib import Path

from .errors import RuntimeFailure


def child_environment(executable: Path, key: str) -> dict[str, str]:
    # Do not inherit LLAMA_*, LD_*, DYLD_*, PYTHON*, proxy or project variables.
    if os.pathsep in str(executable.parent):
        raise RuntimeFailure("runtime_missing")
    env = {"LLAMA_API_KEY": key}
    if os.name == "nt":
        # Windows needs SystemRoot; do not trust the caller's PATH.
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        size = ctypes.windll.kernel32.GetWindowsDirectoryW(buffer, len(buffer))
        if not 0 < size < len(buffer):
            raise RuntimeFailure("native_loader")
        system = buffer.value
        env.update(SystemRoot=system, WINDIR=system,
                   PATH=str(executable.parent) + os.pathsep + str(Path(system) / "System32"))
    else:
        env["PATH"] = "/usr/bin:/bin"
        if os.uname().sysname == "Linux":
            env["LD_LIBRARY_PATH"] = str(executable.parent)
        # macOS payload must have correct @loader_path/@rpath at build time.
    return env


def spawn(executable, model, port, alias, key):
    argv = [str(executable), "--model", str(model), "--host", "127.0.0.1",
            "--port", str(port), "--alias", alias, "--device", "none",
            "--n-gpu-layers", "0", "--no-webui", "--no-slots", "--jinja",
            "--log-disable"]
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {
        "start_new_session": True}
    try:
        return subprocess.Popen(
            argv, cwd=str(executable.parent), env=child_environment(executable, key),
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, shell=False, **options)
    except OSError as exc:
        # Only known executable-format/dependency errors are classified as
        # loader errors; ENOENT can mean missing executable, cwd or interpreter.
        kind = "native_loader" if (exc.errno == errno.ENOEXEC or
                                   getattr(exc, "winerror", None) in (126, 193, 216)) else "process_spawn"
        raise RuntimeFailure(kind) from None
    except ValueError:
        raise RuntimeFailure("process_spawn") from None


def terminate_owned(process, grace=2.0):
    """Bounded direct-child cleanup. POSIX signals its owned process group."""
    if process.poll() is not None:
        return
    try:
        if os.name == "nt":
            process.terminate()
        else:
            os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=grace)
    except ProcessLookupError:
        pass
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=grace)
        except (OSError, subprocess.TimeoutExpired):
            raise RuntimeFailure("cleanup_failed") from None
    except OSError:
        raise RuntimeFailure("cleanup_failed") from None
    if process.poll() is None:
        raise RuntimeFailure("cleanup_failed")
