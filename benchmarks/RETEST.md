# Local retest: opt-in completion guidance and repeated Laravel trials

This is an **unverified experiment**, not a replacement for the Windows 2026-11-11
results. The measured `strict-json + constrained` profile remains unchanged unless
`--progress-guidance checklist` is explicitly enabled. Native tool calling stays
the default; this experiment exposes only the five local tools, not Laravel Boost MCP.

Only run the Laravel evaluations against a **new, disposable, Git-committed Laravel
baseline** with `.tinybuilder-disposable` and `composer.lock`, prepared using
[benchmarks/README.md](README.md). This harness copies dependencies into fresh,
detached worktrees under each new output directory. It does not alter the baseline.
Results, patches and worktrees remain on your computer until manually removed.

## 1. Verify the checkout

From PowerShell in the TinyBuilder checkout:

```powershell
git pull --ff-only origin main
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q tinybuilder benchmarks
.\.venv\Scripts\python.exe -m tinybuilder doctor --project .
ollama list
```

Set `$app` to your **marked, disposable Laravel baseline** (not a production or
personal app). For Herd, ensure Python sees the real `php.exe` without a shell:

```powershell
$app = 'C:\path\to\your\disposable-laravel'
$phpExe = php -r 'echo PHP_BINARY;'
$env:PATH = (Split-Path $phpExe) + ';' + $env:PATH
Test-Path (Join-Path $app '.tinybuilder-disposable')
Test-Path (Join-Path $app 'composer.lock')
```

Both checks must return `True`. Ensure that the baseline is clean and its
original Laravel tests pass. Avoid placing output directories under the baseline.

## 2. Repeat the **measured profile**, unchanged

The model weights must already be available in Ollama. Run three independent
trials of the previous health-endpoint task with fresh hidden Composer package
names and separate Laravel worktrees:

```powershell
$baseline = Join-Path $env:TEMP ('tinybuilder-baseline-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py `
  --models qwen2.5-coder:3b --tool-protocol strict-json `
  --strict-json-profile constrained --trials 3 --laravel $app --output $baseline
```

Do not treat one passing trial as a reliability estimate. An exit code of `1`
means one or more benchmark tasks failed. Review `results.json`,
`trial-001\model-diff-0.patch`, the PHPUnit output files and retained worktrees.

## 3. Compare **new** opt-in completion guidance

The model still selects every tool itself. The checklist does not read files,
write code, run commands or provide hidden facts. It postpones a premature final
answer up to two times if operator-specified required actions have not actually
succeeded, and then reports incomplete instead of accepting a claim. Only
successful local operations satisfy it. CLI mode needs explicit
`--required-read` and/or `--required-tool` entries; the evaluator derives
these from the public task instructions.

```powershell
$guided = Join-Path $env:TEMP ('tinybuilder-guided-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py `
  --models qwen2.5-coder:3b --tool-protocol strict-json `
  --strict-json-profile constrained --progress-guidance checklist `
  --trials 3 --laravel $app --output $guided
```

This uses the *same* underlying scenario as step 2. Compare independent trial
pass counts, actual `tool_end` events and `final_deferred` events. Timing and
model cache state are not controlled across runs.

## 4. Harder opt-in test: repair a failing test, preserve a sibling route

The evaluator seeds an intentionally incorrect `/health` response and adds a
**visible failing PHPUnit regression** in each disposable worktree. The model
must read the test and route, edit only `routes/web.php`, rerun permitted tests,
and satisfy a separate hidden validation suite. Another random existing route
must remain unchanged. The evaluator's own fixture edits are excluded from the
model delta, and edits to the visible test count as failure.

```powershell
$repair = Join-Path $env:TEMP ('tinybuilder-repair-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py `
  --models qwen2.5-coder:3b --tool-protocol strict-json `
  --strict-json-profile constrained --progress-guidance checklist `
  --scenario repair --preserve-sibling-route `
  --trials 3 --laravel $app --output $repair
```

The evaluator requires baseline test success, a failing repair test before
inference, an actual target-file read, a real file change, exact-argv test
execution **after the edit**, unmodified visible regression tests, strict file
scope and the independent hidden PHPUnit suite. A model-generated final answer
alone cannot pass.

## 5. Optional small-model comparison

```powershell
$small = Join-Path $env:TEMP ('tinybuilder-small-' + [guid]::NewGuid().ToString('N'))
.\.venv\Scripts\python.exe benchmarks\evaluate.py `
  --models qwen2.5-coder:0.5b qwen2.5-coder:1.5b `
  --tool-protocol strict-json --strict-json-profile constrained `
  --progress-guidance checklist --trials 3 --output $small
```

The smoke task still requires the model to read `composer.json` and repeat the
full unseen random package name and Laravel constraint. Neither the prompt nor
the report contains the hidden package name. Do not count printed JSON as a call.

## Interpreting results and limits

- Inspect the top-level `summary` for multi-trial pass counts **per model and
  per task**; it is not an average coding benchmark. Default `--trials 1` keeps
  the existing one-run report layout.
- `final_deferred` is *not* a successful action. Failed/denied tools never
  satisfy a checklist. A missing read or tool at the end remains a failure.
- `required_sequence_ok` verifies successful read → write → test order; the
  separately captured `model-diff-N.patch` excludes evaluator-seeded code.
- All tool observations are transient. Event metadata never includes arguments,
  model answers, file content, random package names or generated route markers.
- The harness **does not** automatically download models, train with Soup,
  call paid services, or invoke a shell for agent tool execution.
- A successful route/test scenario does not establish general coding reliability
  or peak RAM/VRAM. Resource measurements, if needed, must be performed locally.
- TinyBuilder's code is MIT licensed; do not assume the
  `qwen2.5-coder:3b` model weights use MIT or Apache. Its Ollama tag advertises
  the **Qwen Research License**; check its terms before redistribution or use.

## Phase 2 harness hardening: matched comparisons (opt-in)

The original measured profile and its model prompt remain unchanged. A new
`--fixture-seed` option makes the **hidden Composer package name** and, when
`--preserve-sibling-route` is used, the **existing sibling route** identical for
corresponding trials in separate benchmark runs. Each trial still has a different
fixture identity; identities are never injected into prompts or saved in
`results.json`. The seed itself is not saved, only a short SHA-256 identifier to
check whether reports use matched fixtures. Treat the seed as a local experiment
input, not as a training example or a secret used for authentication.

From PowerShell, after selecting a clean, marked disposable `$app` as above:

```powershell
$seed = [guid]::NewGuid().ToString('N')
$baseline = Join-Path $env:TEMP ('tinybuilder-base-' + [guid]::NewGuid().ToString('N'))
$guided = Join-Path $env:TEMP ('tinybuilder-guided-' + [guid]::NewGuid().ToString('N'))
$common = @('--models', 'qwen2.5-coder:3b', '--tool-protocol', 'strict-json',
            '--strict-json-profile', 'constrained', '--trials', '3',
            '--fixture-seed', $seed, '--laravel', $app)

.\.venv\Scripts\python.exe benchmarks\evaluate.py @common --output $baseline
.\.venv\Scripts\python.exe benchmarks\evaluate.py @common --progress-guidance checklist --output $guided

# Display aggregate observed successes, not an estimate of general model accuracy.
.\.venv\Scripts\python.exe benchmarks\compare.py `
  --baseline (Join-Path $baseline 'results.json') `
  --candidate (Join-Path $guided 'results.json')
```

Each evaluator command may exit 1 if **any** task fails. Continue to the next
command to record the comparison, and inspect each trial's `failure_kind`,
`tool_end`, `required_sequence_ok` and `tests_after_last_edit`. A test command
before the *last* model edit is not proof of testing the final file; the
acceptance rule now explicitly rejects that case even if an earlier
read → write → test sequence occurred. The independent final PHPUnit checks are
still mandatory.

For a harder scenario, run a *separate matched pair* with the same seed, adding
`--scenario repair --preserve-sibling-route` to **both** commands. The comparer
refuses mismatched scenarios, trial counts, seed identifiers, model order,
and Laravel baseline commit or Composer lockfile identity. The latter
checks prevent a shared seed from falsely labeling different Laravel inputs
as paired. Fresh
worktree directories are still required, and do not put `--output` anywhere
inside the disposable Laravel baseline. The preflight now refuses untracked
source files, missing installed dependencies, nested output directories and
non-root Git checkouts **before any model evaluation**.

These comparisons control fixture differences, **not** model sampling, context
cache state, RAM pressure or stochastic inference. Three trials are still far
too few to claim reliable general coding. The first follow-up should repeat the
original 3B task without checklist guidance using the same seeded fixtures and
compare it with the opt-in checklist. No fine-tuning or weight download is
performed by these commands.
