# Coding Intelligence v1 maintainer decisions

## Scope of this review

PR #21 archives the complete Deep Research report and its planning material for
documentation approval. Native Rust 0.1 requirements take precedence over the
archival Python wording. The supported 0.1 CLI remains read-only, with release
contingent on its unchanged qualification oracle and clean-machine
acceptance. Coding experiments stay outside the shipped product. [Release
contract](../RELEASE_0_1.md) · [Clean-machine acceptance](../CLEAN_MACHINE_ACCEPTANCE.md)

## Accepted direction

- Extend the existing Rust core and llama.cpp runtime. Prioritize reproducible
  headless evaluation before the lightweight TUI.
- Keep the approved 1.5B weights as the low-resource baseline and the existing
  3B research weights as a comparison control. Granite 4.2-3B, Qwen3.5-4B and
  Phi-4-mini remain candidates pending separate qualification.
- Measure selective lexical and then bounded structural retrieval before
  considering embeddings or persistent indexes. Keep Laravel conventions
  behind an ecosystem extension boundary.
- Compare edit representations with the same tasks and evidence. A model
  chooses its own target in the primary experiment. Bind proposals to complete
  source revisions and keep application subject to explicit approval.
- Score independently with behavioral and regression checks. Keep failed
  trials in the record and reserve repository lineages for holdout.

## Open research decisions

Retrieval parsing dependencies, patch representations, context budgets and
numerical promotion thresholds need measured evidence. Defer model downloads
and training. The first measured experiment compares patch location selection
and lexical context selection separately.
