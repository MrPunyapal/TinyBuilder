"""Installation-relative runtime discovery; never search the project or PATH."""
import sys
from pathlib import Path


def runtime_root(explicit=None):
    if explicit is not None:
        candidate = Path(explicit).expanduser()
        if not candidate.is_absolute():
            raise ValueError("Supply an absolute trusted runtime directory")
    elif getattr(sys, "frozen", False):
        executable = Path(sys.executable).resolve(strict=True)
        # Linux <bundle>/app/tinybuilder; macOS <stage>/tinybuilder/tinybuilder;
        # Windows <install>/TinyBuilder.exe.
        candidate = (executable.parent if sys.platform == "win32"
                     else executable.parent.parent) / "runtime"
    else:
        raise ValueError("Source launch requires --runtime-root ABSOLUTE_DIRECTORY")
    candidate = candidate.resolve(strict=True)
    if not candidate.is_dir() or not (candidate / "runtime-manifest.json").is_file():
        raise ValueError("Trusted runtime directory or manifest missing")
    return candidate
