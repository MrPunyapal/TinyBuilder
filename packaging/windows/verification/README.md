# Windows standalone packaging verification

This additive workstream deliberately does not replace the maintainer's unpublished
PyInstaller/NSIS prototype. Preserve and commit that prototype before reconciling
it with these checks. No runtime manager, model download, app entry point or CI
workflow is implemented here.

## Offline build gate

Run on a trusted, private, freshly staged onedir payload before NSIS consumes it.
Do not run against a live install or arbitrary directory. All files and directories
must be ordinary non-linked entries, native PE binaries must be x64, and paths
must satisfy a narrow ASCII installer filename policy (not a restriction on the
user's installation path). The verifier rejects known weight, key, database and
environment file names, but does not replace content/license review.

The runtime owner must supply a mapping of payload-relative paths to lowercase
SHA-256 digests for every file in the dedicated runtime directory, obtained from
the verified pinned runtime and dependency assets, not calculated from an
untrusted staging directory. Include the server, DLLs and any runtime notices in
the map. This is a packaging input adapter, not a competing runtime manifest.
No runtime release or tool versions are guessed. An example invocation (adjust
paths to the shared manifest layout):

    python packaging/windows/verification/payload.py create STAGING OUTSIDE/stage.json --app TinyBuilder.exe --server runtime/llama-server.exe --runtime-files TRUSTED/runtime-files.json
    python packaging/windows/verification/payload.py verify STAGING OUTSIDE/stage.json
    python -m unittest discover -s packaging/windows/verification -v

The external JSON inventory records every file's logical bytes and SHA-256.
Keep it outside staging; never trust an installed copy as uninstall authority.
This is exact inventory verification, not signature verification, a complete PE
loader check, a race-resistant filesystem sandbox or a deletion utility.
Run signing before inventory generation if signing changes payload files.
The NSIS build must use the exact verified directory, not broad source globs.

## Native model-free smoke

On Windows, with actual installed executable paths:

    powershell.exe -NoProfile -File packaging/windows/verification/smoke.ps1 -App "C:\path\TinyBuilder.exe" -Server "C:\path\llama-server.exe"

Reports file hashes, byte sizes and exit codes. Probes use a fresh disposable
project and both server and unrelated working directories. No model downloads,
inference calls or raw child output retained in reports. A timeout is a failure.
The smoke cannot prove clean-machine compatibility or frozen child launch.

## Prototype integration and acceptance (not completed)

- Back up tracked/staged patches and reviewed untracked installer files outside
  the repository; commit only packaging sources to feat/windows-distribution.
  Do not reset, clean, force-push or overwrite local changes.
- Compare direct server launch and frozen child launch; record resolved exe/cwd,
  errno/winerror, PE imports (including transitive dependencies), CPU requirements
  and sanitized loader/process/init/readiness/inference categories. Coordinate
  shared runtime fixes with PR 1, backend with PR 3 and launcher with PR 4.
- Use approved local Python 3.12, PyInstaller onedir and NSIS. No new downloads
  unless separately authorized. Pin versions, hash assets and include all license
  notices. Record source SHA, runtime pin and tool versions.
- Use RequestExecutionLevel user, current-user Start Menu and HKCU uninstall
  registration. No PATH changes. Reject unsafe destination/reparse traversal and
  unknown file collisions. Generate installer/uninstaller ownership lists from
  trusted build input, never recursively remove the install root. Preserve models,
  settings, projects and unrelated files; coordinate paths with PR 2.
- Review eligible app-local VC runtime redistribution, avoid copying System32
  DLLs; verify minimum supported CPU and Windows version with pinned runtime.
- Authenticode is optional, using SHA-256 and a trusted timestamp; no credentials
  in ordinary CI. Unsigned builds can trigger SmartScreen; signing does not
  guarantee reputation.
- Measure exact installer bytes and SHA-256 (Get-Item/Get-FileHash) and installed
  owned file bytes, separately from user models. A clean payload must contain no
  model weights. Document metadata and upstream checksums.
- Native acceptance: run existing GGUF with CPU-only managed runtime, authenticated
  loopback readiness and genuine installed inference; offline repeat; alternate
  drive; Unicode/space paths; safe upgrade and uninstall; process cleanup.
  Use clean standard-user Windows x64 VM with no separate Python/Git/Ollama.
  PATH-only tests are not clean VM evidence.

Official references:
- https://pyinstaller.org/en/stable/runtime-information.html
- https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html
- https://nsis.sourceforge.io/Docs/Chapter4.html
- https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files
- https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool

Status: not tester-ready. No real installed inference, installer artifact or native
smoke result is claimed by this commit.
