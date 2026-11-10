# Training is optional

The runtime does not need Soup installed. `soup.yaml` is a small, unvalidated SFT recipe to start experiments; inspect the current [Soup docs](https://github.com/MakazhanAlpamys/Soup) before launching costly runs.

The two `sample-traces.jsonl` records are illustrative only. For meaningful training, collect tool-use trajectories with licensing/consent provenance, filter against successful test results, remove secrets and personal data, and hold out entire repositories/tasks for evaluation. Do not persist internet-retrieved documents in TinyBuilder's user memory. Training datasets are separate, explicitly curated research artifacts, and may contain only materials you have permission to use.

On a 4 GB RTX 3050, first run `soup profile --model Qwen/Qwen2.5-Coder-0.5B-Instruct`, then `soup doctor --config training/soup.yaml`, and validate an actual training run. Resource claims depend on driver, PyTorch build, model, sequence length and Soup version.
