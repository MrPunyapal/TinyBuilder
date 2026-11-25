"""Integration adapter for the three owned dependency packages.

Dependency imports are deferred until constructing a production service.
No fallback, download or runtime launch happens on construction.
"""
from threading import Event, Thread

from .agent_backend import AgentBackend
from .session import Cancelled, CleanupRequired, DownloadOffer


class _Token:
    def __init__(self, event):
        self.event = event

    def check(self):
        if self.event.is_set():
            raise Cancelled()


class ManagedServices:
    """Adapt the published ModelManager, RuntimeManager and ChatModel APIs."""

    def __init__(self, models, runtime, model_factory, approve):
        self.models = models
        self.runtime = runtime
        self.model_factory = model_factory
        self.approve = approve

    @classmethod
    def from_installation(cls, runtime_root, approve, storage_dir=None):
        # These imports intentionally fail closed until the dependency PRs land.
        from ..models.manager import ModelManager
        from ..runtime.manager import RuntimeManager
        from ..model import ChatModel
        return cls(ModelManager(storage_dir), RuntimeManager(runtime_root),
                   ChatModel.from_managed, approve)

    def offers(self):
        return tuple(DownloadOffer(entry.model_id, entry.size_bytes,
                                   self.models.destination(entry.model_id),
                                   entry.license, entry.sha256)
                     for entry in self.models.catalog)

    def transfer(self, offer, cancel, progress):
        if offer not in self.offers():
            raise ValueError("Catalog or destination changed; obtain fresh consent")
        token = _Token(cancel)
        token.check()
        request = self.models.request_download(offer.model_id, consent=True)
        entry = request.entry
        if (entry.model_id, entry.size_bytes, request.destination, entry.license, entry.sha256) != (
                offer.model_id, offer.size_bytes, offer.destination, offer.license, offer.sha256):
            raise ValueError("Download request changed; obtain fresh consent")
        def notify(update):
            token.check()
            if update.total_bytes != offer.size_bytes:
                raise ValueError("Unexpected transfer length")
            progress(update.received_bytes)
        result = self.models.download(request, progress=notify, cancellation=token)
        token.check()
        if result.provenance != "catalog-verified" or result.catalog_id != offer.model_id:
            raise ValueError("Model manager did not verify download")
        return result.path

    def start(self, model_path, backend, cancel):
        token = _Token(cancel)
        token.check()
        selection = self.models.select_local(model_path)
        token.check()
        # User-provided GGUFs are header-checked, not digest qualified. The
        # frontend must clearly disclose this before startup.
        done = Event()

        def relay():
            while not done.wait(0.05):
                if cancel.is_set():
                    self.runtime.cancel()

        watcher = Thread(target=relay, name="tinybuilder-start-cancel")
        watcher.start()
        try:
            try:
                connection = self.runtime.start(selection.path, backend=backend)
                model = self.model_factory(connection)
                return AgentBackend(model, self.runtime.stop, self.approve)
            except BaseException:
                # Retain cleanup ownership if runtime startup or client setup
                # failed after spawning an owned child.
                try:
                    self.runtime.stop()
                except Exception:
                    raise CleanupRequired(AgentBackend(None, self.runtime.stop, self.approve)) from None
                raise
        finally:
            done.set()
            watcher.join()
