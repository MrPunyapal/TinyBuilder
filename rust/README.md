# TinyBuilder native Rust rewrite (draft)

This is a separate executable, not a Python extension. The original Python
implementation and benchmark history remain available for regression and
rollback. No Python, Git or Ollama is required to run the Rust CLI itself.
A trusted native llama.cpp runtime and an existing GGUF are required for AI.
The public preview remains on hold.

## Build and try

From the repository root, on a native supported builder:

    cargo test --manifest-path rust/Cargo.toml --locked
    cargo build --manifest-path rust/Cargo.toml --release --locked

The CI-generated lock is committed and builds require it. Full dependency security and license review remains a release gate; no release artifacts are published.

    rust/target/release/tinybuilder doctor --project .
    rust/target/release/tinybuilder read README.md --project .
    rust/target/release/tinybuilder search TinyBuilder --project .
    rust/target/release/tinybuilder app --project PATH --runtime ABSOLUTE_RUNTIME --model EXISTING_GGUF
    rust/target/release/tinybuilder chat "Explain this project's structure" --project PATH --runtime ABSOLUTE_RUNTIME --model EXISTING_GGUF

Use tinybuilder.exe on Windows. The app defaults to native tools; /strict is
explicit session consent to experimental constrained JSON. /write applies
to the next model task only; every exact replacement requires human approval.
Commands are not implemented in this draft. /read requests an AI-assisted read with a required file and one-time strict JSON consent. /cat is deterministic display and never counts as model qualification.

## Implemented

- Bounded UTF-8 reads, ignore-aware discovery, Rayon parallel literal search.
- Exact unique replacements, reviewable diffs, stale-content SHA-256 checks,
  temporary file in the same directory and atomic replacement.
- Typed native/strict actions, bounded rounds and context, required genuine
  read evidence, refusal of early answers, sanitized terminal rendering.
- Managed CPU llama.cpp loopback startup with random alias and key, authenticated
  readiness, runtime manifest and inventory checks, owned runtime cleanup through Windows Job Objects and a POSIX parent-pipe supervisor.
- Native CLI, guided line session, model-free smoke and unit tests.

## Not yet complete or qualified

Both b6500 and b12359 official CPU asset metadata are supported in the schema-1 manifest. b12359 archive digests come from the official GitHub release API; flags and authenticated models endpoint were checked against upstream tag source. The unpublished local lab manifest is unavailable and no actual runtime or model execution has been verified.
The runtime manifest checks consistency with a trusted installation; it cannot
authenticate a manifest and binaries supplied by an attacker together.

Full rewrite parity remains open: native process ownership acceptance (including Windows spawn-to-assignment hardening), cancellation/streaming, secure model catalog and resumable consented
downloads, persistent explicit preferences, MCP and approved exact-argv command
execution, creation of new files, installer packaging, and independent Rust
benchmark/clean-machine acceptance. No training or weights are downloaded.
Writes are existing text files only; this is not an OS sandbox, filesystem
operations are not race-proof, and metadata/ACL preservation requires native review. Hard-linked updates are rejected; Unix ownership changes and special mode bits are rejected. The current Rust app deliberately does not replace the Python
installer or claim compatibility with the unpublished Windows prototype.

Native tool arguments require a single OpenAI string-shaped call per round.
Constrained JSON is opt-in. Model claims still require independent evaluation;
a successful file read is not proof the answer is correct.

## Performance experiment

Measure warm and cold read/search/patch operations on identical disposable
trees against the Python baseline, verify output equivalence and report
p50/p95 latency and peak RSS separately from model inference. Include Windows,
macOS and Linux, ignore behavior, Unicode paths and stale-patch rejection.
Do not claim speedup before measurements. Qualify a suitably licensed model
with ten fresh independent read trials before public preview; editing requires
separate independent gates.

No release, merge, new model downloads or local prototype modification is
authorized by this draft.

## Local offline read qualification

Build with Rust 1.88 or later; native CI tests the declared minimum. Select an
existing trusted runtime manifest and an existing GGUF. The model SHA-256 must
be supplied explicitly from verified local/publisher evidence. This example
starts one CPU runtime and runs ten disposable independently randomized
pyproject.toml name/description reads, records only sanitized results, and
requires exact answers plus actual file read evidence and no writes. It is a
new Rust-specific profile, not directly comparable to historical Composer
scores. No retries after a failed trial and no downloads. Exit 1 means failure.

    cargo build --manifest-path rust/Cargo.toml --release --locked --example qualify_read
    rust/target/release/examples/qualify_read --runtime ABSOLUTE_RUNTIME --model EXISTING_GGUF --expected-sha256 EXPECTED_HASH --output NEW_REPORT_DIRECTORY

On Windows use qualify_read.exe. Existing research-license models are lab only.
A passed campaign is not installer, license, edit, or general coding qualification.
