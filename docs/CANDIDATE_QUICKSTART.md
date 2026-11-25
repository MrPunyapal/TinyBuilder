# TinyBuilder 0.1 candidate — not qualified for public distribution

This unsigned experimental portable package contains the native Rust CLI and a
pinned llama.cpp runtime. No model weights or lab executables are included.
No Python, Rust, Ollama or Git is needed at run time on a compatible host.
OS/library prerequisites and clean-machine support are not yet established.

Extract the entire inner archive into a new directory (keep runtime next to
tinybuilder). Verify the archive SHA-256 against artifact.json from trusted CI.
Open a terminal in that directory. On Windows use .\tinybuilder.exe; on
macOS/Linux use ./tinybuilder. Run --version and doctor --project PATH.
Use read FILE --project PATH, search TEXT --project PATH or inspect QUESTION
--project PATH without a model. Run app to select a project and an existing
compatible GGUF; the bundled runtime is selected automatically. No downloads
are performed. Ask a question or use /cat, /search, /ask, /help, /quit.
Model quality is not qualified; verify all responses. No file editing or
command execution. Do not bypass OS security warnings; unsigned packages
are for controlled development testing only.

Exit with /quit. Remove the extracted application folder only, never your
project or separately stored model. No installer, signing, notarization,
clean-machine or independent redistribution approval is claimed.
See build.json and runtime/runtime-manifest.json for provenance and inventory.
