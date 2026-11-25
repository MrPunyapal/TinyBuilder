#!/bin/bash
# Development artifact only; run from a locked, native Python 3.12 environment.
set -euo pipefail
umask 022
[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || { echo "Native macOS arm64 required" >&2; exit 1; }
[[ "$(sysctl -in sysctl.proc_translated 2>/dev/null || true)" != 1 ]] || { echo "Rosetta is not supported" >&2; exit 1; }
[[ $# == 2 ]] || { echo "Usage: bash build.sh VERIFIED_RUNTIME_DIRECTORY NEW_OUTPUT_DIRECTORY" >&2; exit 2; }
HERE="$(cd -- "$(dirname -- "$0")" && pwd -P)"
ROOT="$(cd "$HERE/../.." && pwd -P)"
PYTHON="${PYTHON:-python3}"
"$PYTHON" -c 'import sys,platform; assert sys.version_info[:2] == (3,12) and platform.machine() == "arm64"'
"$PYTHON" -c 'import PyInstaller; assert PyInstaller.__version__ == "6.22.2"'
RUNTIME="$(cd -- "$1" && pwd -P)"
# Refuse existing output; never delete arbitrary user paths.
mkdir -- "$2"
OUT="$(cd -- "$2" && pwd -P)"
STAGE="$OUT/stage/TinyBuilder"
mkdir -p "$STAGE"
"$PYTHON" "$HERE/verify_runtime.py" "$RUNTIME"
"$PYTHON" -m PyInstaller --noconfirm --clean --onedir --console --target-architecture arm64 \
    --name tinybuilder --paths "$ROOT" --distpath "$STAGE" \
    --workpath "$OUT/work" --specpath "$OUT" "$HERE/entry.py"
# Provisional staging boundary; runtime discovery must be coordinated with PR 1.
ditto "$RUNTIME" "$STAGE/runtime"
"$PYTHON" "$HERE/verify_runtime.py" "$STAGE/runtime"
install -m 755 "$HERE/TinyBuilder.command" "$STAGE/TinyBuilder.command"
cp "$ROOT/LICENSE" "$STAGE/LICENSE"
cp "$HERE/README.md" "$STAGE/README.md"
# Check every Mach-O, including libraries and Python extensions.
while IFS= read -r -d '' item; do
    if /usr/bin/file -b "$item" | grep -q 'Mach-O'; then
        [[ "$(lipo -archs "$item")" == arm64 ]] || { echo "Unexpected architecture: $item" >&2; exit 1; }
        otool -L "$item" >> "$OUT/dependencies.txt"
        otool -l "$item" >> "$OUT/load-commands.txt"
        codesign --verify --strict "$item"
    fi
done < <(find "$STAGE" -type f -print0)
"$STAGE/tinybuilder/tinybuilder" --help > "$OUT/cli-help.txt"
"$STAGE/runtime/llama-server" --version > "$OUT/runtime-version.txt" 2>&1
"$STAGE/runtime/llama-server" --help > "$OUT/runtime-help.txt" 2>&1
du -sk "$STAGE" > "$OUT/application-size-kib.txt"
hdiutil create -volname "TinyBuilder Development" -srcfolder "$OUT/stage" -format UDZO "$OUT/TinyBuilder-arm64-development.dmg"
(cd "$OUT" && shasum -a 256 TinyBuilder-arm64-development.dmg > SHA256SUMS)
"$PYTHON" -m pip freeze > "$OUT/python-build-environment.txt"
git -C "$ROOT" rev-parse HEAD > "$OUT/source-commit.txt"
echo "Development artifact only. Native acceptance and release signing are separate gates."
