#!/usr/bin/env bash
# Inputs are supplied by the shared runtime/release owner, never fetched here.
set -euo pipefail
export LC_ALL=C
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/../.." && pwd)
[[ $# == 3 ]] || { echo "usage: $0 VERIFIED_RUNTIME_DIR SHA256SUMS NEW_OUTPUT_DIR" >&2; exit 2; }
runtime=$(realpath "$1")
sums=$(realpath "$2")
out=$(realpath -m "$3")
[[ $(uname -m) == x86_64 && $(getconf GNU_LIBC_VERSION) == 'glibc 2.39' ]]
python -c 'import sys; assert sys.version_info[:2] == (3,12)'
[[ ! -e "$out" ]] || { echo "output must not exist" >&2; exit 2; }
# Require a flat, regular-file runtime payload with a complete trusted checksum list.
python "$here/verify_runtime.py" "$runtime" "$sums"
mkdir -p "$out"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
cd "$repo"
python -m PyInstaller --noconfirm --clean --onedir --name tinybuilder \
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
cp "$repo/LICENSE" "$bundle/licenses/TinyBuilder.txt"
cp "$here/README.md" "$bundle/README.md"
# Preserve upstream notices, including Python and all collected libraries.
cp "$sums" "$bundle/licenses/runtime-SHA256SUMS"
python -m pip show pyinstaller > "$bundle/licenses/pyinstaller-build-metadata.txt"
"$here/audit.sh" "$bundle" > "$out/elf-audit.txt"
"$here/smoke.sh" "$bundle"
epoch=${SOURCE_DATE_EPOCH:-0}
tar --sort=name --mtime="@$epoch" --owner=0 --group=0 --numeric-owner \
  -C "$out" -cf - TinyBuilder-linux-x64 | gzip -n > "$out/TinyBuilder-linux-x64.tar.gz"
(cd "$out" && sha256sum TinyBuilder-linux-x64.tar.gz > SHA256SUMS)
stat -c 'compressed_bytes=%s' "$out/TinyBuilder-linux-x64.tar.gz"
du -sb "$bundle"
