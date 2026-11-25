# ADR — Shared standalone architecture

Status: accepted architecture decision; implementation and qualification pending.

Context: users should inspect local projects without installing a language runtime, inference server or developer tooling. Windows x64, macOS ARM64 and Linux x64 are first-class targets.

Decision: Python 3.12 orchestrates the agent, permissions, terminal UI and explicit preferences. A pinned, bundled llama.cpp server subprocess supplies local inference via an authenticated loopback API. GGUF models are selected independently, reused in place or downloaded with explicit consent and integrity verification. Use one shared application entry point, runtime manifest, model manager and inference adapter. Native packaging and process lifecycle adapters are platform-specific; CPU is the baseline and acceleration is optional. The source CLI remains available for contributors and externally managed compatible endpoints.

Trust boundaries: user -> shared terminal application -> agent policy/tools -> project; agent -> authenticated loopback runtime -> selected GGUF. Optional MCP subprocesses are separately trusted. SQLite stores only explicit preferences/decisions, not external observations or transcripts. No implicit paid API, training, model download or remote retrieval cache. No OS sandbox claim.

Alternatives: external Ollama as a mandatory dependency adds setup friction; in-process inference increases native ABI coupling and crash impact; separate platform implementations duplicate policy. The selected subprocess design incurs lifecycle, authentication, native build and resource-management costs. Textual is provisional; terminal accessibility and packaging must be demonstrated.

Native builds are required for PyInstaller if selected; minimum OS/glibc and CPU instruction requirements follow actual packaging evidence. Preserve third-party notices for Python, llama.cpp, packaging tools and bundled libraries. Verify the pinned components' actual license texts; model redistribution is separately authorized. Signing and notarization are independent release gates.

Primary guidance: [PyInstaller manual](https://www.pyinstaller.org/en/stable/), [llama.cpp license](https://github.com/ggml-org/llama.cpp/blob/master/LICENSE), [Apple notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution), [Microsoft SignTool](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool). The upstream moving documentation is guidance, not a pinned release manifest.

Acceptance: [release checklist](RELEASE_CHECKLIST.md). Do not infer standalone support from source CLI benchmarks.
