"""Connect the existing Agent to a managed model and application approvals.

Runtime ownership remains with the injected close callback. The model must be
the authenticated local client from the inference workstream, supporting the
cancel_event keyword. There is no fallback to an external endpoint.
"""
from threading import Event
from typing import Callable, Protocol

from ..agent import Agent
from .approvals import Approval, ApprovedTools
from .session import Cancelled, Permissions


class CancellableModel(Protocol):
    def complete(self, messages, tools, response_format=None, *, cancel_event: Event):
        ...


class _TaskModel:
    def __init__(self, model, cancel):
        self.model, self.cancel = model, cancel

    def complete(self, messages, tools, response_format=None):
        if self.cancel.is_set():
            raise Cancelled()
        reply = self.model.complete(messages, tools, response_format=response_format,
                                    cancel_event=self.cancel)
        if self.cancel.is_set():
            raise Cancelled()
        return reply


class AgentBackend:
    """RunningBackend implementation using existing agent and local tools."""

    def __init__(self, model: CancellableModel, close: Callable[[], None],
                 approve: Callable[[Approval], bool]):
        self._model, self._close, self._approve = model, close, approve

    def run(self, project, task, permissions: Permissions, protocol, cancel, activity):
        if protocol not in ("native", "strict-json"):
            raise ValueError("Unknown protocol")
        if cancel.is_set():
            raise Cancelled()
        local = ApprovedTools(project, permissions, cancel, self._approve)

        def event(data):
            if cancel.is_set():
                raise Cancelled()
            if data.get("event") == "model_start":
                activity("model")
            elif data.get("event") == "tool_start":
                activity(data.get("tool", "tool"))

        agent = Agent(_TaskModel(self._model, cancel), local,
                      on_event=event, tool_protocol=protocol,
                      strict_json_profile="constrained" if protocol == "strict-json" else "prompt")
        answer = agent.run(task)
        if cancel.is_set():
            raise Cancelled()
        return answer

    def close(self):
        self._close()
