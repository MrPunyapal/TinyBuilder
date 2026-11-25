#!/usr/bin/env bash
set -euo pipefail
root=$(realpath "$1")
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
mkdir -p "$tmp/home" "$tmp/project" "$tmp/bin"
# Launcher needs realpath; no Python, Git or Ollama on PATH.
ln -s "$(command -v realpath)" "$tmp/bin/realpath"
ln -s "$root/tinybuilder" "$tmp/launcher with spaces"
cd "$tmp/project"
env -i HOME="$tmp/home" PATH="$tmp/bin" LC_ALL=C \
  XDG_DATA_HOME="$tmp/data" XDG_CONFIG_HOME="$tmp/config" \
  "$tmp/launcher with spaces" --help
env -i HOME="$tmp/home" PATH="$tmp/bin" LC_ALL=C \
  XDG_DATA_HOME="$tmp/data" XDG_CONFIG_HOME="$tmp/config" \
  "$tmp/launcher with spaces" doctor --project "$tmp/project"
env -i HOME="$tmp/home" PATH="$tmp/bin" LC_ALL=C LD_LIBRARY_PATH="$root/runtime" "$root/runtime/llama-server" --version
env -i HOME="$tmp/home" PATH="$tmp/bin" LC_ALL=C LD_LIBRARY_PATH="$root/runtime" "$root/runtime/llama-server" --help
