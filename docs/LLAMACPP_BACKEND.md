# llama.cpp b6500 compatibility qualification

Pinned source: [utils.hpp lines 568–579](https://github.com/ggml-org/llama.cpp/blob/b6500/tools/server/utils.hpp#L568-L579), [server.cpp lines 411–419](https://github.com/ggml-org/llama.cpp/blob/b6500/tools/server/server.cpp#L411-L419), [grammar converter](https://github.com/ggml-org/llama.cpp/blob/b6500/common/json-schema-to-grammar.cpp#L805-L819). The source reads the nested OpenAI schema for type json_schema; the README's flat example does not match that branch. The converter handles oneOf/const, but actual full schema grammar acceptance is not established by source inspection.

Integration: ChatModel.from_managed(connection, timeout=120) accepts the runtime RuntimeConnection structurally (base_url, model_alias, api_key). Numeric loopback HTTP with explicit port only; root or /v1 normalized. No proxies or redirects for either backend; existing external direct OpenAI/Ollama calls keep their envelope and native default. Do not serialize the descriptor. Pass cancel_event=threading.Event() to complete. Cancellation checks occur before open, after headers, after each read1 chunk and before returning the response; blocked header/body I/O waits for the configured socket inactivity timeout. Deadline checked at checkpoints, not a hard wall-clock guarantee for trickling headers or DNS. No streaming or server-side abort guarantee. Application owns cancellation checks immediately before dispatch and runtime owns server teardown. Responses capped at 2 MiB; incomplete responses and managed missing finish reason rejected.

## Real server probe (explicitly provisioned models only)

Start the already installed b6500 server through the runtime owner or an existing local server using an existing GGUF, --jinja, numeric loopback, alias and transient LLAMA_API_KEY. Check llama-server --version. Do not download weights. From repository root run:

    python tests/probe_llamacpp.py

The script prompts for base URL, alias and hidden API key. It makes one exact constrained request (no tools) and independently validates the resulting action; no action is executed. It then runs an actual Agent read-only task in a disposable project containing a random fact, for native and constrained modes. Only outcome categories and counts are printed. HTTP acceptance, valid action, successful tool execution and exact final fact are separate. A failure is not evidence of unsupported schema unless diagnosed from pinned server source or sanitized server diagnostics. Repeat with the selected GGUFs; qualification owner owns broader randomized acceptance.

Regression: python -m unittest discover -s tests -v
