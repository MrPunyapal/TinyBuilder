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
operations are not race-proof, and metadata/ACL preservation requires native review. Hard-linked reads and updates are rejected; Unix ownership changes and special mode bits are rejected. The current Rust app deliberately does not replace the Python
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

## CI lab binaries

The Rust native workflow retains platform-specific lab binaries and build.json
with the tested checkout SHA, byte sizes and SHA-256 hashes. Verify all binary hashes before using them. They are not signed installers, do not include a model
or llama.cpp, and are not public-preview qualification. Use only a trusted
existing staged runtime with a reviewed manifest. The PR workflow's checkout
may be a merge test SHA; use a branch push run to obtain the exact branch head.

## Paired read diagnostics (experimental)

The Windows lab reported genuine reads but 0/10 exact two-fact answers. The
unpublished local fixes are not present in this branch. The baseline is kept
unchanged by default. To distinguish formatting and tool-loop failure from
model copying limitations, use diagnose_read with the same arguments as
qualify_read (optional --trials 1..10, default 3). Each randomized fixture is
shared by five randomly ordered arms: direct plain, direct final JSON,
baseline agent, split plain agent, split JSON agent. Direct controls do not
count as tool-selected reads. No real project or raw prompt/output is stored.
The report distinguishes wrong facts, formatting, protocol/transport failure,
actual read events, and request sizes. No automatic retries or output repairs.

The split candidate performs one constrained read selection, one actual file
read, and one fresh final-only completion. The answer phase has no tools or
citation mandate; the model output is scored verbatim. This is an experiment,
not a demonstrated improvement. After diagnostic evidence, run qualify_read
with --engine split-plain or --engine split-json on ten new fixtures. The exact
same task, oracle, required read and 10/10 threshold apply; the baseline remains
the default. Do not select the best of repeated qualification campaigns.

## Context-first natural-language workbench (experimental)

    cargo build --manifest-path rust/Cargo.toml --release --locked --example grounded_lab
    grounded_lab --project DISPOSABLE_PROJECT --runtime ABSOLUTE_RUNTIME --model EXISTING_GGUF ask "Locate and explain compute_total"
    grounded_lab --project DISPOSABLE_PROJECT --runtime ABSOLUTE_RUNTIME --model EXISTING_GGUF edit --allow-write "Fix compute_total to include tax"

The lexical retriever ranks filenames and up to four literal terms in one bounded traversal, reads up to four files, and flags incomplete evidence. There is no persistent
index and large files provide bounded matching excerpts with source line ranges. The ask path is
read-only, one completion with evidence; deterministic retrieval does NOT count
as a model-selected read qualification. The edit path accepts exactly one
model-generated replacement in a fully read file, binds proposals to the exact source hash and uses the existing diff/approval/patch engine. It never runs commands and does
not guarantee that a model proposal is semantically correct. Use disposable
projects only; ACL and extended attribute preservation remain unqualified.
No default CLI behavior changed. No real model trials were performed remotely.
