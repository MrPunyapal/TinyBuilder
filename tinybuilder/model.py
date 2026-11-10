"""Minimal OpenAI-compatible chat client. No third-party Python dependencies."""

import json
import urllib.error
import urllib.request
from typing import Any


class ModelError(RuntimeError):
    pass


class ChatModel:
    def __init__(self, base_url: str, model: str, api_key: str = "", timeout: int = 120):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout

    def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {"model": self.model, "messages": messages, "stream": False, "temperature": 0.1}
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
            body = exc.read(1000).decode("utf-8", "replace")
            raise ModelError(f"Model server HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise ModelError(f"Cannot reach model at {url}: {exc}") from exc
        try:
            return data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError("Model response lacks choices[0].message") from exc
