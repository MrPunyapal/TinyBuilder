"""Restore external program library search paths for frozen Linux only."""
import os
import sys


def external_env():
    if not getattr(sys, "frozen", False) or not sys.platform.startswith("linux"):
        return {}
    env = os.environ.copy()
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
    else:
        env.pop("LD_LIBRARY_PATH", None)
    return {"env": env}
