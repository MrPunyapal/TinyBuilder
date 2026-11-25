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
    bash packaging/linux/build.sh /absolute/verified-runtime /absolute/runtime-SHA256SUMS /tmp/tinybuilder-linux-output /absolute/llama-b6500-bin-ubuntu-x64.zip /absolute/reviewed-notices

The runtime directory must be a flat payload containing llama-server, LICENSE,
required native libraries and their notices (only llama-server, lib*.so[.N...],
LICENSE*, NOTICE*, COPYING* filenames are accepted). The checksum inventory must come
from the shared runtime owner's reviewed pin, not be generated from arbitrary
downloaded files. No model weights. Build does not fetch runtime assets.
Use a CPU build with portable instruction-set configuration, no GPU dependency,
and $ORIGIN-relative runtime library resolution or static linking as appropriate.
The build requires the shared runtime branch to be integrated. It imports the
shared CPU_ARCHIVES and REVISION, verifies the original upstream ZIP digest,
checks that staged binaries are byte-identical to unique regular ZIP members,
writes schema-1 runtime-manifest.json and calls the shared resolve_runtime.
Notices not present in the ZIP require independently reviewed checksums.
The currently proposed shared pin is b6500. CPU feature floor, actual ZIP
layout, native dependency inventory and redistribution terms remain unverified.
No modified or rebuilt binaries may be substituted under this archive pin.

The entry wrapper currently calls tinybuilder.cli:main (the existing console
script). The integrated CLI dispatches frozen no-argument launches to the guided app;
installed startup, runtime discovery and XDG paths still require acceptance.
No packaging code creates or deletes user model/preferences directories.
Update by extracting to a new directory; remove only the old extracted folder.
No automated cleanup of user data.
The launcher resolves symlinks and preserves cwd, arguments, exit status and
caller LD_LIBRARY_PATH; it clears stale LD_LIBRARY_PATH_ORIG before bootloader
startup. It requires GNU realpath. The frozen executable is app/tinybuilder;
its sibling installation runtime is ../runtime relative to its directory.
PR #3 must publish guided entry/discovery; do not derive runtime from project cwd.

The PyInstaller bootloader modifies LD_LIBRARY_PATH; shared subprocess owners
must restore LD_LIBRARY_PATH_ORIG (or unset LD_LIBRARY_PATH when absent) for
external tools and isolate the bundled server environment. Do not globally
export runtime paths from the launcher. This remains an integration blocker.

## Qualification

Run `python -m unittest discover -s packaging/linux -p 'test_*.py' -v`
for deterministic runtime inventory tests (Python 3.12 or later).
Run the build, examine elf-audit.txt for interpreter, NEEDED, RPATH/RUNPATH
and host-only dependencies. Reject absolute build paths and unresolved libraries.
Run smoke.sh against the extracted archive on a clean Ubuntu 24.04 x64 image
without Python, Git or Ollama installed, with networking disabled.
PATH isolation in smoke.sh is not proof of package absence. Record OS, CPU,
glibc, output checksums, exact build inputs, compressed and extracted bytes.
The fifth build argument is a reviewed-notices directory containing actual
redistribution texts named CPython.txt, PyInstaller.txt, llama.cpp.txt (exactly
matching runtime/LICENSE), and additional *.txt notices for all collected
components. Include elf-notices.json: a JSON object keyed by each regular ELF
file relative to the bundle, e.g. {"app/tinybuilder":["PyInstaller.txt"],
"runtime/llama-server":["llama.cpp.txt"]}. These are examples, not a complete
inventory. Every ELF must map to one or more included notice filenames. Obtain
actual license texts and review source/redistribution obligations for CPython,
PyInstaller, llama.cpp, system-derived libraries and Python dependencies;
notices alone do not establish legal compliance. The build fails before archive
creation if the inventory is missing or incomplete. Inspect the retained staged
bundle and elf-audit.txt after a failed notice gate to assemble the exact reviewed
inventory, then rerun with a fresh output directory. No publication authorized.
The actual upstream payload and complete reviewed notice texts remain unverified.
The successful build records compressed, installed, application and runtime byte
counts in sizes.txt; no model weights are included.
The build enforces Python 3.12 and PyInstaller 6.15.0, refuses tracked changes,
freezes only a Git archive of the recorded source commit, and records the
source SHA and Python version outside the distribution. Untracked checkout
files are not copied into the build source. Archive timestamps and ownership
are normalized; dependency lock, builder image digest and bit-for-bit
reproducibility remain unverified.
Real model loading, offline inference and randomized tool inspection are
separate gates; do not download weights without approval.

References:
- https://pyinstaller.org/en/stable/usage.html
- https://pyinstaller.org/en/latest/common-issues-and-pitfalls.html
- https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
