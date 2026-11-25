# macOS ARM64 development distribution

Status: packaging scaffold, not a supported or notarized release. The shared
runtime manifest, runtime discovery, model storage and guided entry point are
pending integration. Do not substitute a second implementation. Main currently
has a required CLI subcommand; the Finder-openable .command shows help and
accepts CLI arguments from Terminal. It is not yet the guided app.

## Build

Use an Apple Silicon Mac running native arm64 Python 3.12, Xcode command line
tools, and PyInstaller 6.22.2. The release owner must supply an exact Python
patch version and hash-locked wheelhouse for all build and application
dependencies; install offline using pip --no-index --require-hashes with that
lock. No dependency fetching is performed by build.sh. Record OS/SDK versions,
wheel hashes, runtime source revision and provenance. This is repeatable
staging, not a claim of byte-identical builds or a completed dependency lock.

Supply a trusted, pre-extracted ARM64 runtime directory from PR 1, containing
llama-server at its root, required libraries, its unmodified shared manifest,
licenses/notices and SHA256SUMS covering every regular file except itself.
Authenticate the inventory independently against the runtime owner's pinned
upstream asset digest/attestation before use. The inventory is not an upstream
signature. No model weights or user data. Symlink-based runtime layouts are
rejected until an agreed safe staging policy exists. The script does not
rewrite dylibs; use a relocatable, already signed runtime, and resolve any
invalid rpaths with the runtime owner before signing.

From repository root:

    python -m unittest discover -s packaging/macos -p 'test_*.py' -v
    bash packaging/macos/build.sh /absolute/verified/runtime /absolute/new/output

The output path must not exist. The DMG contains a folder to copy as a unit
into a user-selected location. No Python, Git, Ollama or developer tools are
required by the intended installed artifact. Do not launch the development
artifact by bypassing Gatekeeper; use authorized locally built development
copies for testing. No native .app is claimed. A proper Finder app launcher
must be evaluated with the shared guided application before public release.

The current runtime sibling layout is provisional: PR 1 must confirm the
installed resource root and manifest format. PR 4 must confirm frozen entry
point, default invocation and package data. PR 2 owns models/preferences in
native user data outside the distribution, typically ~/Library/Application
Support/TinyBuilder. Removal or replacement of the copied folder must not
remove external data. Do not introduce migration or deletion logic here.

## Acceptance and signing

Inspect dependencies.txt and load-commands.txt for absolute build paths,
unexpected third-party libraries, unresolved @rpath/@loader_path references,
and minimum OS versions. The script checks arm64 slices and existing signatures
but does not prove all dependencies resolve. Verify runtime version/help,
actual startup and CPU inference (-ngl 0 if supported by the pinned server).
Separately test Metal with explicit offload and inspect logs for real GPU
execution; no GPU claim from a help flag alone. Use a previously authorized
local GGUF, loopback managed server, disposable project and read-only inspection.
No model downloads in baseline CI. Test offline, with a clean user account and
without Python on PATH, from paths with spaces and non-ASCII characters. Test
Finder launch, cancellation, process cleanup and preservation of model and
preference files across replacement/removal. Measure staged KiB and DMG bytes.
Record exact SHA, OS, hardware, logs, commands and failures; redact secrets.

Public release requires a reviewed signed app/launcher distribution design.
Sign each nested Mach-O inside-out using an approved Developer ID Application
identity, hardened runtime and secure timestamp; avoid blanket --deep signing.
Sign the final distribution, submit with xcrun notarytool submit --keychain-profile
PROFILE --wait, inspect the notarization log, staple and validate with xcrun
stapler, then assess with spctl and test a quarantined download on a clean Mac.
Use a protected release environment and Keychain credentials only; never
sign with unapproved credentials or put secrets in source or PR workflows.
The development DMG is intentionally not notarized. Regenerate checksums after
any signing/stapling. Collect Python, PyInstaller, application dependency and
llama.cpp licenses and notices before release; the scaffold only copies the
project license and supplied runtime notices. Intel and universal2 unsupported.

## Primary references

- https://docs.python.org/3.12/using/mac.html
- https://pyinstaller.org/en/stable/usage.html
- https://pyinstaller.org/en/stable/feature-notes.html
- https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
- https://github.com/ggml-org/llama.cpp/releases
- https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- https://developer.apple.com/documentation/security/resolving-common-notarization-issues
