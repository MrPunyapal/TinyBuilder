# Phase 2 local reliability evaluation — 2026-11-12

## Setup and checks

The checkout fast-forwarded from `5ad1d50` to the brief's expected
`22c4097a26e48d18b4beb825f85b116b5f6e488b`. The disposable Laravel 13.42.0
baseline was marked, clean, vendor-installed and locked at
`13392feebf08620c9f871c775b8ff321aef87b2e` (the same lockfile previously
recorded for this fixture). Its original PHPUnit suite passed 2/2.

On Windows 11 with PHP 8.5.12, Composer 2.11.1 and Ollama 0.32.5, the prescribed
checks passed: **64 unit tests**, compileall, doctor, and an HTTP 200 from the
local Ollama tags endpoint. `qwen2.5-coder:3b` was already installed; no model
download occurred. Both comparisons used three trials and a shared fixture seed
within each pair. `compare.py` confirmed matched inputs for both pairs.

## Results

The Laravel read-only task read both `routes/web.php` and `bootstrap/app.php`
in all 3 trials in each profile. The evaluator's final independent PHPUnit
result was 3/3 in every row. “Required edit reads” counts successful reads of
the files required by the edit task. “Route writes” counts actual successful model write calls;
“Laravel pass” is the full acceptance result, including required reads, scope,
tool order, route verification and tests. Composer smoke facts are listed
separately because an observed file read did not always yield a correct answer.

| Experiment | Model | Required edit reads | Route writes | Final PHPUnit | Laravel pass | Composer facts |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Health, original constrained | 3B | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| Health, checklist | 3B | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 |
| Repair, original constrained | 3B | 0/3 complete (route read 3/3; visible test read 0/3) | 3/3 | 3/3 | 0/3 | 3/3 |
| Repair, checklist | 3B | 3/3 | 3/3 | 3/3 | 3/3 | 1/3 |

All health edits were real model `read_file` → `write_file` → permitted
`php artisan test` sequences. Each final test suite passed, `/health` was
registered, and only `routes/web.php` appeared in the model-authored diff.
Independent review of a retained
trial confirmed GET|HEAD `/health`, the exact JSON response, 4 tests and 5
assertions passing, and the expected route-only patch.

In the repair baseline, every trial changed the route and ultimately passed the
independent suite, but skipped the required visible regression-test read. Each
also made an initial test command that returned nonzero, then edited and reran
the test command successfully. Because the checklist was off, this violated the
required read evidence; none counted as a repair pass. The checklist repair
trials read both required files, tested after the final edit, kept the visible
test and sibling route unchanged, changed only the route, and passed all
independent checks. A retained trial independently showed GET|HEAD `/health`,
the preserved sibling route, and 6 tests / 9 assertions passing.

For the Composer smoke task, all trials made a successful `read_file` call.
However, checklist answers repeated the exact hidden package name and Laravel
constraint only once in three trials. The other two were factual failures, not
missing-tool or runtime failures. The checker did not accept plausible claims.

| Matched comparison | Composer smoke | Laravel task |
| --- | ---: | ---: |
| Health: original → checklist | 3/3 → 1/3 | 3/3 → 3/3 |
| Repair: original → checklist | 3/3 → 1/3 | 0/3 → 3/3 |

## Diagnosis and resource snapshot

The observed repair improvement comes from bounded completion guidance keeping
the model on the required read → edit → test sequence. It did not supply file
contents, perform operations, or weaken acceptance. In un-guided repair runs the
3B model repeatedly skipped the visible test and needed to react to a failing
test command. The checklist did not improve exact factual recall on the Composer
fixture. These are small observed samples, not a reliability estimate.

No runtime defect was established, so no implementation behavior was changed.
No model answers, file contents, Composer package identities, MCP results,
fixture seeds or private local paths are included in this report. Trial reports,
worktrees and patches remain in the local temporary evaluation directory.

A point-in-time snapshot after the trials showed Ollama's 3B model at 2.2 GB,
GPU use 2,158/4,096 MiB, and 1.77 GiB free RAM out of 15.63 GiB. This is not a
peak measurement; it is affected by other applications and the model remained
loaded after evaluation.

## Reproduction

Run from the TinyBuilder checkout in PowerShell with the disposable baseline
already prepared, clean and marked. Do not point `$app` at a personal or
production application. Use one fresh seed for each pair and fresh output
directories. Herd users can prepend the actual PHP executable directory as
shown.

```powershell
$app = 'C:\path\to\marked-disposable-laravel'
$phpExe = php -r 'echo PHP_BINARY;'
$env:PATH = (Split-Path $phpExe) + ';' + $env:PATH
$healthSeed = [guid]::NewGuid().ToString('N')
$repairSeed = [guid]::NewGuid().ToString('N')
$baseHealth = Join-Path $env:TEMP ('tb-base-health-' + [guid]::NewGuid().ToString('N'))
$guideHealth = Join-Path $env:TEMP ('tb-guide-health-' + [guid]::NewGuid().ToString('N'))
$baseRepair = Join-Path $env:TEMP ('tb-base-repair-' + [guid]::NewGuid().ToString('N'))
$guideRepair = Join-Path $env:TEMP ('tb-guide-repair-' + [guid]::NewGuid().ToString('N'))
$common = @('--models','qwen2.5-coder:3b','--tool-protocol','strict-json',
  '--strict-json-profile','constrained','--trials','3','--laravel',$app)

.\.venv\Scripts\python.exe benchmarks\evaluate.py @common --fixture-seed $healthSeed --output $baseHealth
.\.venv\Scripts\python.exe benchmarks\evaluate.py @common --fixture-seed $healthSeed --progress-guidance checklist --output $guideHealth
.\.venv\Scripts\python.exe benchmarks\compare.py --baseline (Join-Path $baseHealth 'results.json') --candidate (Join-Path $guideHealth 'results.json')

$repair = @('--scenario','repair','--preserve-sibling-route')
.\.venv\Scripts\python.exe benchmarks\evaluate.py @common @repair --fixture-seed $repairSeed --output $baseRepair
.\.venv\Scripts\python.exe benchmarks\evaluate.py @common @repair --fixture-seed $repairSeed --progress-guidance checklist --output $guideRepair
.\.venv\Scripts\python.exe benchmarks\compare.py --baseline (Join-Path $baseRepair 'results.json') --candidate (Join-Path $guideRepair 'results.json')
```

An evaluation exit code of 1 means one or more task failures; continue to the
paired comparison and inspect the sanitized `results.json`, `model-diff-0.patch`,
`phpunit-0.txt` and retained disposable worktrees. The comparer should exit 0
when both complete reports match configuration and fixture IDs.

## Recommendation

Keep `--progress-guidance checklist` opt-in. Its 3/3 repair result is promising
for explicit multi-step tasks, but the 1/3 Composer factual result and only three
trials do not justify changing defaults. Next, expand the pinned local benchmark
to 20–50 tasks with repeatable repair, read-only and preservation cases, and
measure peak resources. Continue to separate model-quality failures from runtime
bugs; do not start fine-tuning or Soup training from this evidence.
