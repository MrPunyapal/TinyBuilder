# TinyBuilder local release validation — 2026-11-13

## Gate result: FAILED

The local runtime, project tools, deterministic tests, Laravel controls, and
health/repair scenarios worked. The release gate remains failed because the
validation-change scenario passed 0/3 trials with Qwen2.5-Coder 3B, and model-
driven Laravel Boost discovery made no MCP tool call. These are observed model
capability failures; the fixture and hidden acceptance checks were not relaxed.

## Environment

- Windows 11 Home, build 26300; Intel Core i7-12700H; 15.60 GiB RAM.
- Python 3.12.14 in the repository virtual environment.
- PHP 8.5.12; Composer 2.11.1; Ollama 0.32.5.
- Disposable Laravel 13.42.0 project with Laravel Boost 2.10.4.
- The local Ollama endpoint responded. The tested Qwen2.5-Coder model tags were
  already installed; no model weights were downloaded during this validation.
- A post-run snapshot showed Ollama's 3B model using 2.2 GB, GPU placement 100%,
  NVIDIA memory 2,151/4,096 MiB, and 0.50 GiB free system RAM. This is a point
  in time, not a peak measurement.

## Software checks

- `python -m unittest discover -s tests -v`: **98 passed**.
- `python -m compileall -q tinybuilder benchmarks`: passed.
- `python -m tinybuilder doctor --project .`: passed; this repository itself is
  not a Composer/Laravel project, as expected.
- Doctor against the marked disposable Laravel project and MCP configuration
  found Composer dependencies, Laravel Boost, and the config.
- Disposable Laravel baseline: PHPUnit/Pest runner, **2 passed**; clean Git
  status before and after repeated evaluations.
- The validation harness controls passed against real Laravel/PHP: broken
  reference failed, hidden negative control failed, visible negative control
  failed, and the reference repair passed the complete hidden suite. The
  expected POST route was registered. Hidden checks covered invalid/missing
  email, short message, exact success JSON, home route, and an unrelated route.
- A Windows CRLF-preservation bug in the reference fixture was corrected and
  given a regression test. Evaluator project subprocesses now explicitly use
  `shell=False`, also covered by regression tests.

## Model evidence

All listed model evaluations used Ollama locally, the opt-in strict JSON
protocol, constrained profile, randomized hidden fixture data, and observable
tool-event reports. Facts are aggregate outcomes; random names and project
contents are intentionally omitted.

| Model/task | Trials | Actual required tool use | Correct result | Outcome |
|---|---:|---:|---:|---|
| Qwen2.5-Coder 0.5B, Composer inspection | 3 | 0/3 `read_file` | 0/3 | 0/3 passed; no tool call |
| Qwen2.5-Coder 1.5B, Composer inspection | 3 | 3/3 `read_file` | 1/3 | 1/3 passed; two factual failures |
| Qwen2.5-Coder 3B, health endpoint | 3 | 3/3 required reads and writes | 3/3 | 3/3 passed |
| Qwen2.5-Coder 3B, broken-route repair with sibling preservation | 3 | 3/3 required reads and writes | 3/3 | 3/3 passed |
| Qwen2.5-Coder 3B, request-validation change (plain prompt) | 3 | 3/3 required reads; in-scope writes | 0/3 | 0/3 passed |
| Qwen2.5-Coder 3B, request-validation change (checklist guidance) | 3 | 3/3 required reads; in-scope writes | 0/3 | 0/3 passed |

The 0.5B inspection trials took 3.203, 2.094, and 0.594 seconds (mean 1.96s).
The 1.5B trials took 10.172, 1.328, and 1.640 seconds (mean 4.38s). The
validation task's unguided outputs failed PHP parsing. Checklist outputs either
failed parsing or had an invalid request-argument signature and/or an exact
command rejected by the configured allowlist. These failures occurred despite
passing real-Laravel reference controls. The evaluator did not loosen the
allowlist or acceptance tests to make the runs pass.

The 3B health and repair campaigns each used three paired trials with matching
hidden fixture inputs between prompt conditions. Both conditions passed all
three trials for both scenarios. The validation campaign's reference controls
were re-run after simplifying the reference fixture's request handling; hidden
acceptance assertions were unchanged, and model success remained 0/3 in each
condition.

## Laravel Boost MCP

- Direct MCP bridge initialization discovered **9 tools**.
- Direct read-only calls to a project-information tool and the documentation
  search tool both returned successfully. Documentation output was consumed
  transiently and was not saved.
- A TinyBuilder model-driven chat connected to all nine tools but issued **zero
  tool calls** and guessed a nonexistent tool name in text. Therefore Boost MCP
  transport/discovery works, but model-guided MCP use is **not validated**.

## Reproduction

Run from the repository root in PowerShell, with the listed local dependencies
already installed. These commands use fresh output directories. The Laravel
baseline must be an explicitly marked disposable Git project.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q tinybuilder benchmarks
.\.venv\Scripts\python.exe -m tinybuilder doctor --project .

$smoke = Join-Path $env:TEMP ('tinybuilder-smoke-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py --tool-protocol strict-json `
  --strict-json-profile constrained `
  --models qwen2.5-coder:0.5b qwen2.5-coder:1.5b `
  --trials 3 --output $smoke

$app = '<path to the explicitly marked disposable Laravel baseline>'
$health = Join-Path $env:TEMP ('tinybuilder-health-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py --tool-protocol strict-json `
  --strict-json-profile constrained --models qwen2.5-coder:3b `
  --trials 3 --laravel $app --output $health

$validation = Join-Path $env:TEMP ('tinybuilder-validation-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py --tool-protocol strict-json `
  --strict-json-profile constrained --progress-guidance checklist `
  --scenario validation --models qwen2.5-coder:3b --trials 3 `
  --laravel $app --output $validation
```

The harness emits per-trial JSON containing timing, tool-call validity, factual
result, and failure category. It returns a nonzero status when task acceptance
fails; that is expected for the failed model trials above.

## Remaining blockers

1. 0.5B did not invoke the required inspection tool in any trial.
2. 1.5B invoked the inspection tool in all trials but returned correct facts in
   only one.
3. 3B did not reliably produce a valid request-validation endpoint under the
   exact safe command allowlist, even with checklist guidance.
4. Boost MCP transport works, but the model did not select/call an MCP tool.

No model training, fine-tuning, Soup training, paid inference, or persistent
storage of project/MCP/documentation content was used.
