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


## Follow-up maintainer decision — 2026-11-27

The completed [exact-retrieval](https://github.com/MrPunyapal/TinyBuilder/blob/560e2ce7f04fb04fce288566cda5444a00232826/docs/research/2026-11-27-exact-retrieval-ablation.md)
and [source-ID](https://github.com/MrPunyapal/TinyBuilder/blob/560e2ce7f04fb04fce288566cda5444a00232826/docs/research/2026-11-27-source-id-comparison.md)
experiments justify retaining exact-text plus selective lexical retrieval as
the lab baseline; defer the tested line/source-ID representations. No
generalization or model reasoning claim from rejected previews. The highest
value prerequisite is live isolation qualification followed by broader
existing-model development evaluation. See the [Phase 2 maintainer decision](https://github.com/MrPunyapal/TinyBuilder/blob/74aba166d1ad38d87621b518638180fdfe85ae44/docs/research/2026-11-27-model-specialization-roadmap.md#maintainer-decision)
for candidate dossiers, hardware assumptions and training gates. This note
records maintainer direction, not user approval for downloads, training,
merging or release. Preserve the original archival research.
