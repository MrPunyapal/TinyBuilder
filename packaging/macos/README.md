# macOS ARM64 development distribution

Status: packaging scaffold, not a supported or notarized release. Schema-1 runtime manifest generation is implemented; shared runtime discovery, model storage and guided entry point are pending integration. Do not substitute a second implementation. Main currently
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

Supply the original b6500 ARM64 ZIP, not a caller-created directory or inventory. The build checks its SHA-256 against the pinned upstream release API and PR #10 catalog (4f34ae19823ee22e8036d6da91f083ca62ab926c2a0a4a5ce9df34897360087b). Official asset: https://github.com/ggml-org/llama.cpp/releases/download/b6500/llama-b6500-bin-macos-arm64.zip. Download only the runtime archive, never models. The packager parses the same bounded archive bytes that it hashes, selects regular llama-server and dylib members, rejects unsafe paths/collisions/links, flattens the selected files, verifies the pinned upstream MIT license Git blob and ad-hoc signs native files before hashing the final schema-1 manifest. No claim that the actual archive layout has been validated yet; if a required resource or symlink is found, stop and coordinate with PR #10 rather than silently omit or rewrite it. Verify actual dependencies on the native runner. The fixture-only input path has no production manifest or upstream provenance and is distinctly named.

From repository root:

    python -m unittest discover -s packaging/macos -p 'test_*.py' -v
    bash packaging/macos/build.sh /absolute/llama-b6500-bin-macos-arm64.zip /absolute/new/output

The output path must not exist and must be outside the runtime input. Build from committed tracked sources; a Git archive snapshot excludes untracked files. The script records platform, Python and runtime inventory provenance, performs isolated CLI help/doctor smoke checks, rejects non-system absolute dylib dependencies and rpaths, and verifies the resulting DMG. Relative rpath resolution still requires native inspection. Frozen bundle links must be relative, contained and non-dangling so copying the distribution does not break them. The DMG contains a folder to copy as a unit
into a user-selected location. No Python, Git, Ollama or developer tools are
required by the intended installed artifact. Do not launch the development
artifact by bypassing Gatekeeper; use authorized locally built development
copies for testing. No native .app is claimed. A proper Finder app launcher
must be evaluated with the shared guided application before public release.

The shared schema-1 manifest is from PR #10. Installed resource contract proposed to PR #3: the frozen executable at TinyBuilder/tinybuilder/tinybuilder resolves runtime via Path(sys.executable).resolve().parent.parent / 'runtime'; the application owns discovery and guided no-argument invocation. Until #3 is integrated the launcher shows CLI help, not guided startup. PR 2 owns models/preferences in
native user data outside the distribution, typically ~/Library/Application
Support/TinyBuilder. Removal or replacement of the copied folder must not
remove external data. Do not introduce migration or deletion logic here.

## Native deterministic packaging fixture

On a native Mac with the approved Python/PyInstaller environment, run:

    bash packaging/macos/native_fixture_smoke.sh

This compiles a tiny test executable with Xcode's clang, signs it ad-hoc,
stages it through the actual build pipeline, verifies and mounts the DMG,
runs help/doctor directly from the read-only mounted DMG, copies the folder to a path containing spaces and non-ASCII characters,
and runs the relocated frozen CLI and fixture version check with an isolated
HOME and system-only PATH. The temporary DMG is destroyed; never publish
or reuse its fake runtime. This is a packaging-only test double, not
llama.cpp and not CPU/Metal or Gatekeeper acceptance. No model is needed.
The CI owner may call this script on the macOS runner once dependencies
are available. Finder interaction remains manual.

## Acceptance and signing

Inspect dependencies.txt and load-commands.txt for absolute build paths,
unexpected third-party libraries, unresolved @rpath/@loader_path references,
and minimum OS versions. The script checks arm64 slices, absolute non-system dependencies/rpaths and existing signatures
but does not prove all dependencies resolve. Verify runtime version/help,
actual startup and CPU inference (--device none --gpu-layers 0, matching PR #10). The build checks the b6500 version and both CPU-related help flags; flags alone do not prove actual inference.
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
Regenerate runtime-manifest.json files hashes from the final signed runtime bytes (preserving original archive provenance); validate with the shared resolver. Complete dependency notices/SBOM (Python distribution license, PyInstaller license and bootloader exception, installed wheels and native dylib provenance) and review before outer DMG creation/signing. Sign the final distribution, submit with xcrun notarytool submit --keychain-profile
PROFILE --wait, inspect the notarization log, staple and validate with xcrun
stapler, then assess with spctl and test a quarantined download on a clean Mac.
Use a protected release environment and Keychain credentials only; never
sign with unapproved credentials or put secrets in source or PR workflows.
The development DMG is intentionally not notarized. Regenerate checksums after
any signing/stapling. Collect Python, PyInstaller, application dependency and
llama.cpp licenses and notices before release; the scaffold copies the project and pinned llama.cpp licenses; complete third-party inventory remains a release gate. Intel and universal2 unsupported.

## Primary references

- https://docs.python.org/3.12/using/mac.html
- https://pyinstaller.org/en/stable/usage.html
- https://pyinstaller.org/en/stable/feature-notes.html
- https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
- https://github.com/ggml-org/llama.cpp/releases
- https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- https://developer.apple.com/documentation/security/resolving-common-notarization-issues
