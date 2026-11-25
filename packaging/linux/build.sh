#!/usr/bin/env bash
# Inputs are supplied by the shared runtime/release owner, never fetched here.
set -euo pipefail
export LC_ALL=C
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
[[ $# == 5 ]] || { echo "usage: $0 VERIFIED_RUNTIME_DIR SHA256SUMS NEW_OUTPUT_DIR PINNED_UPSTREAM_ZIP REVIEWED_NOTICES_DIR" >&2; exit 2; }
runtime=$(realpath "$1")
sums=$(realpath "$2")
out=$(realpath -m "$3")
archive=$(realpath "$4")
notices=$(realpath -e "$5")
[[ -d "$notices" ]]
# The shared runtime must be integrated before a distribution can be built.
[[ -f "$repo/tinybuilder/runtime/catalog.py" && -f "$repo/tinybuilder/runtime/manifest.py" ]] || { echo "shared runtime integration missing" >&2; exit 1; }
[[ $(uname -m) == x86_64 && $(getconf GNU_LIBC_VERSION) == 'glibc 2.39' ]]
python -I -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else "Python 3.12 required")'
python -I -c 'import sys,PyInstaller; sys.exit(0 if PyInstaller.__version__ == "6.15.0" else "PyInstaller 6.15.0 required")'
git -C "$repo" diff --quiet HEAD -- || { echo "Tracked source changes; commit before building" >&2; exit 1; }
source_sha=$(git -C "$repo" rev-parse HEAD)
[[ "$out" != "$runtime" && "$out" != "$runtime/"* ]] || { echo "output must be outside runtime input" >&2; exit 2; }
[[ ! -e "$out" ]] || { echo "output must not exist" >&2; exit 2; }
# Build exclusively from the recorded committed tree, not the caller's checkout.
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
mkdir "$work/source"
git -C "$repo" archive --format=tar "$source_sha" | tar -xf - -C "$work/source"
repo="$work/source"
here="$repo/packaging/linux"
cd "$repo"
# Require a flat, regular-file runtime payload with a complete trusted checksum list.
python "$here/verify_runtime.py" "$runtime" "$sums"
mkdir -p "$out"
printf '%s\n' "$source_sha" > "$out/source-commit.txt"
python -VV > "$out/python-version.txt" 2>&1
python -I -m PyInstaller --noconfirm --clean --onedir --name tinybuilder \
  --paths "$repo" --collect-all tinybuilder --distpath "$work/dist" \
  --workpath "$work/build" --specpath "$work" "$here/entry.py"
bundle="$out/TinyBuilder-linux-x64"
mkdir -p "$bundle/runtime" "$bundle/licenses"
mv "$work/dist/tinybuilder" "$bundle/app"
install -m 755 "$here/launch.sh" "$bundle/tinybuilder"
cp -a "$runtime/." "$bundle/runtime/"
# Revalidate the staged bytes before any execution.
python "$here/verify_runtime.py" "$bundle/runtime" "$sums"
# Drop inherited special mode bits; only the server needs execution.
find "$bundle/runtime" -type f -exec chmod 644 {} +
chmod 755 "$bundle/runtime/llama-server"
python "$here/prepare_manifest.py" "$bundle/runtime" "$sums" "$archive"
cp "$repo/LICENSE" "$bundle/licenses/TinyBuilder.txt"
cp "$here/README.md" "$bundle/README.md"
# Record the independently reviewed runtime inventory and build metadata.
cp "$sums" "$bundle/licenses/runtime-SHA256SUMS"
python -m pip show pyinstaller > "$bundle/licenses/pyinstaller-build-metadata.txt"
"$here/audit.sh" "$bundle" > "$out/elf-audit.txt"
python "$here/stage_notices.py" "$bundle" "$notices"
"$here/smoke.sh" "$bundle"
epoch=${SOURCE_DATE_EPOCH:-0}
tar --sort=name --mtime="@$epoch" --owner=0 --group=0 --numeric-owner \
  -C "$out" -cf - TinyBuilder-linux-x64 | gzip -n > "$out/TinyBuilder-linux-x64.tar.gz"
(cd "$out" && sha256sum TinyBuilder-linux-x64.tar.gz > SHA256SUMS)
{
  stat -c 'compressed_bytes=%s' "$out/TinyBuilder-linux-x64.tar.gz"
  printf 'installed_bytes=%s\n' "$(du -sb "$bundle" | cut -f1)"
  printf 'app_bytes=%s\n' "$(du -sb "$bundle/app" | cut -f1)"
  printf 'runtime_bytes=%s\n' "$(du -sb "$bundle/runtime" | cut -f1)"
} | tee "$out/sizes.txt"
