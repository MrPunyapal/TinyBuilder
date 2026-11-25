#!/bin/bash
# Development artifact only; run from a locked, native Python 3.12 environment.
set -euo pipefail
umask 022
[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || { echo "Native macOS arm64 required" >&2; exit 1; }
[[ "$(sysctl -in sysctl.proc_translated 2>/dev/null || true)" != 1 ]] || { echo "Rosetta is not supported" >&2; exit 1; }
[[ $# == 3 ]] || { echo "Usage: bash build.sh VERIFIED_RUNTIME_DIRECTORY TRUSTED_INVENTORY_SHA256 NEW_OUTPUT_DIRECTORY" >&2; exit 2; }
HERE="$(cd -- "$(dirname -- "$0")" && pwd -P)"
ROOT="$(cd "$HERE/../.." && pwd -P)"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys,platform; assert sys.version_info[:2] == (3,12) and platform.machine() == "arm64"'
"$PYTHON" -c 'import PyInstaller; assert PyInstaller.__version__ == "6.22.2"'
RUNTIME="$(cd -- "$1" && pwd -P)"
# Refuse existing output; never delete arbitrary user paths.
mkdir -- "$3"
OUT="$(cd -- "$3" && pwd -P)"
case "$OUT/" in "$RUNTIME/"*) echo "Output must be outside runtime input" >&2; exit 1;; esac
STAGE="$OUT/stage/TinyBuilder"
mkdir -p "$STAGE"
"$PYTHON" "$HERE/verify_runtime.py" "$RUNTIME" "$2"
git -C "$ROOT" rev-parse HEAD > "$OUT/source-commit.txt"
git -C "$ROOT" diff --quiet HEAD -- || { echo "Tracked source changes; commit before building" >&2; exit 1; }
sw_vers > "$OUT/build-platform.txt"
xcodebuild -version >> "$OUT/build-platform.txt" 2>&1 || xcode-select -p >> "$OUT/build-platform.txt"
"$PYTHON" -VV >> "$OUT/build-platform.txt"
printf '%s\n' "$2" > "$OUT/runtime-inventory-sha256.txt"
"$PYTHON" -m PyInstaller --noconfirm --clean --onedir --console --target-architecture arm64 \
    --name tinybuilder --paths "$ROOT" --distpath "$STAGE" \
    --workpath "$OUT/work" --specpath "$OUT" "$HERE/entry.py"
# Provisional staging boundary; runtime discovery must be coordinated with PR 1.
ditto "$RUNTIME" "$STAGE/runtime"
"$PYTHON" "$HERE/verify_runtime.py" "$STAGE/runtime" "$2"
install -m 755 "$HERE/TinyBuilder.command" "$STAGE/TinyBuilder.command"
cp "$ROOT/LICENSE" "$STAGE/LICENSE"
cp "$HERE/README.md" "$STAGE/README.md"
# Never execute a shell script masquerading as the native runtime.
for executable in "$STAGE/runtime/llama-server" "$STAGE/tinybuilder/tinybuilder"; do
    /usr/bin/file -b "$executable" | grep -q 'Mach-O.*executable'
done
# Check every Mach-O, including libraries and Python extensions.
# PyInstaller onedir uses symlinks; reject dangling or escaping links.
"$PYTHON" - "$STAGE" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
for path in root.rglob("*"):
    if path.is_symlink() and not path.resolve(strict=True).is_relative_to(root):
        raise SystemExit(f"escaping bundle symlink: {path}")
PY
while IFS= read -r -d '' item; do
    kind="$(/usr/bin/file -b "$item")"
    if [[ "$kind" == *Mach-O* ]]; then
        [[ "$(lipo -archs "$item")" == arm64 ]] || { echo "Unexpected architecture: $item" >&2; exit 1; }
        otool -L "$item" >> "$OUT/dependencies.txt"
        # Reject absolute non-system dylib install names. Relative rpath graph
        # still needs native acceptance and inspection of load commands.
        if otool -L "$item" | tail -n +2 | awk '{sub(/^[ \t]+/, ""); if ($0 ~ /^\// && $0 !~ /^\/usr\/lib\// && $0 !~ /^\/System\/Library\//) bad=1} END {exit !bad}'; then
            echo "Non-system absolute dylib dependency: $item" >&2
            exit 1
        fi
        otool -l "$item" >> "$OUT/load-commands.txt"
        codesign --verify --strict "$item"
    fi
done < <(find "$STAGE" -type f -print0)
SMOKE="$OUT/smoke"
mkdir -p "$SMOKE/home" "$SMOKE/project"
# No user configuration or developer-tool PATH during smoke tests.
env -i HOME="$SMOKE/home" PATH=/usr/bin:/bin "$STAGE/tinybuilder/tinybuilder" --help > "$OUT/cli-help.txt"
env -i HOME="$SMOKE/home" PATH=/usr/bin:/bin "$STAGE/tinybuilder/tinybuilder" doctor --project "$SMOKE/project" > "$OUT/doctor.txt"
"$STAGE/runtime/llama-server" --version > "$OUT/runtime-version.txt" 2>&1
"$STAGE/runtime/llama-server" --help > "$OUT/runtime-help.txt" 2>&1
du -sk "$STAGE" > "$OUT/application-size-kib.txt"
hdiutil create -volname "TinyBuilder Development" -srcfolder "$OUT/stage" -format UDZO "$OUT/TinyBuilder-arm64-development.dmg"
hdiutil verify "$OUT/TinyBuilder-arm64-development.dmg"
stat -f %z "$OUT/TinyBuilder-arm64-development.dmg" > "$OUT/dmg-size-bytes.txt"
(cd "$OUT" && shasum -a 256 TinyBuilder-arm64-development.dmg > SHA256SUMS)
"$PYTHON" -m pip freeze > "$OUT/python-build-environment.txt"
echo "Development artifact only. Native acceptance and release signing are separate gates."
