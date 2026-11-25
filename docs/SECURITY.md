# Security and trust boundaries

**TinyBuilder is experimental and is not an OS sandbox.**

- Local `write_file` requires `--allow-write`. Local `run_command` requires
  `--allow-exec`. Without `--exec-command` restrictions, execution permits
  arbitrary local argv commands under your current operating-system account.
- An exact argv allowlist restricts the launched process, **not** its scripts,
  imports, test hooks, or side effects. Only use trusted disposable worktrees.
- Path containment checks reject known traversal and symlink escapes but
  cannot eliminate filesystem races or replace OS-level isolation.
- Read-only local tools can read project files, including secrets. A remote
  or untrusted model server may receive those contents. Select projects and
  model endpoints accordingly.
- A configured MCP server is a separately trusted subprocess and may have
  capabilities beyond the local file/command flags. Strict-JSON mode has no MCP.
  Remote JSON-RPC error payloads are not copied into CLI exception messages;
  failed MCP handshakes should terminate the started child process.
- Structured actions are validated. Prose, fenced JSON, malformed or unknown
  tools must never become executable actions.
- Persistent SQLite memory contains only explicit user-owned preferences
  and decisions. Missing preference reads do not create a database.
- Sanitized verbose metadata excludes arguments, file contents and model
  responses, but normal chat output and retained local patches may still
  disclose project content. Review before sharing.
- The Laravel benchmark requires an explicitly marked, clean, disposable
  baseline. A passing mock test or evaluator-owned reference fix does not
  count as a model-generated Laravel success.

Never include `.env`, credentials, SQLite memory, model weights, hidden
benchmark values or private files in a release. Third-party model weights
carry separate licenses; TinyBuilder's MIT license does not grant model rights.

## Vulnerability reporting

Do **not** report credentials, working private-project exploits or sensitive
data in a public GitHub issue. Prefer GitHub's private vulnerability-reporting
option under this repository's Security tab **if available**. Otherwise ask
the maintainer for a non-public contact channel without exposing sensitive
details publicly. No formal penetration-test certification is claimed.

## Standalone preview release requirements (not yet verified)

The managed inference process must bind to loopback, authenticate the application client, avoid exposing credentials in diagnostics, and terminate only processes it owns. Loopback and authentication are not an OS sandbox or protection from all same-user processes. Project content and model output remain untrusted. Exact argv restrictions do not constrain behavior of an allowed executable or its children; use a disposable project and OS isolation where appropriate. Read-only does not mean secret-free or side-effect-free when optional MCP servers are configured.

The model downloader must require explicit consent, verify a pinned digest and byte count before use, and handle cancellation and incomplete files safely. A user-selected GGUF is not automatically a verified or licensed model. Never disable Gatekeeper, SmartScreen, antivirus or other OS protections to launch an unknown artifact. Verify published checksums and signing status; a checksum alone does not establish publisher identity. Do not share raw transcripts, source, absolute personal paths, environment variables, tokens, model weights, memory databases or private benchmark fixtures. Review sanitized logs before reporting bugs. See [standalone onboarding](STANDALONE.md) for reporting guidance. These requirements are not claims about the current source CLI.

### Managed-runtime and cancellation limits

The proposed pinned runtime exposes a public model-list endpoint; authentication must be verified against protected inference endpoints, not inferred from model discovery. Session bearer credentials are internal and must never appear in logs or bug reports. A loopback bind race and same-account hostile processes are outside portable containment guarantees. Windows direct-child termination and POSIX process groups are not complete hard-crash/descendant supervision. Cancellation may stop future actions without immediately interrupting a blocking network request or already-running child. Test these limits on the integrated candidate and do not promise instantaneous cancellation or universal cleanup.
