# Model management (PR 2)

The standard-library package tinybuilder.models is independent of the runtime,
inference client, TUI and SQLite. Python 3.10+ is supported. The application
owner should include this Python package in all standalone builds (no JSON
resource or extra package dependency is needed). No changes to packaging or
CI metadata are made here.

## Integration

- CATALOG: immutable tuple of CatalogEntry values, with model_id, revision,
  size_bytes, sha256, license, filename, source_url and qualification.
- native_model_dir(): Windows LocalAppData/TinyBuilder/models, macOS
  ~/Library/Application Support/TinyBuilder/models, Linux
  $XDG_DATA_HOME/tinybuilder/models or ~/.local/share/tinybuilder/models.
- ModelManager(storage_dir=None): uses a canonical absolute root, including
  an explicit alternate drive. Construction, catalog inspection, status and
  local selection make no network requests.
- destination(model_id): absolute planned path, without creating it.
- select_local(path): returns ModelSelection(path, catalog_id, managed,
  provenance). Checks a minimal GGUF header and compares size/digest against
  catalog entries. A user-provided file is not copied or made deletable.
  Neither header nor digest implies the pinned llama.cpp can load it.
- status(model_id): MISSING, PARTIAL, VERIFIED or INVALID. Verification hashes
  the entire file; run on a worker. verified_path(model_id) performs offline
  integrity validation and returns the absolute managed file path.
- check_space(model_id): SpaceCheck(required_bytes, free_bytes, sufficient);
  conservative full-size estimate, no mutation. The actual transfer checks
  remaining space and checks full space if the server restarts.
- request_download(model_id, consent=True): construct the request only after
  showing source, license, exact bytes and destination and obtaining consent.
- download(request, progress=callback, cancellation=token, retries=2):
  synchronous worker operation; callback receives DownloadProgress with
  received_bytes, total_bytes and phase (downloading/verifying/complete).
  CancellationToken.cancel() is thread-safe; checked between chunks and
  during verification. Socket reads can block up to the configured timeout
  (default 15 seconds); DNS resolution can take longer.
- delete_managed(model_id, consent=True): deletes only the verified managed
  file, not external selections, invalid files, or other directory contents.
  Returns whether a file was removed. Stop runtime before deletion or model
  switching; the manager does not own runtime leases.

Example flow: show manager.catalog and manager.destination(entry.model_id),
call manager.check_space, prompt for approval, then construct a download
request. Pass the returned selection.path to the runtime. Alternatively call
manager.select_local on the user's chosen file. Switching is selection, not
copying or moving models. Application owner persists only explicit model path
and storage choices in separate application configuration, not SQLite; no
configuration writes or implicit downloads occur in this package.

## Candidate provenance

Qwen2.5-Coder-1.5B-Instruct Q4_K_M remains provisional, with no default model.
The official upload commit's Git LFS pointer establishes 1,117,320,768 bytes
and SHA-256 cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046:
https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/commit/2ab9f8f42af02fc212effaef7c4850c885e965f4
The official model card/file page declares Apache-2.0:
https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/blob/main/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf
No weights were downloaded and no runtime qualification is claimed. The
benchmark owner must assess candidates independently.

## Security and recovery

Catalog IDs and filenames are constrained to portable safe names. A separate
digest-namespaced directory with ownership marker isolates managed files.
Links, Windows reparse points and multiply linked managed files are rejected.
An OS advisory lock serializes downloads and deletion; locks release when the
process exits. Lock files remain, and unrelated files are not removed.
Existing final files are never overwritten. Verified bytes are published
atomically without clobbering: Windows rename, POSIX hard link then unlink
the partial. POSIX volumes that do not support hard links fail closed; an
existing external GGUF on such a volume can still be selected. A crash
between link and unlink can require manual recovery after verifying the
digest. The directory is trusted user-controlled storage, not an OS sandbox;
hostile concurrent directory replacement by the same local account cannot
be fully prevented by portable path checks.

HTTPS is required except for explicitly enabled loopback fixtures. Redirect
downgrade is rejected. A partial is resumed only with a strong ETag, matching
source/digest, exact effective URL fingerprint, exact 206 Content-Range and
length. Signed URL rotation can prevent resumption; a valid 200 response
restarts from zero rather than appending. No validator means a fresh transfer.
A malformed 206 fails closed rather than appending. The caller can retry
after the resource returns a valid full response. Interrupted transfers retain
partial bytes, cancellation never publishes an incomplete file, and exact
length plus SHA-256 are checked before publication. Invalid checksum partials
are removed, while invalid existing final files are preserved for explicit
manual inspection. No credentials, prompts, source files, MCP observations or
transcripts are stored. No automatic background operations are scheduled.

## Verification

Run python -m unittest discover -s tests -p test_model_manager.py -v and
python -m unittest discover -s tests -v. Fixtures are small and use only
loopback HTTP. Native Windows/macOS/Linux filesystems and actual external
volumes still need acceptance checks; baseline CI is Linux only.
