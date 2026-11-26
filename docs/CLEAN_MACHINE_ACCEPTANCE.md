# Native clean-machine acceptance — release gate, not completed

Test exact successful candidate artifacts from the same Git commit on Windows
x64, macOS ARM64 and Linux x64 separately. Use a fresh VM/physical test host
with the claimed OS baseline and no Python, Git, Ollama or Rust installed for
the product test. Do not disable OS protections or use untrusted model files.
Unsigned CI archives are development-only; no signing approval implied.

## Manual product run

1. On a trusted download machine, obtain the matching GitHub Actions artifact
   and inner portable archive and artifact.json. Verify archive SHA-256, source
   commit, target and size; preserve a copy of the original archive.
2. Copy to the clean host along with one separately vetted permissively licensed
   existing GGUF (exact hash, bytes, license, immutable revision). No downloads
   on the clean host. Disable network connectivity; loopback must still work.
3. Extract into a new directory, verify files against build.json, and retain
   runtime beside the executable. Verify version, doctor and runtime inventory.
   Note any OS security prompt, loader error, missing library or unsupported CPU.
4. Launch with no arguments, choose a disposable project outside the package,
   leave model blank, exercise /cat, /search, /inspect, /help and /quit. Check
   source bytes and file inventory unchanged. Verify mutation/exec options
   rejected. Repeat with paths containing spaces and a non-system drive or
   directory where available.
5. Load the verified GGUF with /model. Record real inference startup, genuine
   read events and exact hidden facts, no network activity, RAM and latency.
   Exercise normal exit and forced parent exit; use the OS process/listener
   tools to verify no runtime child or loopback listener remains.
6. Remove only extracted application folder; verify external project and model
   hashes unchanged. Record unsupported functionality explicitly.
7. Record actual OS version, CPU, RAM, runner identity, commit, artifact SHA,
   runtime archive/manifest digests, model SHA/size/license, measured outcomes
   and reviewer. CI alone cannot clear this gate.

## Packaged CLI qualification

On a separate evaluator machine or after the clean-host product test, use
Python 3.12+ only for the evaluator, not the app. Copy the exact package and
trusted artifact.json. The evaluator runs actual shipped executable, starts
a fresh model process per trial, and uses the unchanged hidden two-fact task.
Use only a vetted existing GGUF and reviewed patched runtime. No model download.

    python acceptance/qualify_packaged_read.py --package-root EXTRACTED_APP --archive INNER_ARCHIVE --artifact-json ARTIFACT_JSON --expected-commit FULL_SHA --model EXISTING_GGUF --expected-model-sha256 SHA256 --output NEW_REPORT_DIR

Preselect this engine and model before the campaign. Keep all failures, including
unattempted trials after a safety/transport stop. The report contains counts
and digests, not prompts, responses or hidden fixture values. No auto retries.
10/10 exact facts with genuine reads and unchanged model/package/project is
required; report is not evidence of general coding ability. The existing
rust/examples/qualify_read.rs remains the separate unchanged lab oracle.
If baseline diagnostics select a different engine, make that engine explicitly
available in the shipped CLI and rerun the shipped workflow rather than
counting lab/direct controls as product passes.
