# Windows parameter scenario and native MCP follow-up — 2026-11-16

TinyBuilder retains its documented **public experimental preview** classification.
This focused retest does not establish stable or production readiness. Historical
benchmark reports were preserved; the completed health/repair and 8/12-round
campaigns were not repeated.

## Source and disposable baseline

- Initial clean local HEAD: `3ac2ce103845bba21a31923198ef7259e793d34f` on `main`.
- Reviewed nine intervening commits and fast-forwarded to the requested
  `286a28a03c87e98a121cdbf26837a4aeb803258b` candidate.
- Verified fixes: workflow setup `c1c0b88b22ea1bd422a6b06453847a8955759c91`
  and parameter acceptance `001c095741f65b130aef8a59d94959b4b3ef3d7b`.
  The final documentation publication SHA is supplied in the accompanying handoff.
- Disposable Laravel baseline: `f8ffe9e7b9bbf8193aabfb2e9e351fd0314b0c43`.
- Full Composer lock SHA-256:
  `ecac92821889d2069e13dd0c79b1ac3f03aacd55fc823b066bce9bfabb20e12d`.
- Laravel 13.42.0 / Boost 2.10.4; Windows Python 3.12.14 / PHP 8.5.12;
  local Ollama 0.32.5 and installed `qwen2.5-coder:3b` (digest prefix `f72c60cabf62`).
- Only marked, clean disposable projects and fresh detached worktrees were used.
  No model downloads, paid inference, training, or official release publication.

## Real PHP controls and verified defects

The first Windows parameter control attempt stopped before inference without a
completed report. Its exact failed phase was not retained. Replaying the reference
and restoration checks in that retained worktree passed: 9 real tests / 13
assertions, correct GET registration, restored broken seed failing again, hidden
test removed, and unchanged `.env`. A fresh control then passed. This initial
failure remains unexplained; it is not relabeled as a pass or claimed fixed.
Subsequent runs captured phase exit codes without source or command arguments.

Two independent defects were reproduced and corrected:

1. **Manual workflow setup:** `composer create-project --no-install` still invoked
   Laravel's post-create scripts, which failed because the autoloader was absent.
   The [original manual run failed](https://github.com/MrPunyapal/TinyBuilder/actions/runs/43922276413)
   with exit 255 before controls. A new regression failed before adding
   `--no-scripts` to skeleton creation. Normal dependency-install scripts remain
   enabled. The [corrected manual workflow passed](https://github.com/MrPunyapal/TinyBuilder/actions/runs/43923039468)
   both real validation and parameter reference controls.
2. **Parameter false positives:** the first three actual model edits produced two
   apparent passes under the original assertions. Real additional PHP probes
   showed those edits accepted fractional/exponent numeric forms, contrary to the
   existing integer-only task requirement. The hidden suite omitted those cases.
   A fixture regression failed before adding two independent negative assertions;
   the public prompt, visible test, reference implementation, permissions, and
   model profile were unchanged. The strengthened Windows controls passed, and
   the [strengthened manual PHP workflow also passed](https://github.com/MrPunyapal/TinyBuilder/actions/runs/43925365474).

Rechecking the three original, frozen model edits with the corrected oracle
rejected all three. The two apparent passes each failed two new assertions; the
third failed four assertions, including an incorrect Laravel response API on its
error branch. All three were lint-clean. Source, `.env`, and original hidden-test
bytes were preserved during this recheck. The original local results were retained.
These rechecks are independent PHP acceptance tests, not new model generations.

## Fresh model trials on the corrected evaluator

A new three-trial campaign uses fresh worktrees and seed, eight rounds,
`strict-json`, the constrained profile, and opt-in checklist guidance. Reference
controls passed before every model trial. The result is **0/3 model-generated
parameter edits passed** on the corrected evaluator.

| Trial | PHP lint exit | Independent PHP suite | Write-tool calls | Outcome |
|---|---:|---:|---:|---|
| 1 | 0 | 9/11 tests passed, 2 failed | 4/4 successful | Semantic failure |
| 2 | 0 | 9/11 tests passed, 2 failed | 4/4 successful | Semantic failure |
| 3 | 0 | 9/11 tests passed, 2 failed | 4/4 successful | Semantic failure |

Each suite executed 15 assertions. Each model read source and visible test before
editing, changed only the allowed route, ran the exact allowed test command after
the final edit, and returned a final answer. `.env` and scope checks passed in all
three. All three reported `final_php_tests_failed=true`, `php_parse_error=false`,
no missing reads/tests, no denied argv, no invalid arguments, no nonzero model test
commands, and no round exhaustion. Visible model tests passed; independent hidden
tests correctly rejected the integer-format error. Write-task times were 14.297,
14.485, and 27.922 seconds, without a controlled latency comparison.

The accompanying fresh Composer smoke tasks passed **2/3**, despite successful
`read_file` calls in all three. The failed task was factual, not a missing tool
call. The earlier pre-fix campaign's Composer tasks passed 3/3. These are separate
measurements and do not change historical reports.

## One refreshed validation diagnostic

Exactly one validation trial was run to exercise the new diagnostics on real PHP:

| Signal | Observed result |
|---|---:|
| Independent task pass | false |
| `php_lint_exit` | 255 |
| `diagnostics.php_parse_error` | true |
| `diagnostics.final_php_tests_failed` | true |
| `write.round_exhausted` | true |
| `write.test_command_nonzero_count` | 3 |
| Denied argv / invalid arguments | 0 / 0 |
| Missing pre-edit reads | false |
| Missing successful post-edit test | true |

All eight rounds were consumed; five tool operations succeeded and three test
commands ran but failed. Write scope and `.env` integrity passed. This confirms
a PHP-generation failure and exhausted loop, not a permission or transport failure.

## One actual native MCP experiment

The real CLI was observed without substituting a model or server. Boost initialized
and advertised two read-only tools with valid object schemas. Ollama emitted
**zero raw native tool calls**: zero MCP dispatch attempts and zero successful
MCP `tool_end` events. The experiment therefore passed **0/1 model-selected MCP
tasks**. Exit 0 from chat did not establish tool use. The child process closed
cleanly and no preferences database was created. Model answers and MCP observations
were discarded; scripted native-dispatch tests remain separate protocol evidence.

## Python and GitHub checks

- Initial candidate: **136 Windows Python tests passed**, plus editable install
  and compilation of `tinybuilder` and `benchmarks`.
- Workflow regression: **137 passed**; parameter-contract regression: **138 passed**.
  Both new checks were observed failing before their respective corrections.
- [Final fix Python CI](https://github.com/MrPunyapal/TinyBuilder/actions/runs/43925364827)
  passed on Python 3.10, 3.12, and 3.13, including source-distribution tests.
- The manual PHP workflow executes actual Laravel controls without Ollama; its
  success is not model-generated coding evidence. No new Windows packaging
  campaign was needed; no packaging defect appeared in this focused retest.

## Reproduction and handoff

Use the clean marked disposable `$app` and the already installed model. Keep all
outputs separate from the baseline and do not reuse existing output directories.

```powershell
$py = '.\.venv\Scripts\python.exe'
$phpExe = php -r 'echo PHP_BINARY;'
$env:PATH = (Split-Path $phpExe) + ';' + $env:PATH
$controls = Join-Path $env:TEMP ('tb-param-controls-' + [guid]::NewGuid().ToString('N'))
& $py benchmarks\evaluate.py --scenario parameter --controls-only --laravel $app --php $phpExe --preserve-sibling-route --output $controls
if ($LASTEXITCODE -ne 0) { throw 'Controls failed; stop inference' }
$out = Join-Path $env:TEMP ('tb-param-model-' + [guid]::NewGuid().ToString('N'))
$seed = [guid]::NewGuid().ToString('N')
& $py benchmarks\evaluate.py --scenario parameter --preserve-sibling-route --models qwen2.5-coder:3b --tool-protocol strict-json --strict-json-profile constrained --progress-guidance checklist --max-steps 8 --trials 3 --fixture-seed $seed --laravel $app --php $phpExe --output $out
```

The original Laravel baseline remained clean at its original SHA and lock
fingerprint. All worktrees remain local; original model routes and result reports were preserved;
no model answers, hidden values, private paths, or MCP responses are included here.
The temporary acceptance probes restored the original test/source bytes.

**Remaining limitations:** parameter semantics and native model-selected MCP remain
unsuccessful; the initial control failure remains unexplained. Three trials do
not establish general reliability, and green model-visible tests are insufficient
evidence of task completion.

**One recommended next experiment:** a matched, opt-in parameter-guidance ablation
that explicitly distinguishes integer identifier syntax from general numeric
strings. Keep the corrected hidden oracle, model, permissions, and tool protocol
identical; do not supply reference code or automatically repair model output.
