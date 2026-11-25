"""Reject links which cannot survive relocating the frozen macOS directory."""
import os
import sys
from pathlib import Path


def verify_links(root):
    root = root.resolve(strict=True)
    for path in root.rglob("*"):
        if path.is_symlink():
            if Path(os.readlink(path)).is_absolute():
                raise ValueError(f"absolute bundle symlink: {path.relative_to(root)}")
            if not path.resolve(strict=True).is_relative_to(root):
                raise ValueError(f"escaping bundle symlink: {path.relative_to(root)}")


if __name__ == "__main__":
    verify_links(Path(sys.argv[1]))
