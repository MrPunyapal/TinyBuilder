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
then terminates the owned server tree. A failed cleanup retains the handle for retry.
The startup timeout covers HTTP readiness after spawn, not file hashing or OS
process creation. Cancellation during those operations is cooperative.
Credentials are random, per-session, passed via LLAMA_API_KEY in the child
environment, not argv. Do not serialize dataclasses or retain connection after
stop. The credential is not protection against other processes under the same
OS account.

## Packaging contract

Use installed_runtime_root(absolute_installation_root) to resolve the explicit\nlauncher-provided installation root / runtime. It never discovers from project\ncwd, PATH, sys._MEIPASS or an implicit executable location. App #3 can pass\nthat absolute result to ManagedServices.from_installation(runtime_root, approve).\nPackaging #4/#5/#8 own the explicit installation root and final staged bytes.\n\nSupply a flat runtime directory (as staged by Linux/macOS packaging) containing
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
public health plus public /v1/models random alias match, then protected /props
rejection of absent and invalid bearer keys and acceptance of the session key.
The pinned b6500 server intentionally makes /v1/models public; it cannot be
used as an authentication test. The temporary free-port selection has an unavoidable bind race;
fail closed for unexpected replies and never kill another process. A hostile
local process could impersonate the server, including capturing a key during
that race; this is not an OS sandbox. A child exit during startup is classified
as server_crash with readiness stage and numeric exit code, not guessed to be a
loader, bind or model error. RuntimeFailure and RuntimeStatus expose optional
stage, os_code and exit_code; OS errors from process creation are distinguished
from known loader-format failures. POSIX shell status 126/127 is not proof of
a loader cause. No raw output is retained. Raw server
output is discarded, not written to disk. No arbitrary extra flags, no web UI
or slots, no server-side tool execution enabled by this pinned server. Native
tool call formatting uses Jinja; TinyBuilder still authorizes and runs tools.

CPU uses --device none and zero GPU layers. CUDA/Vulkan/Metal/ROCm are reserved
backend names, deliberately rejected with cpu_recovery=True pending separately
qualified payloads and hardware detection. No silent fallback or downloads.

Windows uses absolute executable and trusted cwd with a restricted PATH based
on the OS Windows-directory API, not inherited SystemRoot. Runtime paths
containing the platform search-path separator are rejected.
POSIX uses a new process session and bounded TERM/KILL; Linux limits
LD_LIBRARY_PATH to the trusted runtime, macOS requires verified install names
and rpaths. These measures are not a complete native loader sandbox. Windows uses an unnamed non-inheritable Job Object with KILL_ON_JOB_CLOSE,
assigned immediately after Popen. It fails closed if assignment fails (e.g.
incompatible enclosing job). There is a launch-to-assignment race; atomic
STARTUPINFOEX job assignment is not implemented. TerminateJobObject and
accounting plus direct child wait bound ordinary cleanup; native nested jobs
and descendant handle-signaling need platform acceptance.
POSIX launches a fixed /bin/sh supervisor in a fresh session. The private
parent pipe closes on parent exit; the supervisor sends TERM then KILL to its
own group while it remains group leader. The native child receives no pipe
handles and its output is discarded; only a bounded numeric shell exit status
is returned. Descendants deliberately escaping the session/group, kernel
uninterruptible processes and system crashes are outside the guarantee.
Actual target OS tests are required; atexit alone is not a hard-crash solution. Application must use finally
or context manager for normal exits. A stop after failed cleanup can be retried.

Actual target binaries, OS loader dependencies, minimum OS/CPU features,
authentication and native inference with a real GGUF require local validation.
No baseline CI model downloads.

## Windows diagnostic handoff

Do not change the uncommitted installer. Resolve executable, GGUF and cwd
absolutely; run llama-server --version and --help first. Record only stage and
OS error code, not private paths, raw output or secrets. Check native DLLs and
architecture before model loading; then verify health, public alias and authenticated /props before chat completion. Errno 2 alone does not identify the cause.

## Shared schema fixture and qualification

For synthetic tests only, create an empty temporary installation directory with
runtime/ containing llama-server (Windows: llama-server.exe) and LICENSE,
write arbitrary fixture bytes to both, then:

    from tinybuilder.runtime import installed_runtime_root, manifest_fields
    from tinybuilder.runtime.manifest import platform_key, resolve_runtime
    import hashlib, json
    root = installed_runtime_root(absolute_installation_root)
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()}
    (root / "runtime-manifest.json").write_text(json.dumps(manifest_fields(platform_key(), files, [])), encoding="utf-8")
    assert resolve_runtime(root, "cpu").is_absolute()

Do not execute fixture bytes. manifest_fields is a pure schema constructor,
not an archive verifier: packaging must independently authenticate source
archives and final staged files before generating the production manifest.
Linux #4 already uses the same field names and flat layout. macOS #5 and
Windows #8 must reconcile signing/manifest generation and launcher root.
Model qualification #9 confirms the b6500 architecture registry contains
qwen2, qwen3 and phi3; Qwen3.5 is excluded. Architecture presence does not
establish actual GGUF/template compatibility. No silent revision change.

Model-free native qualification: verify archive SHA-256, enumerate ZIP members,
check architecture and dependencies, run staged server --version and --help
from an unrelated cwd, then run tests/test_runtime_processes.py on each target.
See packaging owner smoke scripts. No real archive bytes or models were
available in the connector-only environment. Windows Errno 2 remains local.
Official Windows Job Object reference:
https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects
