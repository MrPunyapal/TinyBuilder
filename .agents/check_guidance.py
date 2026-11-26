"""Model-free checks for TinyBuilder's repository guidance (not runtime code).

Only the project convention of single-line name/description YAML frontmatter
and relative inline Markdown links is checked. No external URLs are fetched;
no claims about Codex or ChatGPT skill activation are made by this check.
"""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


DOCS = ("AGENTS.md", "docs/AGENT_GUIDE.md", "docs/PROJECT_STATUS.md",
        "docs/CHATGPT_PROJECT_INSTRUCTIONS.md")
REQUIRED = {"tinybuilder-" + name for name in (
    "onboard", "maintainer", "implementation", "benchmark",
    "model-research", "release", "knowledge-maintenance",
)}
NAME = re.compile(r"tinybuilder-[a-z0-9]+(?:-[a-z0-9]+)*")
LINK = re.compile(r"(?<!!)\[([^\]\n]+)\]\(([^)\s]+)\)")
INDEX = re.compile(r"(?m)^- \[([^\]\n]+)\]\(\.agents/skills/([^/]+)/SKILL\.md\):")


def validate(root: Path):
    """Return human-readable errors; never change files or use the network."""
    root = root.resolve()
    errors = []
    documents = {}
    skills = root / ".agents/skills"
    names = set()
    seen_names = set()

    def read(path):
        label = path.relative_to(root).as_posix()
        try:
            if not path.resolve().is_relative_to(root):
                raise ValueError("outside repository")
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError, ValueError):
            errors.append(f"{label}: missing or unreadable guidance")
            return ""
        documents[label] = content
        if not content.strip():
            errors.append(f"{label}: empty guidance")
        return content

    for relative in DOCS:
        read(root / relative)
    if not skills.is_dir():
        errors.append(".agents/skills: missing skill directory")
    else:
        for directory in sorted(skills.iterdir()):
            if not directory.is_dir():
                continue
            path = directory / "SKILL.md"
            name = directory.name
            names.add(name)
            content = read(path)
            lines = content.splitlines()
            label = path.relative_to(root).as_posix()
            if (len(lines) < 5 or lines[0] != "---" or lines[3] != "---"
                    or not lines[1].startswith("name: ")
                    or not lines[2].startswith("description: ")):
                errors.append(f"{label}: expected name and description frontmatter")
                continue
            declared = lines[1][6:]
            description = lines[2][13:]
            if declared != name or not NAME.fullmatch(declared) or len(declared) > 64:
                errors.append(f"{label}: invalid name or directory mismatch")
            if declared in seen_names:
                errors.append(f"{label}: duplicate skill name")
            seen_names.add(declared)
            # Keep our minimal YAML convention unambiguous without dependencies.
            if (not description.strip() or description != description.strip()
                    or len(description) > 1024 or ": " in description or " #" in description
                    or description[0] in "-?:,[]{}#&*!|>'\"%@\x60"
                    or any(ord(c) < 32 for c in description)):
                errors.append(f"{label}: invalid single-line description")
            if not any(line.strip() for line in lines[4:]):
                errors.append(f"{label}: missing skill instructions")
    for name in sorted(REQUIRED - names):
        errors.append(f".agents/skills: required skill missing: {name}")

    indexed = INDEX.findall(documents.get("AGENTS.md", ""))
    indexed_names = [name for _, name in indexed]
    for label, name in indexed:
        if label != name or name not in names:
            errors.append(f"AGENTS.md: invalid skill index entry: {label}")
    if len(indexed_names) != len(set(indexed_names)):
        errors.append("AGENTS.md: duplicate skill index entry")
    for name in sorted(names - set(indexed_names)):
        errors.append(f"AGENTS.md: skill not indexed: {name}")

    for label, content in documents.items():
        # Fenced samples may deliberately mention non-existent paths.
        in_fence = False
        for line in content.splitlines():
            if line.lstrip().startswith(("~~~", "\x60\x60\x60")):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            for _, link in LINK.findall(line):
                try:
                    parts = urlsplit(link)
                    if parts.scheme or parts.netloc or not parts.path:
                        continue
                    target = ((root / label).parent / unquote(parts.path)).resolve()
                    valid = target.is_relative_to(root) and target.exists()
                except (OSError, ValueError, RuntimeError):
                    valid = False
                if not valid:
                    errors.append(f"{label}: invalid relative link: {link}")
    return errors


def main():
    errors = validate(Path(__file__).resolve().parent.parent)
    if errors:
        for error in errors:
            print(error)
        return 1
    print("Agent guidance metadata, index and relative links: pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
