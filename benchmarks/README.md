# Local functional evaluation

`evaluate.py` is an opt-in functional harness. It never pulls weights, trains a
model, calls a paid provider, or runs in baseline CI. Install TinyBuilder in a
virtual environment and pull the models explicitly first.

The [2026-11-11 Windows evaluation](results/2026-11-11-windows.md) found working
local HTTP inference, working Boost MCP and working local read/write/command
tools, but **no successful model-driven inspection or Laravel edit** with the
tested Qwen2.5-Coder 0.5B and 1.5B tags. The optional 3B smoke test also failed.
See the accompanying [metadata](results/2026-11-11-windows.json).

## Opt-in tool protocol comparison

The original [2026-11-11 Windows evaluation](results/2026-11-11-windows.md) remains unchanged historical evidence. Native OpenAI-style tool calls remain the default. The **experimental**, opt-in `strict-json` protocol tests whether a small model can produce one exact JSON tool action per round; it does not extract tool calls from Markdown or prose and has no MCP tools.

From PowerShell, with Ollama already running and both local models downloaded, compare separate **new** output directories:

```powershell
$native = Join-Path $env:TEMP ('tinybuilder-native-' + [guid]::NewGuid().ToString('N'))
$strict = Join-Path $env:TEMP ('tinybuilder-strict-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py --tool-protocol native --output $native
.\.venv\Scripts\python.exe benchmarks\evaluate.py --tool-protocol strict-json --output $strict
```

Both commands may exit 1; that is an honest task failure. Each smoke test still hides the random package name, requires an **actual successful `read_file` event** and checks the exact package name and Laravel constraint. Printed JSON alone never counts. `failure_kind` and `missing_required_tools` separate HTTP connectivity, protocol, argument, permission, execution and factual failures.

To repeat the endpoint evaluation after creating the **explicitly disposable** baseline described below:

```powershell
$strictLaravel = Join-Path $env:TEMP ('tinybuilder-strict-laravel-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py --tool-protocol strict-json --laravel $app --output $strictLaravel
```

Do not count success unless route changes, tool events and restored hidden PHPUnit tests all pass. Never use a production project for this harness. No Soup training, model downloads or paid inference occurs automatically.

For the separately evaluated compact/schema-constrained variant, use a fresh
output directory and add `--strict-json-profile constrained`:

```powershell
$constrained = Join-Path $env:TEMP ('tinybuilder-constrained-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py --tool-protocol strict-json --strict-json-profile constrained --models qwen2.5-coder:0.5b qwen2.5-coder:1.5b qwen2.5-coder:3b --laravel $app --output $constrained
```

The profile requests a JSON schema from the local inference server and uses a
shorter system prompt. It leaves tool decisions and factual answers to the model.
Its client-side parser rejects the same malformed, fenced, unknown and oversized
actions. A server HTTP error is a failure, with no automatic protocol fallback.
See the [local comparison and measured limitations](results/2026-11-11-protocol-comparison.md).

The evaluator now also checks the specific requested file reads: `composer.json`
for the smoke task; `routes/web.php` and `bootstrap/app.php` for the Laravel read
task; and `routes/web.php` during the edit task. Only these fixed, public fixture
names can appear in `missing_required_files`; arbitrary paths and source contents
are not logged. A recovered parse error remains in events but does not label an
otherwise successful smoke task as failed. Laravel success additionally requires
a final answer and all required edit-tool/file evidence.

## Windows reproduction

Run from the TinyBuilder checkout. Use an actual Python 3.10+ interpreter if the
`python` command is a Windows Store alias. No activation or system installation
is required when an interpreter is already available:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q tinybuilder benchmarks
.\.venv\Scripts\python.exe -m tinybuilder doctor --project .
ollama --version
ollama pull qwen2.5-coder:0.5b
ollama pull qwen2.5-coder:1.5b

# Smoke only: output must be a NEW directory. Exit 1 means task failure.
$run = Join-Path $env:TEMP ('tinybuilder-eval-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py --output $run
```

For the real Laravel evaluation, create a **new disposable application**. These
commands download PHP dependencies and run their installation scripts. They do
not install PHP, Composer or Ollama system-wide:

```powershell
$repo = (Get-Location).Path
$root = Join-Path $env:TEMP ('tinybuilder-laravel-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $root | Out-Null
$app = Join-Path $root 'app'
composer create-project laravel/laravel $app 13.11.0 --no-install --no-interaction

# Herd users: ensure shell-free Python subprocesses find the real php.exe.
$phpExe = php -r 'echo PHP_BINARY;'
$env:PATH = (Split-Path $phpExe) + ';' + $env:PATH

Push-Location $app
# Disable expensive optimized classmap generation for this disposable fixture.
composer config optimize-autoloader false
composer require laravel/framework:13.42.0 --no-update --no-interaction
composer install --prefer-dist --no-interaction
composer require laravel/boost:2.10.4 --dev --no-interaction
php artisan boost:install --no-interaction
php artisan key:generate --no-interaction
php artisan test
git init --initial-branch=main
Set-Content .tinybuilder-disposable 'Disposable TinyBuilder evaluation only'
git add .
git commit -m 'Disposable Laravel evaluation baseline'
Pop-Location

.\.venv\Scripts\python.exe -m tinybuilder doctor --project $app --mcp-config examples\mcp.json
.\.venv\Scripts\python.exe -m tinybuilder chat 'Inspect routes/web.php using tools and explain how to add a health endpoint. Do not edit files.' --project $app --model qwen2.5-coder:1.5b --mcp-config examples\mcp.json --verbose
.\.venv\Scripts\python.exe benchmarks\evaluate.py --laravel $app --output (Join-Path $root 'evaluation')
```

These pin the application template, framework and Boost versions used in the
recorded run. Transitive dependencies can differ on a fresh installation; retain
the generated `composer.lock` and baseline commit for exact repeats. The harness
reports their identities and copies installed dependencies into each worktree
without network requests. The original recorded lockfile remains in the local
disposable baseline named in the results report.

On POSIX systems, use `.venv/bin/python`, normal shell variable syntax, and
ensure `php` names a real executable. The Python harness itself is cross-platform.

## Protocol and artifacts

- Smoke fixtures contain a fresh random Composer package name, realistic
  dependencies, routes and PHP source. The package name is never put in the
  prompt or project summary. Passing requires an actual successful `read_file`
  call and a final answer containing the package name and Laravel constraint.
- Laravel mode requires an explicit `.tinybuilder-disposable` marker, a clean
  tracked baseline and a committed lockfile. It adds detached Git worktrees,
  leaving the baseline source untouched. Use this mode only on newly created
  disposable apps: the marker expresses operator consent to fixture setup,
  project scripts, opt-in file writes and test execution.
- Each model receives the same read task and health-endpoint edit task. Writes
  are enabled only inside its worktree. Execution is restricted to the exact
  `["php","artisan","test"]` argv (or the supplied `--php` executable).
- The evaluator first proves the original suite passes and the hidden health
  assertion fails. Hidden tests are removed before inference and restored after
  the edit. It checks the route table, exact response JSON, home-page behavior,
  change scope and real PHPUnit/Pest exit codes. Only `routes/web.php` may change
  for this task; successful write and command tool events are required.
- `results.json` contains sanitized event metadata and pass/fail signals.
  `diff-N.patch`, `baseline-health-N.txt` and `phpunit-N.txt` contain the local
  route diff and evaluator test output. Model answers and tool/MCP observations
  are never saved by the harness. No SQLite memory store is used.
- The evaluator snapshots the disposable worktree's ignored `.env` after key
  generation and rejects a trial if it changes, including changes caused
  indirectly by a permitted test command. Reports store only a boolean, never
  the contents of the environment file.
- Worktrees and fixtures are retained for review. Inspect them with `git diff`;
  remove only these disposable worktrees with `git worktree remove` when done.
  No cleanup, recursive deletion or download occurs implicitly.

To include the optional larger comparison, explicitly download it, then pass
`--models qwen2.5-coder:0.5b qwen2.5-coder:1.5b qwen2.5-coder:3b`. Note that the
3B tag advertises the Qwen Research License; do not assume all sizes share the
0.5B tag's Apache license.

## Limits and next milestone

This is one functional task per model, not a statistically useful coding score.
Timing includes HTTP inference and model loading; warm/cold state, scheduling and
system memory pressure can differ. A model answer or a zero CLI exit code alone
does not prove task completion. MCP is tested independently because its discovery
working does not mean a model chose or correctly used its tools.

Next, expand to 20–50 pinned tasks with locked dependencies, repeated trials and
resource sampling. Compare unmodified local baselines before collecting training
data. Do not train or run Soup until observed failures and evaluation data justify it.

## Expanded opt-in regression evaluation

See [RETEST.md](RETEST.md) for exact PowerShell commands covering repeated randomized Composer smoke trials, an opt-in completion checklist, unrelated-route preservation, and a failing-test repair task. These additions preserve the existing acceptance assertions and do not run in CI.

## Phase 3 opt-in request-validation scenario (requires local PHP verification)

The new `--scenario validation` seeds a broken `POST /tinybuilder/contact`
route and a visible failing regression test in a **marked disposable Laravel
worktree**. Independent hidden tests check required email and message fields,
invalid email, minimum message length, valid JSON response, original home route,
and optional unrelated sibling-route preservation. The model must read the
route and visible test **before its first edit**, change only `routes/web.php`,
execute the exact allowed PHP test command after its final edit, and pass
independent final PHPUnit and route-table checks.

**Run the reference controls first, without Ollama**:

```powershell
$py = '.\.venv\Scripts\python.exe'
$phpExe = php -r 'echo PHP_BINARY;'
$env:PATH = (Split-Path $phpExe) + ';' + $env:PATH
$controls = Join-Path $env:TEMP ('tb-validation-controls-' + [guid]::NewGuid().ToString('N'))
& $py benchmarks\evaluate.py --scenario validation --controls-only --laravel $app --php $phpExe --preserve-sibling-route --output $controls
```

This command does **not** call a model. The evaluator proves the initial
tests fail, temporarily applies an evaluator-owned reference fix, requires the
full PHP suite and route table to pass, then restores the broken seed and
removes the hidden test before any inference. It refuses to run the model if
these controls fail. A fake-artisan regression test in CI checks the harness
flow but is **not** evidence of real Laravel correctness. The scenario should
not be counted as locally validated until the above command succeeds with
actual PHP/Laravel.

For a matched three-trial Ollama comparison after controls pass, see
[RETEST.md](RETEST.md). No downloaded model is required for controls-only mode,
and no new model weights or paid APIs are used automatically.
