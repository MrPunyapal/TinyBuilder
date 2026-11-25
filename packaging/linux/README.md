# Linux x64 preview packaging (not yet qualified)

Target Ubuntu 24.04 LTS / glibc 2.39, x86-64, Python 3.12 on the builder.
No system Python, Git, Ollama or root access is intended on the target.
Other distributions, musl, ARM64 and GPU builds are not qualified.
Portable tar.gz avoids AppImage's FUSE/runtime considerations, Debian/RPM's
distribution-specific maintenance and Flatpak's sandbox/runtime integration.
Revisit those formats after the portable preview passes acceptance.

## Build

On a trusted Ubuntu 24.04 x64 builder install python3.12-venv, binutils,
coreutils, gzip and tar. From repository root:

    python3.12 -m venv /tmp/tinybuilder-linux-build
    source /tmp/tinybuilder-linux-build/bin/activate
    python -m pip install 'pyinstaller==6.15.0'
    python -m pip install .
    bash packaging/linux/build.sh /absolute/verified-runtime /absolute/runtime-SHA256SUMS /tmp/tinybuilder-linux-output

The runtime directory must be a flat payload containing llama-server, LICENSE,
required native libraries and their notices. The checksum inventory must come
from the shared runtime owner's reviewed pin, not be generated from arbitrary
downloaded files. No model weights. Build does not fetch runtime assets.
Use a CPU build with portable instruction-set configuration, no GPU dependency,
and $ORIGIN-relative runtime library resolution or static linking as appropriate.
Shared runtime owner must provide the exact upstream commit, asset digest,
CPU feature floor, manifest schema, and redistribution terms. These do not
exist on the base commit. This staging interface is provisional and not
a substitute for the shared runtime manifest.

The entry wrapper currently calls tinybuilder.cli:main (the existing console
script). Guided startup, runtime discovery and XDG paths are integration gates.
No packaging code creates or deletes user model/preferences directories.
Update by extracting to a new directory; remove only the old extracted folder.
No automated cleanup of user data.

The PyInstaller bootloader modifies LD_LIBRARY_PATH; shared subprocess owners
must restore LD_LIBRARY_PATH_ORIG (or unset LD_LIBRARY_PATH when absent) for
external tools and isolate the bundled server environment. Do not globally
export runtime paths from the launcher. This remains an integration blocker.

## Qualification

Run the build, examine elf-audit.txt for interpreter, NEEDED, RPATH/RUNPATH
and host-only dependencies. Reject absolute build paths and unresolved libraries.
Run smoke.sh against the extracted archive on a clean Ubuntu 24.04 x64 image
without Python, Git or Ollama installed, with networking disabled.
PATH isolation in smoke.sh is not proof of package absence. Record OS, CPU,
glibc, output checksums, exact build inputs, compressed and extracted bytes.
Check all redistributable libraries and include their actual license texts,
including CPython, PyInstaller bootloader and system-derived libraries before
release. Current license collection is incomplete; no publication authorized.
Archive timestamps and ownership are normalized; dependency lock, builder
image digest and bit-for-bit reproducibility remain unverified.
Real model loading, offline inference and randomized tool inspection are
separate gates; do not download weights without approval.

References:
- https://pyinstaller.org/en/stable/usage.html
- https://pyinstaller.org/en/latest/common-issues-and-pitfalls.html
- https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
