"""Private process adapter. No shell, inherited server flags or raw logs."""
import errno
import os
import subprocess
from pathlib import Path

from .errors import RuntimeFailure


class WindowsOwned:
    def __init__(self, process, job):
        self.process, self.job = process, job

    def poll(self):
        return self.process.poll()

    def stop(self, grace):
        self.job.terminate(grace)
        try:
            self.process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            raise RuntimeFailure('cleanup_failed', stage='job_wait') from None
        self.job.close()


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
    return spawn_owned(argv, str(executable.parent), child_environment(executable, key))


def spawn_owned(argv, cwd, env):
    """Launch a trusted argv under platform ownership; no project-controlled shell."""
    try:
        if os.name != "nt":
            from .posix_supervisor import spawn_posix
            return spawn_posix(argv, cwd, env)
        from .windows_job import WindowsJob
        job = WindowsJob()
        try:
            process = subprocess.Popen(
                argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False,
                close_fds=True, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        except BaseException:
            job.close()
            raise
        try:
            job.attach(process)
        except BaseException:
            # Do not proceed without ownership. Only the exact launched handle.
            try:
                if process.poll() is None:
                    process.kill()
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                raise RuntimeFailure("cleanup_failed", stage="job_assign") from None
            finally:
                job.close()
            raise
        return WindowsOwned(process, job)
    except OSError as exc:
        code = getattr(exc, "winerror", None) or exc.errno
        loader = (exc.errno == errno.ENOEXEC or getattr(exc, "winerror", None) in (126, 193, 216))
        raise RuntimeFailure("native_loader" if loader else "process_spawn",
                             stage="loader" if loader else "spawn", os_code=code) from None
    except ValueError:
        raise RuntimeFailure("process_spawn", stage="spawn") from None


def terminate_owned(process, grace=2.0):
    """Stop only the owned job or supervised POSIX process group."""
    process.stop(grace)
