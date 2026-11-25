#!/bin/bash
set -eu
ROOT="$(cd -- "$(dirname -- "$0")" && pwd -P)"
if [ "$#" -eq 0 ]; then
    # Current main has no guided default command. Replace with the shared
    # application entry contract during integration, not a second UI.
    cd "$HOME"
    set -- --help
fi
exec "$ROOT/tinybuilder/tinybuilder" "$@"
