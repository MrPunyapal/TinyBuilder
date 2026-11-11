# Local functional evaluation

`evaluate.py` is an opt-in functional harness. It never pulls weights, trains a
model, calls a paid provider, or runs in baseline CI. Install TinyBuilder in a
virtual environment and pull the models explicitly first.

The [2026-11-11 Windows evaluation](results/2026-11-11-windows.md) found working
local HTTP inference, working Boost MCP and working local read/write/command
tools, but **no successful model-driven inspection or Laravel edit** with the
tested Qwen2.5-Coder 0.5B and 1.5B tags. The optional 3B smoke test also failed.
See the accompanying [metadata](results/2026-11-11-windows.json).

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
