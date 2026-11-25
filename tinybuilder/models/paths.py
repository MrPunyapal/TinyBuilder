"""Native model data directories, without creating directories on inspection."""
import os
from pathlib import Path
import sys


def native_model_dir(*, platform=None, environ=None, home=None) -> Path:
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)

    def absolute_env(key, fallback):
        value = environ.get(key)
        return Path(value) if value and Path(value).is_absolute() else fallback

    if platform == "win32":
        return absolute_env("LOCALAPPDATA", home / "AppData" / "Local") / "TinyBuilder" / "models"
    if platform == "darwin":
        return home / "Library" / "Application Support" / "TinyBuilder" / "models"
    return absolute_env("XDG_DATA_HOME", home / ".local" / "share") / "tinybuilder" / "models"
