#!/usr/bin/env bash
set -euo pipefail
export LC_ALL=C
root=$(realpath "$1")
for required in app/tinybuilder runtime/llama-server; do
  [[ -x "$root/$required" ]] || exit 1
  readelf -h "$root/$required" >/dev/null
  [[ -f "$root/$required" && ! -L "$root/$required" ]] || exit 1
done
while IFS= read -r -d '' link; do
  target=$(realpath -e "$link")
  [[ "$target" == "$root/"* ]] || { echo "escaping bundle link: $link" >&2; exit 1; }
done < <(find "$root" -type l -print0)
while IFS= read -r -d '' f; do
  if ! readelf -h "$f" >/dev/null 2>&1; then continue; fi
  printf '\n%s\n' "${f#"$root/"}"
  header=$(readelf -h "$f")
  grep -q 'ELF64' <<< "$header"
  grep -q 'Advanced Micro Devices X86-64' <<< "$header"
  dynamic=$(readelf -d "$f")
  printf '%s\n' "$dynamic"
  # Reject non-relocatable or cwd-dependent ELF search paths.
  while IFS= read -r paths; do
    [[ -n "$paths" && "$paths" != :* && "$paths" != *: && "$paths" != *::* ]] || exit 1
    IFS=: read -ra components <<< "$paths"
    for component in "${components[@]}"; do
      case "$component" in
        '$ORIGIN'|'${ORIGIN}') ;;
        '$ORIGIN/'*|'${ORIGIN}/'*)
          [[ "$component" != *..* ]] || { echo "parent search path: $f" >&2; exit 1; } ;;
        *) echo "unsafe ELF search path: $f" >&2; exit 1 ;;
      esac
    done
  done < <(sed -nE '/\((RPATH|RUNPATH)\)/s/.*\[([^]]*)\].*/\1/p' <<< "$dynamic")
  versions=$(readelf --version-info "$f")
  printf '%s\n' "$versions"
  while read -r v; do
    [[ -z "$v" ]] && continue
    [[ $(printf '%s\n' "$v" 2.39 | sort -V | tail -1) == 2.39 ]] || {
      echo "glibc requirement exceeds 2.39: $f ($v)" >&2; exit 1;
    }
  done < <(grep -oE 'GLIBC_[0-9]+(\.[0-9]+)+' <<< "$versions" | cut -d_ -f2 | sort -u)
  # ldd only on trusted build outputs, never untrusted downloaded executables.
  if grep -q '(NEEDED)' <<< "$dynamic"; then
    if [[ "$f" == "$root/runtime/"* ]]; then
      deps=$(env -u LD_PRELOAD -u LD_LIBRARY_PATH ldd "$f" 2>&1) || exit 1
    else
      deps=$(env -u LD_PRELOAD LD_LIBRARY_PATH="$root/app/_internal" ldd "$f" 2>&1) || exit 1
    fi
    printf '%s\n' "$deps"
    if grep -q 'not found' <<< "$deps"; then exit 1; fi
  fi
done < <(find "$root" -type f -print0)
