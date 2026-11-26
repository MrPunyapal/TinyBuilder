# Native 0.1 exact-main rehearsal

The exact candidate source is `9d4343141bab4d710f7d16450105673c994d5c51`.
All five push workflows passed. The three inner archives were checked against
their artifact manifests, and every payload entry was checked against its
build manifest. The checks included executable architecture, pinned runtime
inventory and bundled notices. All three candidates are unsigned and
unnotarized. [Package workflow](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45889820700) ·
[Security evidence](https://github.com/MrPunyapal/TinyBuilder/actions/runs/45889820607)

| Target | Bytes | SHA-256 |
| --- | ---: | --- |
| Windows x64 | 21,950,380 | `9e0bcc34fdcf53784eadc30765e508bf81d631470b92e493209bd0e9e0af812a` |
| Apple Silicon | 27,938,130 | `d9c94d775523c09d18161e456ccc20f87024b3a6271ab6b6ba24ac6e0920d3b3` |
| Linux x64 | 31,004,077 | `defe8b7e142363b8c75d85fb0bab7d7eda7e8b054de56847da6cbe9ed5b875ec` |

The runtime is llama.cpp b12359 at
`b1b770d90d94cad9e9ea5b993bdbc383a522fb28`. The approved existing 1.5B
GGUF is 1,117,320,768 bytes at SHA-256
`cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046`.
[Runtime release](https://github.com/ggml-org/llama.cpp/releases/tag/b12359)

The exact Windows archive passed 10/10 genuine reads with the original
packaged qualification oracle. Median trial time was 4.664 seconds.
Authenticated readiness took 1.843 seconds on normal quit and 1.704 seconds
on forced exit. Both removed the runtime child and its loopback listener.
The run also verified read-only denial, launcher removal, and preservation
of the fixture, package, and model. Server peak working set was about
2.44 GiB during the lifecycle probes.

The Windows machine was elevated and connected and already had the VC++
runtime installed. Standard-user trust prompts and dependency loading on a
clean Windows host remain open, along with offline Ubuntu 22.04 x64 and Apple
Silicon acceptance. The available WSL instance does not qualify as a clean
Linux test machine. Keep the release on hold.
[Sanitized rehearsal evidence](../../benchmarks/results/2026-11-27-exact-main-release.json) ·
[Clean-machine checklist](../CLEAN_MACHINE_ACCEPTANCE.md)

```text
python acceptance/windows_acceptance.py --archive ARCHIVE --artifact-json ARTIFACT_JSON --expected-commit 9d4343141bab4d710f7d16450105673c994d5c51 --expected-archive-sha256 9e0bcc34fdcf53784eadc30765e508bf81d631470b92e493209bd0e9e0af812a --model EXISTING_GGUF --expected-model-sha256 cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046 --output NEW_REPORT_DIR --dev-host
```
