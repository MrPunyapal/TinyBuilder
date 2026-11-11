"""Minimal OpenAI-compatible chat client. No third-party Python dependencies."""

import json
import urllib.error
import urllib.request
from typing import Any


class ModelError(RuntimeError):
    def __init__(self, message: str, kind: str = "response_protocol"):
        self.kind = kind
        super().__init__(message)


class ChatModel:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                 response_format: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"model": self.model, "messages": messages, "stream": False, "temperature": 0.1}
        if response_format is not None:
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
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
        except urllib.error.HTTPError as exc:
            # HTTP error bodies may echo prompts, source contents and credentials.
            raise ModelError(f"Model server HTTP {exc.code}", "http") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ModelError("Cannot reach the configured model server", "connectivity") from exc
        except (json.JSONDecodeError, UnicodeError) as exc:
            raise ModelError("Model server returned invalid JSON", "response_protocol") from exc
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError("Model response lacks choices[0].message") from exc
        if not isinstance(message, dict) or message.get("role", "assistant") != "assistant":
            raise ModelError("Model message is not an assistant object")
        if not isinstance(message.get("content"), (str, type(None))):
            raise ModelError("Model message content must be text or null")
        if "tool_calls" in message and message["tool_calls"] is not None and not isinstance(message["tool_calls"], list):
            raise ModelError("Model tool_calls field must be a list")
        return message
