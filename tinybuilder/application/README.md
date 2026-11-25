# Application orchestration (draft)

The existing CLI and unpublished terminal prototype are not replaced. Session
is a framework-neutral, in-memory service. Frontends run download, start,
run_task and stop on a worker and poll immutable snapshots. Only one operation
is allowed; cancel signals the operation's Event, and cancelling remains
visible until the operation returns. Join the worker before closing the UI.
No network, model, or runtime implementations are duplicated.

DownloadOffer includes exact byte count, destination, license and pinned digest.
The frontend must present these and obtain fresh explicit consent. Transfer
adapters verify the GGUF and digest, manage resumable partials, honor cancellation
and return the verified path only after resources are released. The application
checks destination and size, not binary integrity. Existing file selection is
path validation only; the start factory must verify the model before launch.

Runtime discovery supplies backend IDs. The start factory owns cleanup on
failure before returning a RunningBackend. The handle owns inference and
runtime cleanup; close must be retryable, and failure retains ownership in
cleanup_failed. The application closes late handles after cancelled startup.
The run method receives one-task permissions, project, protocol and cancellation
token. Map strict-json to constrained profile; native remains default. A run must
return only after inference and tools are no longer active. Cancellation is
cooperative: blocking HTTP or subprocesses may remain pending until adapters
return. Do not advertise immediate interruption. Activity accepts only fixed
tool labels, never tool arguments. Answers are returned to the frontend, not
stored by the service.

Permissions are explicitly set by the user for the next task, then reset on
dispatch; use LocalTools exact argv allowlist (not a sandbox). Project switching
requires stopping the owned backend first and revokes permissions and protocol
selection. ApprovedTools adds per-action approval to the existing LocalTools without
changing legacy CLI behavior. It requires task permission AND explicit approval,
rejects oversized previews, and checks for file changes during approval. Its
callback runs on the worker: frontend must render untrusted text safely and
unblock the request on cancellation. The underlying filesystem and subprocess
operations are not atomic or sandboxed. AgentBackend constructs this gate for each task and wraps the existing Agent,
forwarding cancel_event to the injected managed model and checking cancellation
before tool dispatch. Runtime/model manager wiring and frontend approval callback
remain pending. MCP is not configured by this adapter.

PR 3 backend exposes ChatModel.from_managed and a cancel_event argument but
currently checks cancellation around a blocking request; the application adapter stops subsequent tool dispatch but cannot interrupt an
already blocking HTTP call or subprocess. ManagedServices adapts the published ModelManager/RuntimeManager interfaces
and ChatModel.from_managed, using deferred imports until integration. Startup
cancellation is relayed to RuntimeManager.cancel while the worker is active.
Progress may decrease on a restarted download. Failed factory cleanup retains
an owned handle for retry. No actual runtime/model execution has been verified. No production test double or automatic model download is provided.
Keep draft until real integration and preserved prototype terminal acceptance.

## Frontend wiring

Create Session and Worker, then ManagedServices.from_installation with the
trusted runtime directory and worker.approve as the callback. Use worker.start,
download, task and stop; poll session.snapshot(), worker.pending() and
worker.take_result() from the UI event loop. Display pending Approval as plain
text (escape all path and argv control characters), then call worker.respond
with the exact sequence and explicit decision. Ctrl+C calls worker.cancel;
continue polling until completion. Consume every result. Disable session
settings changes while busy. Do not close or exit until backend stop succeeds.
Do not save answers, diffs or approval requests.

The frontend must display the experimental status, project path, verified vs
user-provided model provenance, consent metadata, current phase, permissions,
activity and sanitized error. Only CPU is currently qualified by runtime
interface; no auto-fallback. The existing unpublished renderer is not replaced.
