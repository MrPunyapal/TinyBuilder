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
