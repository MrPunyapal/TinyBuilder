# TinyBuilder evaluation plan

A functioning tool loop is not evidence that a 0.5B local model can do real Laravel development. Reproducible task-level evaluation is the next priority.

## Task protocol

For each task: start from a pinned Git commit and fixed dependency lockfiles; describe the requested change; run the same configured tests in a disposable worktree/container; capture the diff, test exit code, elapsed time, model/RAM/VRAM use, and number of tool calls. Keep each task's evaluation hidden from the agent where practical.

Proposed JSONL task schema:

```json
{"id":"001","repo":"local/fixture","base_commit":"<sha>","request":"Add GET /health returning JSON","test_command":["php","artisan","test","--filter=HealthEndpointTest"]}
```

This is a proposed benchmark format, **not an executable benchmark harness** yet. Do not add flaky or unpinned tasks. Keep benchmark outcomes separate from training examples and avoid leakage.

## Comparisons

Compare the same tasks across (a) unmodified tiny base model, (b) tiny model with tools+Boost, (c) Soup-fine-tuned version and (d) a larger local or permitted teacher-model reference. Report success rate, tool-call accuracy, time, memory, and security violations. A pass rate should be backed by observable tests, not self-reported completions.
