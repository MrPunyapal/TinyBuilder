# TinyBuilder Local Codex Validation — 2026-11-15

## Outcome

TinyBuilder ran locally against Ollama and made genuine, observable tool calls. The read-only Laravel inspection task passed all recorded trials. Qwen2.5-Coder 3B did **not** complete a validated Laravel repair in any trial. This is not a release pass.

The 12-round comparison completed with matched fixture inputs and `paired_inputs: true`. The requested 8-round comparison is incomplete: the base arm finished 3 trials, while the checklist arm has 2 saved trials because the user asked to pause while trial 3 was beginning. `compare.py` correctly rejected those incomplete inputs. No 8-round paired result is claimed.

## Repository and Python verification

- Branch: `main`
- Starting and validation-source ending commit: `a75b52787790fd5ce7cefce25d552437bb48b9ae` (this SHA identifies the code under test; the sanitized report is a separate artifact).
- TinyBuilder working tree was clean at start. No source changes or fixes were justified; this report is the only new repository file.
- Editable install in `.venv`: passed.
- `python -m unittest discover -s tests -v`: 113 tests passed.
- `python -m compileall -q tinybuilder benchmarks`: passed.
- `python -m tinybuilder doctor --project .`: passed; the repository root is not itself a Laravel project.

## Local environment

- Windows 11, build 26300; Intel Core i7-12700H; 15.63 GiB visible RAM.
- Python 3.12.14; Git 2.45.2; Ollama 0.32.5.
- PHP 8.5.12; Composer 2.11.1.
- NVIDIA GeForce RTX 3050 Laptop GPU, 4 GiB VRAM.
- Disposable Laravel fixture: Laravel Framework 13.42.0 with Laravel Boost 2.10.4.
- Evaluated model: `qwen2.5-coder:3b` (Ollama reports 2.2 GB model size, GPU placement, 4096 context).

During the final resource snapshot, Ollama still had the 3B model loaded; the GPU showed 2,151 MiB used and 1,812 MiB free. Windows reported 0.47 GiB free RAM. These are point-in-time readings, not measured peaks. The original marked candidate directories were not suitable clean baselines, so the Laravel tests used a newly created disposable project under the OS temp directory. No personal or production project was used.

## Laravel baseline, controls, and Boost MCP

- Installed the disposable Laravel dependencies and Boost using Composer and Boost's installer; the original Laravel test suite passed (2/2).
- `tinybuilder doctor` recognized Laravel 13.42.0 and Boost 2.10.4.
- Three independent validation `--controls-only` runs passed. The per-trial reference controls also passed in all recorded 8-round and 12-round Laravel trials. Controls verified baseline tests, negative tests, reference repair, route registration, restoration, and unchanged protected `.env` state.
- Boost MCP initialized and discovered two configured read-only tools. A direct read-only `database-connections` call succeeded; its returned content was discarded and not recorded.
- Native model-driven Boost MCP did **not** pass: the 3B model produced no actual MCP invocation in 3 trials. Mentioning a tool in model text was not counted as tool use.

## Model results

All recorded smoke inspections used a random package name not supplied in the prompt. Results below require observable tool events, not plausible prose.

| Budget / prompt | Complete trials | Read-only smoke | Laravel repair | Route registered | Changed PHP lint | Successful test commands | Reference controls |
|---|---:|---:|---:|---:|---:|---:|---:|
| 8, baseline | 3 | 3/3, factual; real `read_file` | 0/3 | 0/3 | 0/3 | 0 | 3/3 |
| 8, checklist | 2/3 | 2/2, factual; real `read_file` | 0/2 | 0/2 | 0/2 | 0 | 2/2 |
| 12, baseline | 3 | 3/3, factual; real `read_file` | 0/3 | 1/3 | 1/3 | 0 | 3/3 |
| 12, checklist | 3 | 3/3, factual; real `read_file` | 0/3 | 1/3 | 1/3 | 0 | 3/3 |

The 12-round `compare.py` output was:

```text
paired_inputs: true
trials: 3
smoke: baseline 3/3, checklist 3/3, delta 0
Laravel: baseline 0/3, checklist 0/3, delta 0
```

Every Laravel run kept changes within the intended project scope and left `.env` unchanged. No model test command completed successfully. In the 12-round runs, two of three changed PHP outcomes per arm failed PHP lint; the remaining lint-clean change in each arm still failed independent acceptance. The 8-round base's three changed PHP outcomes and the two saved guided outcomes all failed PHP lint. Every base Laravel task failure was classified as execution; guided 12-round failures were two execution and one permission denial. No validated write is claimed.

The errors are consistent with model-generated code/task failures, not an Ollama transport or general tool-dispatch outage: inference completed, valid `read_file` calls were observed, `write_file` calls changed only allowed files, and unsafe/invalid command attempts were denied by the permission boundary. The 12-round checklist did not improve the measured repair pass rate. One 8-round campaign also stopped on a reference-control error; exact control replay and three subsequent standalone control runs passed, so control stability should be investigated before treating future 8-round comparisons as reliable.

## Exact reproduction commands

These commands reproduce the test shape with a fresh fixture seed and fresh output directories. `$app` must point to a marked disposable Laravel project. The original randomized seed and temporary worktree names are intentionally not recorded.

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py -m pip install -e .
& $py -m unittest discover -s tests -v
& $py -m compileall -q tinybuilder benchmarks
& $py -m tinybuilder doctor --project .

$app = 'C:\path\to\marked-disposable-laravel'
$phpExe = php -r 'echo PHP_BINARY;'
$env:PATH = (Split-Path $phpExe) + ';' + $env:PATH
$controls = Join-Path $env:TEMP ('tb-controls-' + [guid]::NewGuid().ToString('N'))
& $py benchmarks\evaluate.py --scenario validation --controls-only `
  --laravel $app --php $phpExe --preserve-sibling-route --output $controls

$seed = [guid]::NewGuid().ToString('N')
$base = Join-Path $env:TEMP ('tb-validation-base-' + [guid]::NewGuid().ToString('N'))
$guided = Join-Path $env:TEMP ('tb-validation-guided-' + [guid]::NewGuid().ToString('N'))
$common = @('--scenario','validation','--preserve-sibling-route',
  '--models','qwen2.5-coder:3b','--tool-protocol','strict-json',
  '--strict-json-profile','constrained','--trials','3',
  '--fixture-seed',$seed,'--laravel',$app,'--php',$phpExe)

# Run once with each budget: 8, then 12. Compare only complete paired outputs.
$steps = '12' # change to '8' for the 8-round pair
& $py benchmarks\evaluate.py @common --max-steps $steps --output $base
& $py benchmarks\evaluate.py @common --max-steps $steps `
  --progress-guidance checklist --output $guided
& $py benchmarks\compare.py --baseline (Join-Path $base 'results.json') `
  --candidate (Join-Path $guided 'results.json')
```

## Remaining work

1. Resume a fresh 8-round pair only after confirming the validation reference gate is stable; require all three trials in both arms before comparing.
2. Diagnose model-side PHP syntax and tool-loop failures using the retained disposable worktrees. Do not weaken permissions or count lint-clean writes as success.
3. Retry genuine native, model-selected Boost MCP calls only after analyzing why discovery plus schemas did not lead to an invocation.
4. Do not mark TinyBuilder ready until model-generated Laravel changes pass independent route, PHP, and Pest/PHPUnit validation and MCP tool selection is demonstrated.
