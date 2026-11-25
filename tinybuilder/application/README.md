# Application foundation (draft)

This package is deliberately independent of terminal libraries. The existing CLI
is unchanged until the local prototype is preserved and reviewed.

Session owns setup state in memory. A frontend runs download on a worker and
polls immutable snapshots; cancel signals the adapter, and close requires the
worker to finish. The transfer callable must be implemented by the model manager
adapter, not by this package. It must validate the GGUF and digest, honor the
event, clean up or preserve resumable partial files, and release resources before
returning. The service checks the consent offer, returned destination and size,
but these checks do not replace model-manager verification.

Pending integration: model validation and catalog; backend selection, runtime
startup and shutdown; agent task cancellation and tool approvals; file change
reporting; terminal rendering and CLI launch. No production test double is
provided. Native is the default; strict-json selection is intended to map to
the constrained profile when the agent adapter is connected. Exact argv is
required for application execution permissions. This is not an OS sandbox.

Do not mark this draft ready until the prototype is preserved and actual
runtime/model/inference interfaces have been reviewed. No transcript storage.
