#!/bin/bash
# Native fixture acceptance, not a product artifact or model test.
set -euo pipefail
[[ "$(uname -s)" == Darwin && "$(uname -m)" == arm64 ]] || { echo "Native macOS arm64 required" >&2; exit 1; }
HERE="$(cd -- "$(dirname -- "$0")" && pwd -P)"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/tinybuilder-macos-fixture.XXXXXX")"
MOUNT="$TMP/mount"
mounted=0
cleanup() {
    if [[ "$mounted" == 1 ]]; then
        /usr/bin/hdiutil detach "$MOUNT" || { echo "Fixture mount retained at $MOUNT" >&2; return 1; }
    fi
    rm -rf -- "$TMP"
}
trap cleanup EXIT
mkdir "$TMP/runtime" "$MOUNT" "$TMP/home" "$TMP/project"
xcrun clang -arch arm64 -Wall -Wextra -Werror "$HERE/fixtures/runtime.c" -o "$TMP/runtime/llama-server"
codesign --force --sign - "$TMP/runtime/llama-server"
printf '%s\n' 'Test-only executable, not llama.cpp. No third-party runtime shipped.' > "$TMP/runtime/NOTICE"
(cd "$TMP/runtime" && shasum -a 256 llama-server NOTICE > SHA256SUMS)
digest="$(shasum -a 256 "$TMP/runtime/SHA256SUMS" | awk '{print $1}')"
bash "$HERE/build.sh" --fixture "$TMP/runtime" "$digest" "$TMP/output"
(cd "$TMP/output" && shasum -a 256 -c SHA256SUMS)
grep -Fxq TINYBUILDER_PACKAGING_FIXTURE_NOT_LLAMA_CPP "$TMP/output/runtime-version.txt"
/usr/bin/hdiutil attach -readonly -nobrowse -mountpoint "$MOUNT" "$TMP/output/TinyBuilder-arm64-fixture.dmg"
mounted=1
# Launcher must work from a read-only mounted image without writing beside it.
env -i HOME="$TMP/home" PATH=/usr/bin:/bin "$MOUNT/TinyBuilder/TinyBuilder.command" --help
env -i HOME="$TMP/home" PATH=/usr/bin:/bin "$MOUNT/TinyBuilder/TinyBuilder.command" doctor --project "$TMP/project"
test -f "$MOUNT/TinyBuilder/FIXTURE-ONLY.txt"
INSTALLED="$TMP/installed space é"
ditto "$MOUNT/TinyBuilder" "$INSTALLED"
/usr/bin/hdiutil detach "$MOUNT"
mounted=0
# Execute the relocated copy, not the build stage or mounted volume.
env -i HOME="$TMP/home" PATH=/usr/bin:/bin "$INSTALLED/TinyBuilder.command" --help
env -i HOME="$TMP/home" PATH=/usr/bin:/bin "$INSTALLED/TinyBuilder.command" doctor --project "$TMP/project"
env -i HOME="$TMP/home" PATH=/usr/bin:/bin "$INSTALLED/runtime/llama-server" --version | grep -Fxq TINYBUILDER_PACKAGING_FIXTURE_NOT_LLAMA_CPP
if "$INSTALLED/runtime/llama-server" --model dummy; then
    echo "Fixture must not accept inference requests" >&2
    exit 1
fi
echo "Native packaging fixture smoke passed; NOT real llama.cpp, inference, or release acceptance."
