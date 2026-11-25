#!/bin/sh
set -eu
# Resolve the extracted launcher without changing the project's cwd.
launcher=$(realpath -e -- "$0")
root=${launcher%/*}
# PyInstaller owns this backup variable. Do not trust a stale inherited copy.
# Leave the user's LD_LIBRARY_PATH intact for the bootloader to preserve.
unset LD_LIBRARY_PATH_ORIG
exec "$root/app/tinybuilder" "$@"
