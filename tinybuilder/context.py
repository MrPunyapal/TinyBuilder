"""Read the project's installed frameworks without retaining remote documents."""

import json
from pathlib import Path


def project_summary(root: Path) -> str:
    lines = [f"Project root: {root.resolve()}"]
    composer = root / "composer.json"
    if composer.exists():
        try:
            data = json.loads(composer.read_text(encoding="utf-8"))
            require = {**data.get("require", {}), **data.get("require-dev", {})}
            packages = [f"{name}={version}" for name, version in require.items()
                        if name == "laravel/framework" or name.startswith(("livewire/", "filament/", "laravel/"))]
            lines.append("Composer dependencies: " + (", ".join(packages[:20]) or "no Laravel packages detected"))
        except (OSError, ValueError, TypeError):
            lines.append("composer.json could not be parsed")
    else:
        lines.append("No composer.json found")
    package = root / "package.json"
    if package.exists():
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
            names = list(data.get("dependencies", {})) + list(data.get("devDependencies", {}))
            lines.append("JavaScript packages: " + ", ".join(names[:25]))
        except (OSError, ValueError, TypeError):
            lines.append("package.json could not be parsed")
    return "\n".join(lines)
