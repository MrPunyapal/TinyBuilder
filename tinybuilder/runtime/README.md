# Managed inference runtime (preview foundation)

Only this package owns native server lifecycle. The application supplies a trusted
absolute installation runtime directory, not the project path. Model management
supplies an already validated, absolute GGUF path (we check regular file, suffix
and magic again; not full GGUF validation).

    from tinybuilder.runtime import RuntimeManager, RuntimeFailure
    with RuntimeManager(runtime_root) as runtime:
        connection = runtime.start(absolute_gguf, backend="cpu", timeout=180)
        # Pass connection.base_url, connection.model_alias, connection.api_key
        # to the existing authenticated inference client. Do not log or serialize it.

Start is synchronous; run it on a worker. Poll status() for starting/loading
(indeterminate progress), ready, failed (sanitized failure category), stopping,
stopped. cancel() signals active startup; stop() cancels and joins the operation,
then terminates the owned server. A failed cleanup retains the handle for retry.
The startup timeout covers HTTP readiness after spawn, not file hashing or OS
process creation. Cancellation during those operations is cooperative.
Credentials are random, per-session, passed via LLAMA_API_KEY in the child
environment, not argv. Do not serialize dataclasses or retain connection after
stop. The credential is not protection against other processes under the same
OS account.

## Packaging contract

Supply a flat runtime directory (as staged by Linux/macOS packaging) containing
the executable, LICENSE, native dependencies and runtime-manifest.json.
The JSON schema version is 1. Required keys:

- schema: integer 1
- revision: b6500
- os: windows / macos / linux
- architecture: x64 / arm64
- backend: cpu
- executable: llama-server.exe (Windows), llama-server (POSIX)
- archive and archive_sha256: match catalog.py for target
- native_dependencies: list of bundled native dependency filenames
- files: mapping of every payload filename except runtime-manifest.json to its
  lowercase SHA-256. Includes LICENSE, executable, all libraries, any additional
  notices and any SHA256SUMS staged by packaging.

Use independently authenticated upstream bytes and review the extracted inventory;
the manifest itself must be delivered by a trusted installer. A colocated manifest
is not a signature or defense against an attacker who can replace both manifest
and files. Do not stage binaries from a selected project. No symlinks, nested
directories, model weights or unlisted files. OS-provided dependencies are not
listed as bundled files; packaging must audit them separately. macOS signing
changes bytes: coordinate final hashes after binary signing and before final
outer bundle signing. Do not claim support for unsigned/unqualified payloads.

Official b6500 metadata: https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/b6500
Pinned server flags: https://github.com/ggml-org/llama.cpp/blob/b6500/tools/server/README.md
Pinned license: https://github.com/ggml-org/llama.cpp/blob/b6500/LICENSE (MIT).
Redistribution notices for bundled dependencies remain to be inventoried.
Archive names and reported hashes are in catalog.py; no archive bytes or native
dependency inventory were independently verified in this change. No runtime
payload or production manifest is shipped yet. All packaging owners must agree
on the revision and generate the manifest from their audited staged files.

## Security and lifecycle limitations

Explicit loopback, no redirects/proxies for readiness, random alias and secret,
public health plus rejection of unauthenticated models and successful authenticated
alias match. The temporary free-port selection has an unavoidable bind race;
fail closed for unexpected replies and never kill another process. A hostile
local process could impersonate the server, including capturing a key during
that race; this is not an OS sandbox. A child exit during startup is classified
as server_crash, not guessed to be a loader, bind or model error. Raw server
output is discarded, not written to disk. No arbitrary extra flags, no web UI
or slots, no server-side tool execution enabled by this pinned server. Native
tool call formatting uses Jinja; TinyBuilder still authorizes and runs tools.

CPU uses --device none and zero GPU layers. CUDA/Vulkan/Metal/ROCm are reserved
backend names, deliberately rejected with cpu_recovery=True pending separately
qualified payloads and hardware detection. No silent fallback or downloads.

Windows uses absolute executable and trusted cwd with a restricted PATH.
POSIX uses a new process session and bounded TERM/KILL; Linux limits
LD_LIBRARY_PATH to the trusted runtime, macOS requires verified install names
and rpaths. These measures are not a complete native loader sandbox. Windows
uses direct child termination, not a Job Object. Ordinary stop and atexit are
implemented, but forced interpreter exit, signals, OS crashes, descendant
processes and Windows Job Object / POSIX supervisor behavior are unqualified.
Atexit does not run on SIGKILL or TerminateProcess. Application must use finally
or context manager for normal exits. A stop after failed cleanup can be retried.

Actual target binaries, OS loader dependencies, minimum OS/CPU features,
authentication and native inference with a real GGUF require local validation.
No baseline CI model downloads.

## Windows diagnostic handoff

Do not change the uncommitted installer. Resolve executable, GGUF and cwd
absolutely; run llama-server --version and --help first. Record only stage and
OS error code, not private paths, raw output or secrets. Check native DLLs and
architecture before model loading; then verify health and authenticated
/v1/models before chat completion. Errno 2 alone does not identify the cause.
