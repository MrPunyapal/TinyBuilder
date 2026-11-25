"""Additive portable line frontend; the unpublished prototype is not replaced."""
import json
import time
import unicodedata

from ..application.install import runtime_root
from ..application.managed import ManagedServices
from ..application.session import Permissions, Session
from ..application.worker import Worker


def plain(value):
    return "".join(c if c.isprintable() and unicodedata.category(c)[0] != "C" and c != "\\"
                   else c.encode("unicode_escape").decode("ascii") for c in str(value))


def block(value, write):
    for line in str(value).split("\n"):
        write("| " + plain(line))


class Guided:
    def __init__(self, root, *, read=input, write=print, service_factory=None):
        self.root, self.read, self.write = root, read, write
        self.session = Session()
        self.worker = Worker(self.session)
        self.factory = service_factory or ManagedServices.from_installation

    def yes(self, prompt):
        return self.read(prompt + " [type yes to confirm]: ").strip() == "yes"

    def await_result(self):
        previous = None
        last_approval = None
        cancelled = False
        while True:
            try:
                result = self.worker.take_result()
                if result is not None:
                    state = self.session.snapshot()
                    if result.error or state.error:
                        self.write(plain(state.error or result.error))
                    return None if cancelled else result.value
                state = self.session.snapshot()
                status = (state.phase, state.progress, state.activity)
                if status != previous:
                    detail = state.phase
                    if state.phase == "downloading" and state.offer:
                        detail += f" {state.progress}/{state.offer.size_bytes} bytes"
                    if state.activity:
                        detail += " | " + state.activity
                    self.write(plain(detail))
                    previous = status
                pending = self.worker.pending()
                if pending and pending.sequence != last_approval and not cancelled:
                    last_approval = pending.sequence
                    approval = pending.request
                    self.write("Proposed action: " + plain(approval.tool))
                    if approval.path is not None:
                        self.write("Path: " + plain(approval.path))
                        block(approval.diff or "", self.write)
                    if approval.argv:
                        self.write("Exact argv: " + json.dumps(approval.argv, ensure_ascii=True))
                        self.write("Commands are not sandboxed.")
                    self.worker.respond(pending.sequence, self.yes("Approve this action"))
                time.sleep(0.05)
            except (KeyboardInterrupt, EOFError):
                if self.worker.cancel():
                    cancelled = True
                    self.write("Cancellation requested; waiting for underlying work to finish.")
                else:
                    self.write("Waiting for cleanup to finish.")

    def model_setup(self, services):
        while True:
            choice = self.read("Model: [1] existing GGUF [2] catalog download [q] quit: ").strip()
            if choice == "q":
                return False
            if choice == "1":
                path = self.read("GGUF file path: ")
                self.worker.submit(lambda token: services.inspect_model(path))
                selection = self.await_result()
                if selection is None:
                    continue
                self.write("Model: " + plain(selection.path))
                self.write("Provenance: " + plain(selection.provenance))
                self.write("Catalog identity is not runtime qualification.")
                if not self.yes("Use this model"):
                    continue
                self.session.select_model(selection.path)
                return True
            if choice != "2":
                continue
            offers = services.offers()
            if not offers:
                self.write("No catalog model available; use an existing GGUF.")
                continue
            for i, offer in enumerate(offers, 1):
                self.write(f"{i}. " + plain(offer.model_id) + " (" + plain(offer.qualification) + ")")
            raw = self.read("Catalog model number (blank to go back): ").strip()
            if not raw.isascii() or not raw.isdigit() or len(raw) > 5 or not 1 <= int(raw) <= len(offers):
                continue
            offer = offers[int(raw)-1]
            self.session.offer_download(offer)
            for label, value in (("Model", offer.model_id), ("Filename", offer.filename),
                                 ("Source", offer.source_url), ("Revision", offer.revision),
                                 ("SHA-256", offer.sha256), ("License", offer.license),
                                 ("Qualification", offer.qualification), ("Exact bytes", offer.size_bytes),
                                 ("Destination", offer.destination)):
                self.write(label + ": " + plain(value))
            if not self.yes("Download this exact model to this destination"):
                continue
            self.worker.download(offer, services.transfer)
            if self.await_result() is True:
                self.write("Catalog digest verified; runtime compatibility is not established.")
                return True
            self.write("Retry by selecting the same catalog model, or use an existing GGUF.")

    def settings(self):
        self.write("Permissions apply to the next task only; every mutation requires separate approval.")
        allow_write = self.yes("Allow proposed file writes for next task")
        raw = self.read("Optional exact command argv as JSON array of strings (blank = deny): ")
        try:
            argv = json.loads(raw) if raw.strip() else None
            if argv is not None and not isinstance(argv, list):
                raise ValueError
            self.session.set_permissions(Permissions(allow_write, (tuple(argv),) if argv is not None else ()))
        except (ValueError, TypeError):
            self.session.set_permissions(Permissions())
            self.write("Invalid argv; permissions reset to read-only.")
        self.session.set_constrained(self.yes("Select experimental constrained strict-JSON (otherwise native)"))

    def run(self):
        self.write("TinyBuilder - experimental local coding assistant")
        self.write("Read-only by default. Ctrl+C requests cancellation. No automatic downloads.")
        code = 0
        try:
            while True:
                path = self.read("Project directory (blank = current, q = quit): ")
                if path == "q":
                    break
                try:
                    self.session.select_project(path or ".")
                except (OSError, ValueError, RuntimeError):
                    self.write("Choose an existing accessible project directory.")
                    continue
                self.write("Project: " + plain(self.session.snapshot().project))
                storage = self.read("Model storage directory (blank = platform default): ")
                try:
                    services = self.factory(self.root, self.worker.approve, storage or None)
                except (OSError, ValueError, RuntimeError, ImportError):
                    self.write("Managed dependencies or storage unavailable; check installation.")
                    code = 2
                    break
                if not self.model_setup(services):
                    break
                self.write("Backend: CPU (experimental; accelerator support is not qualified).")
                self.session.select_backend("cpu")
                while True:
                    self.worker.start(services.start)
                    self.await_result()
                    if self.session.snapshot().phase == "ready":
                        break
                    if self.session.snapshot().phase == "cleanup_failed":
                        raise RuntimeError("cleanup required")
                    if not self.yes("Retry model startup"):
                        break
                if self.session.snapshot().phase != "ready":
                    continue
                self.write("Ready. Example: Describe this project's structure without changing files.")
                self.write("Commands: /settings, /project, /quit. Each task is independent.")
                while True:
                    state = self.session.snapshot()
                    self.write("Project: " + plain(state.project) + " | Model: " + plain(state.model))
                    self.write("Protocol: " + state.protocol + " | next task write: "
                               + str(state.permissions.allow_write) + " | allowed commands: "
                               + str(len(state.permissions.exec_commands)))
                    task = self.read("Task: ")
                    if task == "/settings":
                        self.settings()
                    elif task in ("/quit", "/project"):
                        self.worker.stop()
                        if self.await_result() is not True:
                            raise RuntimeError("cleanup required")
                        if task == "/quit":
                            return 0
                        break
                    elif task.strip():
                        self.worker.task(task)
                        answer = self.await_result()
                        if answer is not None:
                            self.write("Model response (untrusted):")
                            block(answer, self.write)
        except (EOFError, KeyboardInterrupt):
            self.write("Exit requested.")
        except (OSError, RuntimeError, ValueError):
            self.write("Application operation failed; check installation and retry.")
            code = 1
        finally:
            if self.worker.busy():
                self.worker.cancel()
                self.await_result()
            else:
                self.worker.take_result()
            if self.session.snapshot().phase in ("ready", "cleanup_failed"):
                self.worker.stop()
                if self.await_result() is not True:
                    self.write("Backend cleanup failed; runtime exit cleanup will retry. Do not assume it stopped.")
                    code = 1
            if self.session.snapshot().phase != "cleanup_failed":
                self.session.close()
        return code


def launch(explicit=None):
    try:
        root = runtime_root(explicit)
    except (OSError, ValueError, RuntimeError):
        print("TinyBuilder experimental: trusted runtime missing. From source, use app --runtime-root ABSOLUTE_DIRECTORY.")
        return 2
    return Guided(root).run()
