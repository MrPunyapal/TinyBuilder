#!/bin/bash
set -eu
ROOT="$(cd -- "$(dirname -- "$0")" && pwd -P)"
if [ "$#" -eq 0 ]; then
    # Finder launch starts the shared guided app from the user's home.
    cd "$HOME"
    set -- app
fi
exec "$ROOT/tinybuilder/tinybuilder" "$@"
