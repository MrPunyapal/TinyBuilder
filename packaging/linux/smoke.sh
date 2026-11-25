#!/usr/bin/env bash
set -euo pipefail
root=$(realpath "$1")
tmp=$(mktemp -d)
trap 'rm -rf -- "$tmp"' EXIT
mkdir -p "$tmp/home" "$tmp/project" "$tmp/bin"
# Launcher needs dirname; no Python, Git or Ollama on PATH.
ln -s "$(command -v dirname)" "$tmp/bin/dirname"
env -i HOME="$tmp/home" PATH="$tmp/bin" LC_ALL=C \
  XDG_DATA_HOME="$tmp/data" XDG_CONFIG_HOME="$tmp/config" \
  "$root/tinybuilder" --help
env -i HOME="$tmp/home" PATH="$tmp/bin" LC_ALL=C \
  XDG_DATA_HOME="$tmp/data" XDG_CONFIG_HOME="$tmp/config" \
  "$root/tinybuilder" doctor --project "$tmp/project"
env -i HOME="$tmp/home" PATH="$tmp/bin" LC_ALL=C "$root/runtime/llama-server" --version
env -i HOME="$tmp/home" PATH="$tmp/bin" LC_ALL=C "$root/runtime/llama-server" --help
