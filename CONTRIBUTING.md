# Contributing

TinyBuilder is intentionally an experiment. Favor reproducible tests, constrained actions and benchmark evidence over claims of capability. Open an issue describing desired changes; keep pull requests focused and include `python -m unittest discover -s tests -v` output. Do not commit model weights, API keys, personal data, downloaded documentation caches, or unlicensed training traces.

## Reproduce before changing behavior

Use Python 3.10+ and run `python -m pip install -e .`,
`python -m unittest discover -s tests -v`, and
`python -m compileall -q tinybuilder benchmarks`.
Tests must be deterministic and must not download models or run Laravel.
For issues involving real inference/PHP behavior, report sanitized local
results separately; mocks do not count as real model-generated edits.

See the [quick start](docs/QUICKSTART.md),
[security guidance](docs/SECURITY.md), and
[release checklist](docs/RELEASE_CHECKLIST.md) before proposing release changes.
