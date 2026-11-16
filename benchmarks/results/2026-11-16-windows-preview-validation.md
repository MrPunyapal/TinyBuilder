# Windows public-preview validation — 2026-11-16

**PUBLIC EXPERIMENTAL PREVIEW READY**

Windows installation, distribution, permission safety, genuine read-tool use, and
small independently accepted Laravel changes passed. Share the documented
experimental CLI with the measured limitations below. The request-validation
task and native model-selected MCP use remain unsuccessful. No version tag,
official release, binary upload, or PyPI publication was performed or authorized.

## Candidate and environment

The initial local checkout was `d17905e82d022f04602807691f79a7aa133a5bd4`, clean on `main`.
It fast-forwarded through three commits to the requested candidate
`faf4fb016cef302f4d5082c72eb9528de414a44b`. These commits added SQLite read safety,
MCP cleanup/error sanitization, packaging CI, and preview documentation. The
verified packaging/documentation correction is commit
`469243fccfe28f0024bd285da8d515c5d4ce987e`. The subsequent HTTP error-stream
cleanup and diagnostic correction is `0bd6ede8787c0951a7b52383676f273ad84554d7`.
Successful inference handling, model profiles, permissions, and acceptance tests
were unchanged; benchmark arms that started before the error fix exercised the
same successful-response logic. The error fix was separately retested against
real Ollama, and its built wheel passed a real tool-assisted inspection.
The final report publication commit is identified in the accompanying handoff.

- Windows 11 Home Single Language, build 26300; Intel Core i7-12700H.
- Python 3.12.14; Git 2.45.2.windows.1; PHP 8.5.12; Composer 2.11.1.
  PHP loaded Xdebug 3.5.3 and Zend OPcache; CLI OPcache was enabled. These settings
  were retained throughout rather than changed to improve benchmark timings.
- Ollama client/server 0.32.5, local OpenAI-compatible endpoint.
- Installed model evaluated: `qwen2.5-coder:3b`, digest prefix `f72c60cabf62`,
  3.1B parameters, Q4_K_M. No model downloads, training, or paid inference.
  Its local metadata advertises the Qwen Research License; TinyBuilder's MIT
  license does not license the model weights, which are not bundled.
- Existing clean, marked disposable Laravel baseline: Framework 13.42.0,
  Boost 2.10.4, committed lockfile, installed Composer autoloader, baseline
  commit `f8ffe9e7b9bbf8193aabfb2e9e351fd0314b0c43`.
- Old evaluations were preserved. New worktrees/artifacts are outside both
  source repositories. No personal or production Laravel project was used.

## Repository checks and packaging correction

Editable installation, the initial **119 Python tests**, compilation of `tinybuilder`
and `benchmarks`, and root doctor passed. After the HTTP regression was added,
the full **120-test** suite and compilation passed. The existing candidate CI passed on Ubuntu Python 3.10,
3.12, and 3.13.

Windows wheel installation passed in a new independent environment. CLI help,
doctor, and `pip check` passed from outside the checkout. Isolated import
resolved to that environment's `site-packages`, with version 0.1.0 and no runtime
dependencies. Uninstall succeeded and an isolated import then failed as expected.

**Reproduced defect:** the original source archive included tests but omitted
the benchmark modules those tests import. Testing the extracted archive failed
with 13 missing-module import errors. It also lacked its linked quick-start and
security documentation.

**Fix:** `MANIFEST.in` includes benchmark Python modules, benchmark instructions,
documentation, and the MCP example. The wheel remains runtime-only. CI now
extracts the source archive, checks essential files, and runs the complete suite
from that extracted directory. The corrected archive initially passed 119 tests;
the final rebuilt archive passed **120/120 tests** in the independent Windows
environment. Its installed wheel also completed a real successful `read_file`
inspection with correct facts and no preferences database creation. Both rebuilt archives passed inspection:
16 wheel entries, 63 source-archive entries; no forbidden environment files,
databases, weights, caches, generated reports, or personal checkout paths were
found. A scan for private-key, AWS access-key, and GitHub-token markers found
zero matches. This bounded inspection is not security certification.

The quick start now includes clone commands, an installed-Python fallback when
`py` is unavailable, and the actual PHP executable/PATH setup. This machine has
Python but no `py` launcher, so the fallback was exercised in a fresh clone and
virtual environment. Build directories are now ignored.

The fix passed [GitHub Actions on Python 3.10, 3.12, and 3.13](https://github.com/MrPunyapal/TinyBuilder/actions/runs/43889941094), including the new source-archive regression step.
The later HTTP cleanup and diagnostic fix also passed [all three CI jobs](https://github.com/MrPunyapal/TinyBuilder/actions/runs/43894902133) with the 120-test suite.

## First-user and real Ollama checks

A fresh GitHub clone, independent virtual environment, editable install, CLI help,
and doctor passed. The quick-start `pyproject.toml` task was tested with real
local Ollama. Answers and observations were inspected in memory and discarded.

| Mode/check | Observed result |
|---|---|
| Default native | HTTP inference completed; zero actual reads; project-name answer incorrect |
| Opt-in constrained strict JSON | One successful `read_file`; exact project name correct; 3.26 seconds |
| Unavailable local server | Exit 1, sanitized connectivity error |
| Unavailable model | Exit 1, sanitized HTTP error; no download |

These read-only chats left project source unchanged and created neither the
missing preferences database nor its parent directory. Native tool failure is
disclosed rather than treated as a successful inspection. The strict mode remains
opt-in; native remains the default.

The unavailable-model CLI originally displayed only `Model server HTTP 404`.
A deterministic HTTP test also proved its response stream remained open after
failure, matching observed resource warnings. Before the fix, the new recovery-hint
test and the response-closure assertion both failed. After the fix, all six focused
model-client tests passed. HTTP errors close their unread response stream and 404s
add `check the installed model name and API base URL`; private server response
bodies remain excluded and the `http` failure category is preserved. The actual
Ollama missing-model request returned the improved message and exit 1.

## Laravel controls and model trials

The original Laravel suite passed **2/2**. Doctor found Laravel, Boost, and MCP
configuration. Preflight required a clean root Git checkout, marker, committed
lockfile, installed dependencies, separate output, and safe benchmark paths.

The real controls-only run passed: baseline exit 0, hidden and visible negative
controls exit 1, independent reference fix passed full assertions and registered
POST, broken source restored, hidden assertions removed, and protected `.env`
unchanged. Home and unrelated route survival are asserted by the hidden suite.
Reference fixes are evaluator-owned controls and never count as model successes.

Each Composer smoke task uses a separate disposable Laravel-style fixture with
an unknown random package name and a `^12.0` framework constraint. The package
name is absent from both task prompt and automatic project summary. Dependencies
can appear in automatic context; therefore the unseen name plus a successful
file-read event is required, rather than accepting a version-only answer. The edit and route-inspection tasks use the
real installed Laravel 13.42.0 application. These are distinct evaluation tasks.

| Validation budget / guidance | Trials | Factual Composer inspection | Independent edit passes | PHP lint passes | Successful post-final-edit tests |
|---|---:|---:|---:|---:|---:|
| 8 / off | 3 | 3/3 | 0/3 | 0/3 | 0/3 |
| 8 / checklist | 3 | 3/3 | 0/3 | 0/3 | 0/3 |
| 12 / off | 3 | 3/3 | 0/3 | 0/3 | 0/3 |
| 12 / checklist | 3 | 3/3 | 0/3 | 0/3 | 0/3 |

The eight-round comparer returned `paired_inputs: true`, three trials, and zero
pass-count delta for both inspection and Laravel edits. Each arm made 24 write-task
tool attempts: 15 successful reads/writes and nine failed test-command executions.
All six trials read the required files before editing, preserved write scope and
`.env`, then exhausted their budget without a final response. Model-generated
PHP used quoted strings in formal parameter positions, causing parse errors.
There was no evidence of a runtime double-escaping defect. The twelve-round
comparison also returned `paired_inputs: true`, three complete trials in each arm,
and zero success-count delta. Each twelve-round arm made 36 write-task tool
attempts: 21 successful reads/writes and 15 failed test-command executions.
All twelve validation edits failed PHP lint and exhausted their model/tool budget.
There were no malformed action, missing pre-edit read, transport, or scope failures
in these validation campaigns. All 48 attempted test commands actually ran and
failed; they were not permission denials. No successful post-final-edit test or
independent acceptance result was observed. The current reference gate passed
13/13 executions (one separate controls-only run plus twelve trial controls), so
the previously reported intermittent control error did not recur in this campaign.

Observed mean write-task durations were 44.0 seconds (8/off), 43.9 (8/checklist),
67.8 (12/off), and 71.2 (12/checklist), excluding worktree setup and independent
acceptance. These are observed timings, not controlled performance estimates.
Neither the checklist nor the larger round budget improved the repair pass count.

The health scenario, with checklist guidance and sibling-route preservation,
passed **3/3 actual model-generated edits**. Each write task made three successful
tool calls (read, write, exact-argv test), produced a final answer, passed PHP lint,
registered the route, and passed the independent full suite: **5 tests, 7
assertions per trial**. Home, sibling route, write scope, and `.env` survived.
Observed write-task durations were 12.938, 13.000, and 13.391 seconds. This proves
these specific small edits, not general autonomous coding reliability.

The repair scenario, also using checklist guidance and sibling preservation,
passed **3/3 actual model-generated fixes**. Each model read both route and visible
regression test before editing, changed only the route, executed the permitted
test command after the final edit, and returned a final answer. Each independent
suite passed **6 tests, 9 assertions**, with valid PHP, registered route, preserved
home/sibling routes, unchanged visible test, and unchanged `.env`. Each write task
made four successful calls; durations were 14.812, 14.875, and 14.750 seconds.

Across the separate smoke tasks, factual inspections passed 18/18 with real reads.
The original Laravel baseline remained clean at its original commit after all
evaluations. These small task counts establish observed functionality, not a
general coding-success rate.

## Boost MCP and safety checks

Real Boost initialized, advertised two configured read-only tools with object
input schemas, and returned a successful direct `database-connections` result.
The response was discarded, not written to this report or persistent memory.
Three native 3B agent trials emitted **zero raw native tool calls** and completed
**zero MCP tools**. None returned the expected fact. Discovery and direct transport
work; native model tool selection remains unproven. No agent dispatch can occur
when the model emits no native calls. The server subprocess exited after close.

Windows regression tests verified failed MCP initialization cleanup and sanitized
JSON-RPC errors using scripted servers; these are protocol/security tests, not
real Laravel success evidence. Actual disposable local-tool probes also verified
default write/execute denial, successful exact-argv execution, changed-argv denial,
and traversal/symlink write rejection. Fenced JSON and unknown actions were
rejected. Verbose events contained only permitted metadata. SQLite set/get/delete
also worked across separate installed-wheel CLI processes.

The runtime remains an experimental agent, not an OS sandbox. Exact argv does not
contain indirect project-script effects, and configured MCP servers are separately
trusted processes. These limitations remain documented.

## Resource observations and platforms

A live snapshot showed 15.63 GiB visible RAM with 1.34 GiB free and the RTX 3050
Laptop GPU using 2,151/4,096 MiB VRAM. These are snapshots, not peak or isolated
process measurements. Model/cache state and machine load were not controlled.
Paired inputs do not imply matched model randomness or latency conditions.
The final snapshot showed 0.50 GiB free RAM, the same GPU use, and Ollama reporting
2,159,374,499 bytes resident entirely on GPU with context length 4096. Memory
pressure was high; no inference timeout or transport failure was observed.

Windows 11/Python 3.12 received real packaging, Ollama, PHP, and MCP checks.
Ubuntu Python 3.10/3.12/3.13 received CI tests and packaging checks. macOS,
other Windows/Python combinations, and other model servers were not validated.

## Changes and next release step

Verified changes were limited to `MANIFEST.in`, `.github/workflows/ci.yml`,
`.gitignore`, `docs/QUICKSTART.md`, `tinybuilder/model.py`, `tests/test_model.py`,
the release checklist, and this sanitized report. Historical reports were left
unchanged. The fixes are [source packaging and Windows setup](https://github.com/MrPunyapal/TinyBuilder/commit/469243fccfe28f0024bd285da8d515c5d4ce987e)
and [HTTP stream cleanup and diagnostics](https://github.com/MrPunyapal/TinyBuilder/commit/0bd6ede8787c0951a7b52383676f273ad84554d7).

The public preview should lead with the verified constrained read-only example
and opt-in permissions. Disclose unreliable validation edits and unproven native
MCP selection prominently. Retain all local worktrees for review. Before expanding
capability claims, evaluate 20–50 pinned tasks and investigate the parameter-syntax
failures and native model outputs using controlled experiments. Monitor the
historical reference-control issue; its absence in this campaign does not prove
it can never recur. Do not train Soup or redistribute weights based on this
small evaluation. Any official release publication requires separate maintainer
authorization.

## Reproduction

Run from a clone in PowerShell. Use an already installed model, and set `$app`
to your own clean, marked disposable Laravel baseline. Never substitute a
personal or production project. Seeds, hidden values, model answers, and local
artifact paths are deliberately excluded from this report.

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py -m pip install -e .
& $py -m unittest discover -s tests -v
& $py -m compileall -q tinybuilder benchmarks
& $py -m tinybuilder doctor --project .
& $py -m pip install build
$dist = Join-Path $env:TEMP ('tb-dist-' + [guid]::NewGuid().ToString('N'))
& $py -m build --sdist --wheel --outdir $dist

& $py -m tinybuilder chat 'Use read_file to inspect pyproject.toml and report the project name.' --project . --model qwen2.5-coder:3b --tool-protocol strict-json --strict-json-profile constrained --verbose

$app = '<clean marked disposable Laravel baseline>'
$phpExe = php -r 'echo PHP_BINARY;'
$env:PATH = (Split-Path $phpExe) + ';' + $env:PATH
$controls = Join-Path $env:TEMP ('tb-controls-' + [guid]::NewGuid().ToString('N'))
& $py benchmarks\evaluate.py --scenario validation --controls-only --laravel $app --php $phpExe --preserve-sibling-route --output $controls
if ($LASTEXITCODE -ne 0) { throw 'Controls failed; stop inference' }

foreach ($steps in @(8,12)) {
  $seed = [guid]::NewGuid().ToString('N')
  $base = Join-Path $env:TEMP ('tb-base-' + [guid]::NewGuid().ToString('N'))
  $guided = Join-Path $env:TEMP ('tb-guided-' + [guid]::NewGuid().ToString('N'))
  $common = @('--scenario','validation','--preserve-sibling-route',
    '--models','qwen2.5-coder:3b','--tool-protocol','strict-json',
    '--strict-json-profile','constrained','--trials','3',
    '--max-steps',"$steps",'--fixture-seed',$seed,'--laravel',$app,'--php',$phpExe)
  & $py benchmarks\evaluate.py @common --output $base
  if (!(Test-Path (Join-Path $base 'results.json')) -or
      (Get-Content (Join-Path $base 'results.json') -Raw | ConvertFrom-Json).trials.Count -ne 3) {
    throw 'Incomplete base report; stop and diagnose the harness/control failure'
  }
  & $py benchmarks\evaluate.py @common --progress-guidance checklist --output $guided
  if (!(Test-Path (Join-Path $guided 'results.json')) -or
      (Get-Content (Join-Path $guided 'results.json') -Raw | ConvertFrom-Json).trials.Count -ne 3) {
    throw 'Incomplete checklist report; stop and diagnose the harness/control failure'
  }
  & $py benchmarks\compare.py --baseline (Join-Path $base 'results.json') --candidate (Join-Path $guided 'results.json')
}

foreach ($scenario in @('health','repair')) {
  $out = Join-Path $env:TEMP ('tb-' + $scenario + '-' + [guid]::NewGuid().ToString('N'))
  & $py benchmarks\evaluate.py --scenario $scenario --preserve-sibling-route --models qwen2.5-coder:3b --tool-protocol strict-json --strict-json-profile constrained --progress-guidance checklist --trials 3 --laravel $app --php $phpExe --output $out
}

# For a trusted, read-only Boost configuration, inspect native tool_end events.
& $py -m tinybuilder chat 'Use the connected Laravel Boost database-connections MCP tool to inspect this project. Call the actual tool, then report the default database connection. Do not edit files or execute commands.' --project $app --model qwen2.5-coder:3b --mcp-config examples/mcp.json --verbose
```

Exit 1 from a complete evaluator report can represent a model task failure.
Inspect completeness and the safety/control gate before continuing or comparing.
Use fresh output directories for every run; retain worktrees for local review.
