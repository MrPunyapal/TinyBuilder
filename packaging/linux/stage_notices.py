"""Require reviewed redistribution notices for every bundled regular ELF file."""
import json
import re
import shutil
import sys
from pathlib import Path


REQUIRED = {"CPython.txt", "PyInstaller.txt", "llama.cpp.txt"}


def stage(bundle: Path, source: Path) -> None:
    entries = list(source.iterdir())
    if any(p.is_symlink() or not p.is_file() or not p.stat().st_size for p in entries):
        raise ValueError("notices must be nonempty regular files")
    names = {p.name for p in entries}
    if not REQUIRED | {"elf-notices.json"} <= names:
        raise ValueError("missing required redistribution notices")
    notices = names - {"elf-notices.json"}
    if any(not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.+-]*\.txt", n) for n in notices):
        raise ValueError("unexpected notice filename")
    mapping = json.loads((source / "elf-notices.json").read_text(encoding="utf-8"))
    elf = set()
    for p in bundle.rglob("*"):
        if not p.is_symlink() and p.is_file():
            with p.open("rb") as stream:
                if stream.read(4) == b"\x7fELF":
                    elf.add(p.relative_to(bundle).as_posix())
    if not isinstance(mapping, dict) or set(mapping) != elf:
        raise ValueError("ELF notice inventory must cover exact bundled ELF files")
    for path, refs in mapping.items():
        if (not isinstance(refs, list) or not refs or
                not all(isinstance(n, str) and n in notices for n in refs)):
            raise ValueError("missing notice reference for " + path)
    if (source / "llama.cpp.txt").read_bytes() != (bundle / "runtime/LICENSE").read_bytes():
        raise ValueError("llama.cpp notice differs from staged runtime license")
    destination = bundle / "licenses" / "reviewed"
    destination.mkdir()
    for p in entries:
        shutil.copyfile(p, destination / p.name)
        (destination / p.name).chmod(0o644)


if __name__ == "__main__":
    stage(Path(sys.argv[1]), Path(sys.argv[2]))
