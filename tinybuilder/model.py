"""Minimal OpenAI-compatible chat client. No third-party Python dependencies."""

import json
import ipaddress
from dataclasses import dataclass, field
from urllib.parse import urlsplit
import urllib.error
import urllib.request
from typing import Any


class ModelError(RuntimeError):
    def __init__(self, message: str, kind: str = "response_protocol"):
        self.kind = kind
        super().__init__(message)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class ManagedConnection:
    base_url: str
    model_alias: str
    api_key: str = field(repr=False)


class ChatModel:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: int = 120, *,
                 backend: str = "openai", managed: bool = False):
        if backend not in ("openai", "llamacpp"):
            raise ValueError("Unknown inference backend")
        try:
            parsed = urlsplit(base_url)
            if (parsed.scheme not in ("http", "https") or not parsed.hostname
                    or parsed.username is not None or parsed.password is not None
                    or parsed.query or parsed.fragment):
                raise ValueError
            if managed and (not ipaddress.ip_address(parsed.hostname).is_loopback
                            or not parsed.port or not api_key or not model
                            or parsed.path.rstrip("/") not in ("", "/v1")):
                raise ValueError
        except ValueError:
            raise ModelError("Invalid model server URL or managed credentials", "configuration") from None
        self.backend = backend
        self.base_url = base_url.rstrip("/")
        if managed and not self.base_url.endswith("/v1"):
            self.base_url += "/v1"
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    @classmethod
    def from_managed(cls, connection: ManagedConnection, timeout: int = 120):
        return cls(connection.base_url, connection.model_alias, connection.api_key,
                   timeout, backend="llamacpp", managed=True)

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                 response_format: dict[str, Any] | None = None, *,
                 cancel_event=None) -> dict[str, Any]:
        if cancel_event is not None and cancel_event.is_set():
            raise ModelError("Generation cancelled", "cancelled")
        payload = {"model": self.model, "messages": messages, "stream": False, "temperature": 0.1}
        if response_format is not None:
            if self.backend == "llamacpp" and response_format.get("type") == "json_schema":
                if tools:
                    raise ModelError("Constrained generation cannot include native tools", "configuration")
                envelope = response_format.get("json_schema")
                if not isinstance(envelope, dict) or not isinstance(envelope.get("schema"), dict):
                    raise ModelError("Invalid constrained schema envelope", "configuration")
                payload["response_format"] = {"type": "json_schema", "schema": envelope["schema"]}
            else:
                payload["response_format"] = response_format
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        url = self.base_url + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = "Bearer " + self.api_key
        request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                data = json.load(response)
        except urllib.error.HTTPError as exc:
            # HTTP error bodies may echo prompts, source contents and credentials.
            message = f"Model server HTTP {exc.code}"
            if exc.code == 404:
                message += "; check the installed model name and API base URL"
            # urlopen raises before its response context manager is entered.
            # Close the unread error stream without exposing the server body.
            exc.close()
            kind = "authentication" if exc.code in (401, 403) else "http"
            if self.backend == "llamacpp" and response_format is not None and exc.code in (400, 422):
                message += "; constrained request rejected (schema or other request parameters)"
            raise ModelError(message, kind) from exc
        except TimeoutError:
            raise ModelError("Model server request timed out", "timeout") from None
        except urllib.error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise ModelError("Model server request timed out", "timeout") from None
            raise ModelError("Cannot reach the configured model server", "connectivity") from None
        except OSError as exc:
            raise ModelError("Cannot reach the configured model server", "connectivity") from None
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ModelError("Model server returned invalid JSON", "response_protocol") from None
        if cancel_event is not None and cancel_event.is_set():
            raise ModelError("Generation cancelled", "cancelled")
        try:
            choice = data["choices"][0]
            message = choice["message"]
            finish = choice.get("finish_reason")
            if finish == "length":
                raise ModelError("Generation truncated by token or context limit", "generation_limit")
            if finish not in (None, "stop", "tool_calls", "function_call"):
                raise ModelError("Model generation did not finish successfully", "response_protocol")
        except (KeyError, IndexError, TypeError, AttributeError) as exc:
            raise ModelError("Model response lacks choices[0].message") from None
        if not isinstance(message, dict) or message.get("role", "assistant") != "assistant":
            raise ModelError("Model message is not an assistant object")
        if not isinstance(message.get("content"), (str, type(None))):
            raise ModelError("Model message content must be text or null")
        if "tool_calls" in message and message["tool_calls"] is not None and not isinstance(message["tool_calls"], list):
            raise ModelError("Model tool_calls field must be a list")
        return message
