# TinyBuilder product vision

TinyBuilder is a free, open-source, local-first coding assistant. Laravel/PHP
developers are the initial audience; other ecosystems should be supported by
plugins, not forks of the core.

## Product direction

- Prefer a lightweight terminal UI over a desktop shell initially. Keep the
  Rust core independent of the UI.
- Local coding-specialized small models provide reasoning, generation and
  repair. Select the smallest model meeting measured quality and hardware
  requirements, rather than promising frontier-level performance by size.
- Keep changing facts outside weights: opt-in documentation and web search
  providers, MCP, version-aware knowledge, skills and project guidelines.
  No mandatory paid APIs. External search access depends on provider terms.
- Keep temporary task context bounded and in memory. Persist only explicit
  project preferences as described in AGENTS.md; no remote-result or transcript
  caching. Never send project files or secrets to remote tools without consent.
- Use deterministic orchestration for reliable workflow steps and independent
  validation. Train stable coding skills and action selection where evidence
  supports it; do not encode permissions or security policy solely in weights.
- Keep editing and execution explicitly approved and contained. External
  content is untrusted data, not instructions.
- Target Windows x64, macOS ARM64 and Linux x64; measure actual end-to-end
  RAM, latency, VRAM and correctness on consumer hardware.

## Current boundary

0.1 remains native, read-only and offline-first, with an existing compatible
GGUF. No editing, execution, MCP, download or training additions in its
supported interface. Release remains subject to the existing contract.

The research track should compare ordinary prompts, deterministic workflow
assistance and, only after approval and a credible baseline, adapter tuning.
Do not equate success on narrow synthetic fixtures with general coding ability.
