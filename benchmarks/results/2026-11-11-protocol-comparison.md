# Local protocol comparison — 2026-11-11

**A local 3B model completed the bounded read-and-edit evaluation with the new
opt-in constrained strict JSON profile.** The 0.5B and 1.5B models did not. Native
and prompt-only strict JSON both failed the complete evaluation for every model.

The checkout was fast-forwarded from `9a620c0` to the requested `857a227` before
testing. All 34 existing tests, compilation and doctor passed. The new changes
add six regression tests, for **40 passing tests**. No weights were downloaded,
no paid inference was used, and no training or system installation occurred.

## Comparison

Calls below are successful executed local tool calls summed across the Composer
smoke, Laravel source read and Laravel edit tasks. “Read task” means correctly
identifying the full hidden random Composer package name and Laravel constraint,
after actually reading `composer.json`. A valid JSON response alone never counts.

| Model | Protocol/profile | Valid executed tool calls | Read task | Laravel edit | PHPUnit |
| --- | --- | ---: | --- | --- | --- |
| 0.5B | native | 0 | Fail | Fail | 3/4 |
| 1.5B | native | 0 | Fail | Fail | 3/4 |
| 3B | native | 0 | Fail | Fail | 3/4 |
| 0.5B | strict-json / prompt | 1 | Fail | Fail | 3/4 |
| 1.5B | strict-json / prompt | 0 | Fail | Fail | 3/4 |
| 3B | strict-json / prompt | 0 | Fail | Fail | 3/4 |
| 0.5B | strict-json / constrained | 0 | Fail | Fail | 3/4 |
| 1.5B | strict-json / constrained | 3 | Fail | Fail | 3/4 |
| **3B** | **strict-json / constrained** | **6** | **Pass** | **Pass** | **4/4** |

Every disposable worktree first passed the two original tests. The hidden
health assertion failed before inference with 404, then was removed during model
execution and restored for validation. Failed edit runs left `/health` absent;
their original/home checks passed and only the health check failed.

Primary measured durations in seconds (model requests and tools, excluding
worktree copying/setup):

| Model | Native smoke/read/edit | Prompt strict smoke/read/edit | Constrained smoke/read/edit |
| --- | --- | --- | --- |
| 0.5B | 7.922 / 0.844 / 0.312 | 0.859 / 0.781 / 0.578 | 0.547 / 0.625 / 0.282 |
| 1.5B | 2.828 / 0.969 / 0.531 | 0.922 / 2.297 / 1.187 | 0.812 / 1.328 / 0.703 |
| 3B | 3.969 / 1.094 / 0.578 | 1.172 / 5.625 / 1.203 | 1.516 / 1.937 / 4.579 |

These are individual trials with warm caches, model loading/eviction, diagnostic
requests and system memory pressure; they are not controlled speed comparisons.

## Evidence of the successful edit

The final constrained 3B run made these real calls:

1. Composer smoke: `read_file` for `composer.json`, then a correct final answer.
2. Laravel read task: `read_file` for `routes/web.php` and `bootstrap/app.php`.
3. Edit task: `read_file` for `routes/web.php`, `write_file` for that file, then
   `run_command` with the exact allowed `php artisan test` argv.

The [captured model diff](2026-11-11-constrained-3b.patch) adds only:

```php
Route::get('/health', function () {
    return response()->json(['status' => 'ok']);
});
```

The existing `/` route remains. Independent `php artisan route:list --path=health
--json` showed GET|HEAD `health`. Independent PHPUnit execution passed **4 tests,
5 assertions**, including the evaluator's exact JSON response and preserved home
page. Pint fixed line endings/test layout only, and the suite passed again.
No deterministic tool-control run was counted as a model success.

The baseline was the same disposable Laravel commit
`13392feebf08620c9f871c775b8ff321aef87b2e`, Composer lock SHA-256
`93a729350d188fc6d960e10d06677be94ddc1a1ff9250778dee6f16b209f7695`.
All model variants used separate detached worktrees with full vendor copies.

## Diagnosis and changes

The unmodified strict JSON mode asked for JSON only but did not request
structured generation from Ollama. Actual transient responses still used
Markdown fences; the parser correctly refused them. This was model formatting
noncompliance, not a parser defect. Native responses likewise remained text
instead of native tool calls.

Controlled diagnostic variants separated formatting from task reasoning:

- Server JSON schema with the original long prompt removed fences, but 0.5B and
  1.5B answered prematurely; 3B read the file but shortened the package name
  incorrectly. All smoke checks failed.
- A compact prompt plus the same schema let 1.5B read the file, though its facts
  were wrong; 3B read it and copied the exact hidden name correctly.
- A diagnostic 3B Laravel run also passed, followed by the final normal CLI/
  benchmark run recorded above. These are two successful bounded edit trials,
  not a broad reliability estimate.

Added `--strict-json-profile constrained`, requiring explicit `--tool-protocol
strict-json`. It uses the compact prompt and requests an action JSON schema via
the [Ollama-supported `response_format` field](https://docs.ollama.com/capabilities/structured-outputs).
The grammar permits either a final answer or any of the five existing local
tools. It does not inject facts, choose the correct tool for the model or supply
the endpoint implementation. The independent parser, retry limit, path checks,
permission flags and exact argv allowlist remain enforced. Servers that ignore
the schema still cannot cause fenced or unknown actions to execute. Servers
rejecting the feature fail explicitly. Native and prompt-only defaults remain
unchanged; MCP remains native-only.

Verified benchmark defects fixed with deterministic regressions:

- A successful retry could produce `passed=true` while still reporting a
  terminal protocol failure. Successful smoke recovery now clears the terminal
  failure category while retaining rejection events.
- A read of an unrelated file could satisfy the file-read evidence check.
  The evaluator now tracks requested target files in RAM and requires the actual
  Composer/route/bootstrap reads. Only fixed public fixture names appear in
  missing-file metadata; arbitrary arguments and source contents remain excluded.
- Laravel acceptance now also requires all requested edit-tool/file evidence
  and a final answer, in addition to route/diff/scope and PHPUnit validation.

The parser was not relaxed, and no fenced JSON was converted into an action.
No changes were needed to the local file/command tools or Laravel dependencies.

## Remaining model limitations

0.5B generally chose a premature final answer even when formatting was enforced.
1.5B read files but confused dependency names with the project package, skipped
the requested bootstrap read and stopped before writing/testing. The constrained
3B read-task diagnostic produced an incomplete prose explanation despite correct
file reads; source access is proven, but explanation quality still needs work.
Only a small additive route task was evaluated. Larger files, long contexts,
failure recovery, complex changes and adversarial projects remain unproven.

Syntax constraints do not guarantee honest final answers. The diagnostic 3B
read task's incomplete explanation and the smaller models' wrong facts were not
fixed by accepting weaker responses. The hidden-name and PHPUnit assertions were
retained, and target-file checks became stricter.

## Boost and resource observations

On the same Windows 11/i7-12700H/16 GB/RTX 3050 4 GB machine, using Python 3.12.14,
Ollama 0.32.5, Herd PHP 8.5.12, Laravel 13.42.0 and Boost 2.10.4:

- Updated TinyBuilder again discovered **9 Boost MCP tools** and verified the
  project's default SQLite connection. Documentation retrieval was proven in
  the earlier evaluation; it was not repeated here. Responses remained transient.
- Ollama reported all three models fully GPU-offloaded with context 4096.
- With all three loaded, NVIDIA reported **3,892 / 4,096 MiB** GPU use. Free
  system RAM in that snapshot was only **576,812 KiB** while other apps ran.
- Runner working sets were approximately **557 MiB (0.5B), 644 MiB (1.5B),
  758 MiB (3B)**. Private commit was approximately **1.21, 1.94 and 2.98 GiB**,
  respectively. Private commit is not resident RAM, and GPU allocations are
  separate from download size. These were snapshots, not measured peaks.

## Commands and artifacts

After `git pull --ff-only origin main`, these local checks ran:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q tinybuilder benchmarks
.\.venv\Scripts\python.exe -m tinybuilder doctor --project .
```

The primary benchmark commands used the following arguments (output directories
must be new; choose fresh names to repeat):

```powershell
$env:PATH = 'C:\Users\mrpun\.config\herd\bin\php85;' + $env:PATH
$app = Join-Path $env:TEMP 'tinybuilder-e2e-20261111\laravel'
$models = @('qwen2.5-coder:0.5b', 'qwen2.5-coder:1.5b', 'qwen2.5-coder:3b')
.\.venv\Scripts\python.exe benchmarks\evaluate.py --tool-protocol native --models @models --laravel $app --output "$env:TEMP\tinybuilder-protocol-857a227-native"
.\.venv\Scripts\python.exe benchmarks\evaluate.py --tool-protocol strict-json --models @models --laravel $app --output "$env:TEMP\tinybuilder-protocol-857a227-strict"
.\.venv\Scripts\python.exe benchmarks\evaluate.py --tool-protocol strict-json --strict-json-profile constrained --models @models --laravel $app --output "$env:TEMP\tinybuilder-protocol-constrained-final"
```

All three aggregate commands exit **1**, because at least one included model
fails. The constrained 3B result inside its report is successful. To evaluate only
that model on a new output directory, use `--models qwen2.5-coder:3b`.

The local artifacts retain original model diffs and evaluator test output.
The [committed metadata](2026-11-11-protocol-comparison.json) contains sanitized
events and outcomes, with worktree paths shortened. No model answers, hidden
package values, tool observations, documentation or MCP responses were persisted
to repository evidence or SQLite. The patch is the requested generated source
artifact. Historical evaluation files remain unchanged.

Changed implementation files: `agent.py`, `model.py`, `protocol.py`, `cli.py` and
`benchmarks/evaluate.py`; regression files: `test_protocol.py`, `test_model.py`,
`test_cli.py` and `test_benchmark.py`; README and these evidence artifacts document
the opt-in profile and observed limits.

Next experiment: repeat the constrained 3B task across fresh hidden package names
and locked Laravel worktrees, including failing-test repair and a second route
change. Measure success rate and resource peaks before claiming reliable coding
capability. Keep the 3B tag's Qwen Research License distinct from TinyBuilder's
MIT code license. No training is justified by this narrow success alone.
