# Standalone onboarding — draft, not a download announcement

The following is the intended user journey. Exact buttons, filenames, paths, supported versions and model choices must be confirmed against the accepted candidate before publication. Today the [source quick start](QUICKSTART.md) remains the documented route.

## Choose and verify an artifact

| Target | Intended distribution | Qualification |
|---|---|---|
| Windows x64 (Intel/AMD 64-bit) | Native installer | Pending |
| macOS Apple Silicon (ARM64) | Native app/DMG | Pending |
| Linux x64 (x86_64) | Portable archive | Pending |

Use only an explicitly published asset from the [project releases page](https://github.com/MrPunyapal/TinyBuilder/releases). If no qualified asset is listed for your system, do not substitute another architecture. On Windows check Settings > System > About; on macOS check About This Mac; on Linux use `uname -m`. Intel Macs and Windows/Linux ARM64 are not initial targets.

Compare the exact artifact's SHA-256 to the maintainer-published digest before opening it. Substitute the actual downloaded path for FILE:

- Windows PowerShell: `Get-FileHash -Algorithm SHA256 -LiteralPath 'FILE'`
- macOS: `shasum -a 256 'FILE'`
- Linux: `sha256sum -- 'FILE'`

A mismatch means stop, delete the suspect download and obtain a trusted copy. A hash does not authenticate the publisher. Check the release's signing status and OS trust prompts; do not bypass security protections. Signing/notarization is pending. Windows signature verification guidance: [Microsoft](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool). macOS: [Apple](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

## Installation and first launch (intended)

Windows: run the verified installer and follow its prompts. macOS: open the verified DMG and follow its documented launcher placement/launch instructions (the packaging workstream currently proposes a Terminal .command launcher, not a confirmed .app). Linux: extract the verified archive to a user-owned directory and use the documented launcher. Final installer options and minimum OS requirements are pending native acceptance. Basic inspection is designed not to need separately installed Python, Git or Ollama. Do not install system developer tools just to compensate for a broken standalone package; report the failure.

Choose a trusted, non-sensitive sample project directory on first launch. Keep write and command permissions off. Ask the assistant to inspect a known file and report a fact you can independently check. A successful tool event plus a correct fact is evidence; model prose alone is not.

## Models and offline operation (intended)

Choose an existing compatible GGUF without copying it unnecessarily, or explicitly authorize a catalog download. Before agreeing, review exact filename, source and immutable revision, model license, quantization, byte count, destination and expected SHA-256. No model is recommended by this draft. File size is not RAM/VRAM usage. The app should show available disk space and allow an alternative writable drive/directory. The model-manager workstream proposes the following defaults; these are branch-level design evidence, not installed-application guarantees:

| OS | Proposed model root |
|---|---|
| Windows | `%LOCALAPPDATA%\\TinyBuilder\\models` |
| macOS | `~/Library/Application Support/TinyBuilder/models` |
| Linux | `$XDG_DATA_HOME/tinybuilder/models` or `~/.local/share/tinybuilder/models` |

Select an existing writable directory on an attached volume for alternate/removable storage. Re-select after remount if the app reports a changed volume. Preferences and migration paths still require integration evidence.

For a catalog download, verification must finish before inference; cancellation or interruption must not make partial bytes usable. Retry only through a documented safe recovery path. Do not manually rename incomplete files into valid models. Cancellation may wait for a blocking network read; resume is conditional on a matching server validator and range response. A fresh transfer may be needed. Use only the application's explicit partial-discard action when available; do not delete an entire model directory. For imported files, verify provenance and compatibility yourself unless the app can match a trusted catalog digest. GGUF is a file format, not a license; model terms are separate from TinyBuilder's MIT license.

CPU inference is the intended baseline. The runtime workstream currently implements a CPU-only interface; Metal, CUDA and other acceleration are not advertised as available. No minimum RAM, VRAM or speed is promised. If loading fails, close other memory-heavy applications, choose a qualified smaller model or CPU mode when available, and consult the candidate's diagnostic instructions.

After installation and verified model availability, basic local inspection is intended to run without internet. Model downloads, dependency installation and optional external integrations may need a network. Offline behavior must be demonstrated with networking disabled before advertising it.

## Permissions and Laravel

Read-only is the intended default. Grant only necessary write/command rights in a disposable trusted project; inspect diffs and tests yourself. The existing CLI uses --allow-write, --allow-exec and repeatable --exec-command exact argv arrays (for example ["php","artisan","test"]). Standalone permission controls must be mapped and tested before publishing exact UI steps. An allowlisted executable can still run scripts, imports, child processes or network operations. Path checks are not OS isolation. See [security](SECURITY.md).

PHP and Composer are optional for inspection but needed for applicable Laravel tooling/tests. Laravel Boost is optional and uses php artisan boost:mcp in an existing app; see the [source README](../README.md). Native MCP discovery/direct transport is not proof of model-selected calls; strict JSON does not support MCP in the existing CLI. Only configure trusted servers, which can have independent side effects.

## Recovery, upgrades and removal (intended)

If launch fails, record the exact candidate, platform/architecture and sanitized error; check compatibility, digest and signing status. Do not disable protection. For model failure check compatibility, storage, verification and memory; for project errors choose a readable trusted directory. For a stuck runtime use the documented shutdown/recovery procedure; do not kill unrelated processes. Cancellation is cooperative, not a guarantee of instant interruption of a blocking request or already-running command.

Before upgrading, back up preferences and any irreplaceable local data, close the app and verify the new artifact. The release must document compatible data migrations and rollback limits. Uninstall should remove only application-owned program files, preserving models, preferences, project files and unrelated files by default. Exact removal paths and any explicit data deletion procedure are pending acceptance.

Report ordinary reproducible bugs at the [issue tracker](https://github.com/MrPunyapal/TinyBuilder/issues): candidate SHA/version, OS/architecture, CPU/RAM/GPU, model revision/quantization, reproduction steps, expected/actual result and reviewed sanitized diagnostics. Omit secrets, absolute personal paths, private source, prompts/transcripts and memory files. For vulnerabilities follow [security reporting](SECURITY.md). Contributors should follow [CONTRIBUTING](../CONTRIBUTING.md) and the source quick start.

### Provisional catalog entry — developer evidence only

The [model-manager PR](https://github.com/MrPunyapal/TinyBuilder/pull/11) reports the official Qwen2.5-Coder-1.5B-Instruct Q4_K_M GGUF pointer: `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`, 1,117,320,768 bytes, SHA-256 `cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046`, Apache-2.0 as declared by the upstream card. The [immutable upload revision](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/commit/2ab9f8f42af02fc212effaef7c4850c885e965f4) identifies the metadata, not downloaded bytes verified by this documentation workstream. Verify the pinned license and complete file before release. This entry is neither a recommendation nor a default and is not runtime-qualified.
