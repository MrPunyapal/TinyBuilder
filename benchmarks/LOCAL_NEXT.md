# Focused local retest — after 2026-11-16 preview validation

The [existing full Windows campaign](results/2026-11-16-windows-preview-validation.md)
already measured 18/18 real randomized Composer inspections, 3/3 health edits,
3/3 health repairs, and four complete paired validation arms (0/3 each).
Three model-selected native MCP trials made zero calls. **Do not rerun all
historical campaigns unchanged.** This handoff concerns the *new* parameter
scenario and optional diagnostic/MCP follow-ups only.

## Safe Windows checkout and new Python regressions

```powershell
if (git status --porcelain) { throw 'Preserve local changes before updating' }
git pull --ff-only origin main
git rev-parse HEAD
$py = '.\.venv\Scripts\python.exe'
& $py -m pip install -e .
& $py -m unittest discover -s tests -v
& $py -m compileall -q tinybuilder benchmarks
ollama list
```

The regular CI checks Python and release packages on Ubuntu; it cannot test
actual installed Ollama or the Windows Laravel environment.

## Real PHP reference controls (manually triggered in GitHub)

In GitHub: **Actions → Laravel PHP reference controls (manual) → Run workflow**.
[Workflow file](../.github/workflows/laravel-controls.yml).

This creates a new marked, disposable Composer-installed Laravel 13 app,
then runs both contact-validation and integer-parameter negative/reference
controls. It requires **no Ollama, downloaded model, paid API or training**.
Successful reference controls establish PHP fixture correctness only, **not**
a model-generated success. The workflow is not triggered by normal pushes.
No workflow execution is claimed until an actual run succeeds.

## New model experiment: route parameter only

Use a clean, marked, **disposable** Laravel baseline; never use a production
or personal project. Choose new temp outputs for each command.

```powershell
$app = 'C:\path\to\clean-marked-disposable-laravel'
if (!(Test-Path (Join-Path $app '.tinybuilder-disposable'))) {
  throw 'Missing disposable marker'
}
if (!(Test-Path (Join-Path $app 'composer.lock'))) {
  throw 'Missing Composer lockfile'
}
if (git -C $app status --porcelain) {
  throw 'Baseline has changes; preserve them'
}
$phpExe = php -r 'echo PHP_BINARY;'
$env:PATH = (Split-Path $phpExe) + ';' + $env:PATH
$controls = Join-Path $env:TEMP ('tb-param-controls-' + [guid]::NewGuid().ToString('N'))
& $py benchmarks\evaluate.py --scenario parameter --controls-only --laravel $app --php $phpExe --preserve-sibling-route --output $controls
if ($LASTEXITCODE -ne 0) { throw 'Real parameter controls failed; stop inference' }

$trial = Join-Path $env:TEMP ('tb-param-3b-' + [guid]::NewGuid().ToString('N'))
$seed = [guid]::NewGuid().ToString('N')
& $py benchmarks\evaluate.py --scenario parameter --preserve-sibling-route --models qwen2.5-coder:3b --tool-protocol strict-json --strict-json-profile constrained --progress-guidance checklist --max-steps 8 --trials 3 --fixture-seed $seed --laravel $app --php $phpExe --output $trial
```

A complete report may exit 1 when model tasks fail. Inspect sanitized
`results.json` and independent tool/route/test/scope evidence. Retained
worktree diffs and PHP test output can contain source; do not upload them
without review. Real model success is not a reference fix or a scripted test.

## Optional only: a single refreshed failure-diagnostic sample

The new evaluator fields `php_lint_exit`, `diagnostics.php_parse_error`,
`write.round_exhausted`, rejected/denied command counts and nonzero
allowed-test counts are sanitized. To verify these on your own real PHP
environment, one fresh validation trial suffices for now; do **not**
repeat both historical 8-vs-12 matched campaigns without a new hypothesis.

```powershell
$diag = Join-Path $env:TEMP ('tb-validation-diagnostic-' + [guid]::NewGuid().ToString('N'))
& $py benchmarks\evaluate.py --scenario validation --models qwen2.5-coder:3b --tool-protocol strict-json --strict-json-profile constrained --max-steps 8 --trials 1 --laravel $app --php $phpExe --output $diag
```

## Optional only: real model-selected Boost MCP

The latest MCP regressions verify catalog schemas and actual scripted
native-call-shaped messages over stdio. They **do not** establish real Qwen
model selection. For one focused read-only local trial using an already
installed model and trusted MCP config:

```powershell
& $py -m tinybuilder chat 'Use one connected read-only Laravel Boost MCP tool to inspect this project. Invoke it with native tool calling; do not edit or run commands.' --project $app --model qwen2.5-coder:3b --mcp-config examples\mcp.json --verbose
```

Look for a genuine MCP `tool_end` event. Model prose naming a tool is not
an invocation; the previous native model results remained 0/3.

Return the ending code SHA, actual parameter reference pass/fail, 3B
parameter scenario trial results, sanitized diagnostics if collected, and
an actual native MCP event if one occurred. Keep private content local.
No model downloads, paid APIs, Soup training or automatic PHP repair.
