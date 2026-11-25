# TinyBuilder quick start — experimental preview

TinyBuilder is a **local-first experimental coding agent**, not a production-safe
autonomous programmer or an OS sandbox. It does not ship weights, train models,
or require paid APIs.

## Windows PowerShell

Install Python 3.10+, Git, and Ollama first. Ollama must already have a model
you chose to download; TinyBuilder never downloads weights automatically.
PHP, Composer, and Laravel are optional for general use.

Clone the repository, then create an environment:

```powershell
git clone https://github.com/MrPunyapal/TinyBuilder.git
Set-Location TinyBuilder
py -3 -m venv .venv
```

If `py` is unavailable, use `python -m venv .venv`. If `python` opens the
Microsoft Store, use your installed Python executable's full path:

```powershell
& 'C:\path\to\python.exe' -m venv .venv
```

Continue without activating the environment:

```powershell
$py = '.\.venv\Scripts\python.exe'
& $py -m pip install -e .
& $py -m tinybuilder --help
& $py -m tinybuilder doctor --project .
ollama list
```

A read-only example on this repository, assuming the 3B model is installed:

```powershell
& $py -m tinybuilder chat 'Use read_file to inspect pyproject.toml and report the project name.' --project . --model qwen2.5-coder:3b --tool-protocol strict-json --strict-json-profile constrained --verbose
```

Check `tool_end` for a genuinely successful `read_file` call. Verify the
answer against the file. Model text mentioning a tool does not prove tool use.

Native OpenAI-style tool calling is the **default**. The structured strict-JSON
profile used above is **opt-in**, supports only five local tools, and does
not dispatch MCP tools. Some small models cannot reliably choose native tools.

## Permissions

By default, local file writes and commands are refused.
Grant `--allow-write` only in a trusted disposable project.
Grant `--allow-exec` only when you understand the command being permitted.
You can restrict execution to one **exact argv array**:

```powershell
& $py -m tinybuilder chat 'Run the tests and explain failures.' --project 'C:\path\to\disposable-laravel' --model qwen2.5-coder:3b --tool-protocol strict-json --strict-json-profile constrained --allow-exec --exec-command '["php","artisan","test"]' --verbose
```

Use a marked disposable Laravel project, not a production or personal project.
An allowed executable can have indirect side effects; exact argv is **not**
an OS sandbox. On Windows, Python subprocesses need the real `php.exe`; a
`php.bat` wrapper may not launch with shell-free execution.

Resolve it and prepend its directory to the current PowerShell session's PATH
before using the Laravel example:

```powershell
$phpExe = php -r 'echo PHP_BINARY;'
$env:PATH = (Split-Path $phpExe) + ';' + $env:PATH
```

## Troubleshooting

- **Cannot connect:** ensure Ollama is running and the configured API URL
  points to the local server, default `http://127.0.0.1:11434/v1`.
- **Model not found:** inspect `ollama list` and choose an installed model.
- **No tool events:** a small model may not support the default native protocol;
  opt-in constrained strict JSON is a separate local-tools experiment.
- **Boost not detected:** optional Laravel Boost support requires a real
  Laravel installation and the MCP config. Use **native mode** for MCP.
- **Invalid project:** supply a real directory with `--project`.
- **Untrusted code:** do not grant permissions on a project you do not trust.

Run Python tests with `& $py -m unittest discover -s tests -v`.

On Linux/macOS, use `python3 -m venv .venv` and `.venv/bin/python`.
Ubuntu Python CI does not prove macOS or Windows Ollama/Laravel behavior.

See [Security](SECURITY.md), [Release checklist](RELEASE_CHECKLIST.md),
and [benchmark setup](../benchmarks/README.md).

## Standalone versus source installation

The instructions above are for the existing source CLI, not the future standalone application. For the planned no-Python/no-Git/no-Ollama onboarding flow, see [standalone onboarding](STANDALONE.md). Until a platform artifact has passed acceptance and is explicitly published, use these source instructions if you have the prerequisites. Keep writes and execution disabled for your first inspection.
