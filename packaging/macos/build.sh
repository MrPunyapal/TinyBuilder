#!/bin/bash
# Development artifact only; run from a locked, native Python 3.12 environment.
set -euo pipefail
umask 022
[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || { echo "Native macOS arm64 required" >&2; exit 1; }
[[ "$(sysctl -in sysctl.proc_translated 2>/dev/null || true)" != 1 ]] || { echo "Rosetta is not supported" >&2; exit 1; }
FIXTURE=0
if [[ $# == 4 && "$1" == --fixture ]]; then
    FIXTURE=1
    shift
elif [[ $# != 2 ]]; then
    echo "Usage: bash build.sh PINNED_RUNTIME_ZIP NEW_OUTPUT_DIRECTORY" >&2
    exit 2
fi
HERE="$(cd -- "$(dirname -- "$0")" && pwd -P)"
ROOT="$(cd "$HERE/../.." && pwd -P)"
PYTHON="${PYTHON:-python3}"
PYTHON="$("$PYTHON" -E -c 'import sys; print(sys.executable)')"
"$PYTHON" -E -c 'import sys,platform; sys.exit(0 if sys.version_info[:2] == (3,12) and platform.machine() == "arm64" else "Native Python 3.12 arm64 required")'
"$PYTHON" -E -c 'import sys,PyInstaller; sys.exit(0 if PyInstaller.__version__ == "6.22.2" else "PyInstaller 6.22.2 required")'
if [[ "$FIXTURE" == 1 ]]; then
    RUNTIME="$(cd -- "$1" && pwd -P)"
    "$PYTHON" -E "$HERE/verify_runtime.py" "$RUNTIME" "$2"
    DEST="$3"
else
    RUNTIME="$(cd -- "$(dirname -- "$1")" && pwd -P)/$(basename -- "$1")"
    [[ -f "$RUNTIME" ]] || { echo "Pinned archive required" >&2; exit 1; }
    DEST="$2"
fi
# Refuse existing output; validate before creating anything.
git -C "$ROOT" diff --quiet HEAD -- || { echo "Tracked source changes; commit before building" >&2; exit 1; }
SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD)"
OUT="$("$PYTHON" -E - "$RUNTIME" "$DEST" <<'PY'
import sys
from pathlib import Path
runtime = Path(sys.argv[1]).resolve(strict=True)
output = Path(sys.argv[2]).absolute()
if output.resolve().is_relative_to(runtime):
    raise SystemExit("Output must be outside runtime input")
output.mkdir()
print(output.resolve())
PY
)"
STAGE="$OUT/stage/TinyBuilder"
SOURCE="$OUT/source"
mkdir -p "$STAGE" "$SOURCE"
# Build only committed files, avoiding untracked project data and module shadowing.
git -C "$ROOT" archive --format=tar "$SOURCE_SHA" | tar -xf - -C "$SOURCE"
printf '%s\n' "$SOURCE_SHA" > "$OUT/source-commit.txt"
sw_vers > "$OUT/build-platform.txt"
xcodebuild -version >> "$OUT/build-platform.txt" 2>&1 || xcode-select -p >> "$OUT/build-platform.txt"
"$PYTHON" -VV >> "$OUT/build-platform.txt"
(
    cd "$SOURCE"
    "$PYTHON" -E -m PyInstaller --noconfirm --clean --onedir --console --target-architecture arm64 \
        --name tinybuilder --paths "$SOURCE" --collect-data tinybuilder --distpath "$STAGE" \
        --workpath "$OUT/work" --specpath "$OUT" "$SOURCE/packaging/macos/entry.py"
)
# Fixture mode is deliberately separate and has no production manifest.
if [[ "$FIXTURE" == 1 ]]; then
    ditto "$RUNTIME" "$STAGE/runtime"
    "$PYTHON" "$HERE/verify_runtime.py" "$STAGE/runtime" "$2"
    printf '%s\n' 'TEST FIXTURE ONLY - NOT LLAMA.CPP' > "$STAGE/FIXTURE-ONLY.txt"
    DMG="TinyBuilder-arm64-fixture.dmg"
    VOL="TinyBuilder Fixture"
else
    "$PYTHON" -E "$SOURCE/packaging/macos/stage_runtime.py" "$RUNTIME" "$SOURCE/packaging/macos/llama.cpp-LICENSE" "$STAGE/runtime"
    cp "$STAGE/runtime/runtime-manifest.json" "$OUT/runtime-manifest.json"
    # Use the actual shared validator when integrated, never a parallel runtime resolver.
    if [[ -f "$SOURCE/tinybuilder/runtime/manifest.py" ]]; then
        (cd "$SOURCE" && "$PYTHON" -E -c 'from pathlib import Path; from tinybuilder.runtime.manifest import resolve_runtime; import sys; resolve_runtime(Path(sys.argv[1]), "cpu")' "$STAGE/runtime")
    else
        printf '%s\n' 'Shared runtime validator not integrated' > "$OUT/integration-pending.txt"
    fi
    DMG="TinyBuilder-arm64-development.dmg"
    VOL="TinyBuilder Development"
fi
install -m 755 "$SOURCE/packaging/macos/TinyBuilder.command" "$STAGE/TinyBuilder.command"
cp "$SOURCE/LICENSE" "$STAGE/LICENSE"
cp "$SOURCE/packaging/macos/README.md" "$STAGE/README.md"
# Never execute a shell script masquerading as the native runtime.
for executable in "$STAGE/runtime/llama-server" "$STAGE/tinybuilder/tinybuilder"; do
    /usr/bin/file -b "$executable" | grep -q 'Mach-O.*executable'
done
# Check every Mach-O, including libraries and Python extensions.
# PyInstaller onedir uses symlinks; reject absolute, dangling or escaping links.
"$PYTHON" -E "$SOURCE/packaging/macos/check_bundle_links.py" "$STAGE"
"$PYTHON" - "$STAGE" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
for path in root.rglob("*"):
    if path.name.lower().endswith((".gguf", ".safetensors", ".sqlite", ".sqlite3", ".pem", ".p12", ".pfx", ".key")) or path.name.startswith(".env"):
        raise SystemExit(f"forbidden distribution path: {path.relative_to(root)}")
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
        if otool -l "$item" | awk '$1 == "cmd" {rpath=($2 == "LC_RPATH")} rpath && $1 == "path" && $2 ~ /^\// && $2 !~ /^\/usr\/lib(\/|$)/ && $2 !~ /^\/System\/Library(\/|$)/ {bad=1} END {exit !bad}'; then
            echo "Non-system absolute rpath: $item" >&2
            exit 1
        fi
        codesign --verify --strict "$item"
    fi
done < <(find "$STAGE" -type f -print0)
SMOKE="$OUT/smoke"
mkdir -p "$SMOKE/home" "$SMOKE/project"
# No user configuration or developer-tool PATH during smoke tests.
env -i HOME="$SMOKE/home" PATH=/usr/bin:/bin "$STAGE/tinybuilder/tinybuilder" --help > "$OUT/cli-help.txt"
env -i HOME="$SMOKE/home" PATH=/usr/bin:/bin "$STAGE/tinybuilder/tinybuilder" doctor --project "$SMOKE/project" > "$OUT/doctor.txt"
env -i HOME="$SMOKE/home" PATH=/usr/bin:/bin "$STAGE/runtime/llama-server" --version > "$OUT/runtime-version.txt" 2>&1
env -i HOME="$SMOKE/home" PATH=/usr/bin:/bin "$STAGE/runtime/llama-server" --help > "$OUT/runtime-help.txt" 2>&1
if [[ "$FIXTURE" == 0 ]]; then
    grep -Eq '(^|[^0-9])6500([^0-9]|$)' "$OUT/runtime-version.txt"
    grep -q -- '--device' "$OUT/runtime-help.txt"
    grep -q -- '--gpu-layers' "$OUT/runtime-help.txt"
fi
du -sk "$STAGE" > "$OUT/application-size-kib.txt"
hdiutil create -volname "$VOL" -srcfolder "$OUT/stage" -format UDZO "$OUT/$DMG"
hdiutil verify "$OUT/$DMG"
stat -f %z "$OUT/$DMG" > "$OUT/dmg-size-bytes.txt"
(cd "$OUT" && shasum -a 256 "$DMG" > SHA256SUMS)
"$PYTHON" -E - <<'PY' > "$OUT/python-build-environment.txt"
from importlib.metadata import distributions
for item in sorted(f"{dist.metadata['Name']}=={dist.version}" for dist in distributions()):
    print(item)
PY
echo "Development artifact only. Native acceptance and release signing are separate gates."
