"""Prepare and inspect public source-only proposal workspaces without inference.

No model, subprocess, network, evaluator execution, private fixture, or source
transfer. Output is a separate directory; each model-facing root contains only
the public seeded class files. The manifest is outside those roots.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

from .coding_v1_corpus import REPOSITORIES
from .contained_corpus import TAX_PATH
from .contained_public import TASKS

VERSION = 1
MAX_SOURCE_BYTES = 32 * 1024
MANIFEST = "public-plan.json"


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _inventory():
    """Regenerate source identities from reviewed repository-owned fixtures."""
    rows = []
    for repo, (split, classes, tasks) in REPOSITORIES.items():
        files = {f"app/CodingV1/{cls}.php": source.encode("utf-8")
                 for cls, source in classes.items()}
        for task in tasks:
            allowed = tuple(f"app/CodingV1/{cls}.php" for cls, _, _ in task.changes)
            spec_paths = (TAX_PATH,) if task.name == "exempt_tax" else TASKS[task.name].files
            if set(allowed) != set(spec_paths) or not set(allowed) <= files.keys():
                raise ValueError("Corpus and contained scorer scopes differ")
            planned = 9 if task.name == "exempt_tax" else len(TASKS[task.name].probes)
            rows.append(({
                "task": task.name, "repository": repo, "split": split,
                "project": f"projects/{repo}/{task.name}",
                "prompt": task.prompt,
                "allowed_edit_paths": list(allowed),
                "patch_budget": len(allowed),
                "planned_observations": planned,
                "seed_sha256": {path: digest(content) for path, content in sorted(files.items())},
            }, files))
    return rows


def plan():
    tasks = [row for row, _ in _inventory()]
    return {"version": VERSION, "condition": "public-source-only-proposals",
            "semantic_qualification": False, "tasks": tasks,
            "planned_tasks": len(tasks),
            "planned_observations": sum(row["planned_observations"] for row in tasks)}


def _manifest_bytes(result):
    return (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")


def prepare(output: Path):
    # Explicit fresh destination only; never overwrite a prior campaign.
    output = Path(output).absolute()
    output.mkdir(exist_ok=False)
    for row, files in _inventory():
        root = output / row["project"]
        root.mkdir(parents=True, exist_ok=False)
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as handle:
                handle.write(content)
    result = plan()
    with (output / MANIFEST).open("xb") as handle:
        handle.write(_manifest_bytes(result))
    return result


def _metadata(path: Path, directory: bool):
    info = path.lstat()
    if (stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
        raise ValueError("link_or_reparse_point")
    if directory:
        if not stat.S_ISDIR(info.st_mode):
            raise ValueError("expected_directory")
    elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("non_regular_or_linked_file")
    return info


def _signature(info):
    # Reading can update atime. Compare identity, size and modification
    # metadata instead of rejecting a file because it was read.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _same_open_file(by_path, by_handle):
    # Windows stat(path) and fstat(fd) can expose different ctime semantics.
    # Match identity and size/mtime across providers, and compare ctime only
    # within each provider. Fail closed if file identity is unavailable.
    return (by_path.st_ino != 0 and by_handle.st_ino != 0
            and os.path.samestat(by_path, by_handle)
            and stat.S_ISREG(by_handle.st_mode) and by_handle.st_nlink == 1
            and not (getattr(by_handle, "st_file_attributes", 0)
                     & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
            and by_path.st_size == by_handle.st_size
            and by_path.st_mtime_ns == by_handle.st_mtime_ns)


def _bounded_read(path: Path, limit: int) -> bytes:
    before = _metadata(path, False)
    if before.st_size > limit:
        raise ValueError("source_budget")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        opened = os.fstat(handle.fileno())
        if not _same_open_file(before, opened):
            raise ValueError("source_changed_or_oversize")
        content = handle.read(limit + 1)
        if _signature(os.fstat(handle.fileno())) != _signature(opened):
            raise ValueError("source_changed_or_oversize")
    after = _metadata(path, False)
    if len(content) > limit or _signature(before) != _signature(after) or len(content) != after.st_size:
        raise ValueError("source_changed_or_oversize")
    return content


def _snapshot(project: Path, files: dict[str, bytes]):
    # Fixed inventory and exact directory traversal: never open extra files.
    allowed_dirs = {str(parent.as_posix()) for relative in files
                    for parent in Path(relative).parents if parent != Path(".")}
    observed = {}

    def visit(directory, prefix=""):
        _metadata(directory, True)
        for entry in sorted(directory.iterdir(), key=lambda path: path.name):
            relative = prefix + entry.name
            if relative in allowed_dirs:
                visit(entry, relative + "/")
            elif relative in files:
                observed[relative] = digest(_bounded_read(entry, MAX_SOURCE_BYTES))
            else:
                raise ValueError("unexpected_path")

    visit(project)
    if observed.keys() != files.keys():
        raise ValueError("missing_source")
    return observed


def inspect(root: Path):
    root = Path(root).absolute()
    _metadata(root, True)
    expected = plan()
    manifest = _bounded_read(root / MANIFEST, 256 * 1024)
    # Byte equality also rejects duplicate fields and bool/int coercions.
    if manifest != _manifest_bytes(expected):
        raise ValueError("campaign_manifest_differs")
    rows = []
    for row, files in _inventory():
        task = {"task": row["task"], "planned_observations": row["planned_observations"]}
        try:
            project = root
            for part in Path(row["project"]).parts:
                project = project / part
                _metadata(project, True)
            observed = _snapshot(project, files)
            changed = [path for path in sorted(files)
                       if observed[path] != row["seed_sha256"][path]]
            if not set(changed) <= set(row["allowed_edit_paths"]):
                task.update(status="scope_rejected", reason="unapproved_source_change")
            elif not changed:
                task.update(status="no_change", changed_paths=[])
            else:
                task.update(status="proposal_ready", changed_paths=changed,
                            candidate_sha256={path: observed[path] for path in row["allowed_edit_paths"]})
        except OSError:
            task.update(status="scope_rejected", reason="source_unavailable")
        except ValueError as error:
            task.update(status="scope_rejected", reason=str(error))
        rows.append(task)
    counts = {status: sum(row["status"] == status for row in rows)
              for status in ("proposal_ready", "no_change", "scope_rejected")}
    return {"condition": expected["condition"], "semantic_qualification": False,
            "planned_tasks": expected["planned_tasks"], "planned_observations": expected["planned_observations"],
            "attempted_semantic_observations": 0, "counts": counts, "tasks": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    create = sub.add_parser("prepare")
    create.add_argument("--output", type=Path, required=True)
    check = sub.add_parser("inspect")
    check.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.output) if args.operation == "prepare" else inspect(args.root)
    print(json.dumps(result, sort_keys=True))
    return 2 if result.get("counts", {}).get("scope_rejected") else 0


if __name__ == "__main__":
    raise SystemExit(main())
