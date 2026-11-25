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
  an explicit alternate drive. Choose an existing directory on an attached
  volume for removable storage. The nearest existing ancestor is pinned by
  filesystem identity; if it disappears or is replaced during the manager's
  lifetime, operations fail closed. Re-select the directory after remount.
  Construction, catalog inspection, status and local selection make no
  network requests.
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
- download_offer(model_id): immutable ModelOffer containing full CatalogEntry and
  destination, no writes or network. This display-only type cannot be passed
  directly to download().
- request_download(model_id, consent=True, expected=offer): bind the displayed identity after explicit consent; a mismatch requires fresh consent. Show model ID, revision, filename, source URL, exact bytes, license, digest and destination. The expected argument is optional for adapters independently comparing every field; download validates the full request again.
- download(request, progress=callback, cancellation=token, retries=2):
  synchronous worker operation; callback receives DownloadProgress with
  received_bytes, total_bytes and phase (downloading/verifying/complete).
  CancellationToken.cancel() is thread-safe; checked between chunks and
  during verification. Socket reads can block up to the configured timeout
  (default 15 seconds); DNS resolution can take longer.
- discard_partial(model_id, consent=True): explicitly discard owned partial
  bytes and transfer metadata; never touches the final model. Use when a
  server keeps returning invalid ranges or the user wants to free space.
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
atomically without clobbering: Windows rename, Linux renameat2 with
RENAME_NOREPLACE, macOS renamex_np with RENAME_EXCL. If the POSIX exclusive
rename primitive is unavailable, hard link then unlink is the fallback.
Volumes that support neither fail closed; external GGUF reuse still works.
A crash between fallback link and unlink can be recovered explicitly using
recover_publication after full verification. Native primitive references:
https://man7.org/linux/man-pages/man2/renameat2.2.html
https://developer.apple.com/documentation/foundation/urlresourcekey/volumesupportsexclusiverenamingkey

The directory is trusted user-controlled storage, not an OS sandbox;
hostile concurrent directory replacement by the same local account cannot
be fully prevented by portable path checks.

HTTPS is required except for explicitly enabled loopback fixtures. Redirect
downgrade is rejected. A partial is resumed only with a strong ETag, matching
source/digest, exact effective URL fingerprint, exact 206 Content-Range and
length. Signed URL rotation can prevent resumption; a valid 200 response
restarts from zero rather than appending. No validator means a fresh transfer.
A malformed 206 fails closed rather than appending. The caller can retry
after the resource returns a valid full response, or explicitly discard the
partial before starting a fresh authorized download. Interrupted transfers retain
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

## HQ review follow-up

- recover_publication(model_id, consent=True): offline repair of an interrupted
  fallback hard-link publication. The final and partial must be exactly two
  regular links to the same inode and the full digest and length must match.
  No directory or final file is deleted. External third links are rejected.
- download_offer returns a description, not a security capability. The TUI
  must obtain consent; request_download accepts expected=offer and download
  revalidates all fields. The existing PR #3 adapter at b5aa4bc44f45aaacb86cb4c12d492c0f8510cc90
  has compatible check()-only cancellation and received_bytes/total_bytes
  progress, but must expose and bind source, revision and filename too.
- Known invalid HTTP completion is discarded instead of promoted on retry.
  Storage identity is rechecked before operations and after network response.
  Publication is a commit point; cancellation afterward does not undo it.
- The new forced-exit test kills a subprocess holding the actual OS lock,
  then resumes the partial. Native matrix owner PR #6 should run the model
  suite on Windows x64, macOS ARM64 and Linux x64 from combined checkout;
  report skips separately. Physical removable-volume tests are still needed.
  No default until PR #9 qualifies a candidate.
