---
name: tinybuilder-model-research
description: Research small coding models, inference efficiency, data provenance, specialization and training feasibility for TinyBuilder.
---
# Model research

Read existing model and benchmark notes before surveying primary model cards,
papers, licenses and implementation code. Separate publisher results from
independently measured TinyBuilder results. Record exact candidate revision,
license, quantization, runtime/template support and whole-system resource
measurements. Do not rank untested models as winners. Existing 1.5B is a
baseline; existing research-license 3B is a control. Prefer qualified
permissively licensed weights for distribution.

Fix retrieval, protocol and evaluator problems before attributing failures to
model reasoning. Consider SFT/QLoRA only with reproducible failure evidence,
licensed verified data, lineage-disjoint holdout, untouched-base comparison,
regression tests and actual hardware profiling. No downloads, training or
paid compute without approval. Keep training tooling outside the product.
Never assume a GGUF file size equals RAM or proves training feasibility.
Use knowledge-maintenance to record findings and update decision guidance.
