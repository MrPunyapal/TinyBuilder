"""Fail-closed parsing for opt-in strict JSON actions and local tool arguments.

This is deliberately not a parser for markdown, XML, Python or shell snippets.
No untrusted model text becomes a tool action without passing these checks.
"""

import json
from typing import Any

from .tools import SPECS

MAX_ACTION_BYTES = 64_000
LOCAL_SCHEMAS = {spec["function"]["name"]: spec["function"]["parameters"] for spec in SPECS}


def strict_response_format() -> dict[str, Any]:
    """Request constrained generation; the independent parser still validates it."""
    branches = [{"type": "object", "properties": {
        "type": {"const": "final"}, "content": {"type": "string"}},
        "required": ["type", "content"], "additionalProperties": False}]
    for name, schema in LOCAL_SCHEMAS.items():
        branches.append({"type": "object", "properties": {
            "type": {"const": "tool"}, "name": {"const": name}, "arguments": schema},
            "required": ["type", "name", "arguments"], "additionalProperties": False})
    return {"type": "json_schema", "json_schema": {
        "name": "tinybuilder_action", "strict": True, "schema": {"oneOf": branches}}}


class ProtocolError(ValueError):
    """A rejected model action. `code` contains only a fixed, safe category."""

    def __init__(self, code: str):
        self.code = code
        super().__init__("Rejected model action: " + code)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ProtocolError("duplicate_key")
        obj[key] = value
    return obj


def parse_json_object(raw: str, maximum: int = MAX_ACTION_BYTES) -> dict[str, Any]:
    """Require exactly one JSON object, no prose/fences, no duplicate keys."""
    if not isinstance(raw, str) or len(raw.encode("utf-8")) > maximum:
        raise ProtocolError("oversized_response")
    if not raw.lstrip().startswith("{"):
        raise ProtocolError("not_json_object")
    try:
        result = json.loads(raw, object_pairs_hook=_unique_pairs)
    except ProtocolError:
        raise
    except (ValueError, TypeError, RecursionError) as exc:
        raise ProtocolError("malformed_json") from exc
    if not isinstance(result, dict):
        raise ProtocolError("not_json_object")
    return result


def validate_local_arguments(name: str, args: Any) -> dict[str, Any]:
    """Enforce required fields, no extras and exact JSON types before calling LocalTools.

    LocalTools independently enforces permissions, project roots and size limits.
    """
    if name not in LOCAL_SCHEMAS:
        raise ProtocolError("unknown_tool")
    schema = LOCAL_SCHEMAS[name]
    if not isinstance(args, dict):
        raise ProtocolError("argument_shape")
    allowed = schema["properties"]
    if set(args) != set(schema["required"]):
        raise ProtocolError("argument_keys")
    for key, spec in allowed.items():
        val = args[key]
        if spec["type"] == "string":
            if not isinstance(val, str) or (key != "content" and not val.strip()):
                raise ProtocolError("argument_type")
            if key == "query" and len(val) > 200:
                raise ProtocolError("argument_size")
            if key == "path" and len(val) > 4096:
                raise ProtocolError("argument_size")
            if key == "content" and len(val.encode("utf-8")) > 250_000:
                raise ProtocolError("argument_size")
        elif spec["type"] == "array":
            if not isinstance(val, list) or not 1 <= len(val) <= 25 or not all(
                isinstance(item, str) and bool(item) for item in val
            ):
                raise ProtocolError("argument_type")
        else:
            raise ProtocolError("unsupported_schema")
    return args


def parse_strict_action(content: Any) -> dict[str, Any]:
    """Opt-in protocol: {type:tool,name,arguments} or {type:final,content}.

    Only the five local tools are available; MCP stays on native tool calling.
    """
    obj = parse_json_object(content)
    kind = obj.get("type")
    if kind == "tool":
        if set(obj) != {"type", "name", "arguments"}:
            raise ProtocolError("action_keys")
        if not isinstance(obj["name"], str) or obj["name"] not in LOCAL_SCHEMAS:
            raise ProtocolError("unknown_tool")
        validate_local_arguments(obj["name"], obj["arguments"])
        return obj
    if kind == "final":
        if set(obj) != {"type", "content"}:
            raise ProtocolError("action_keys")
        if not isinstance(obj["content"], str) or not obj["content"].strip() or len(obj["content"].encode("utf-8")) > MAX_ACTION_BYTES:
            raise ProtocolError("invalid_final")
        return obj
    raise ProtocolError("unknown_action")


def validate_native_calls(calls: Any, step: int = 0) -> list[dict[str, Any]]:
    """Check the entire native call batch before allowing any side effects."""
    if not isinstance(calls, list) or not 1 <= len(calls) <= 8:
        raise ProtocolError("native_call_shape")
    normalized: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, call in enumerate(calls):
        if not isinstance(call, dict) or not isinstance(call.get("function"), dict):
            raise ProtocolError("native_call_shape")
        if call.get("type", "function") != "function":
            raise ProtocolError("native_call_shape")
        function = call["function"]
        if not isinstance(function.get("name"), str) or not function["name"]:
            raise ProtocolError("native_call_shape")
        raw = function.get("arguments")
        if isinstance(raw, str):
            args = parse_json_object(raw, 250_000)
        elif isinstance(raw, dict):
            args = raw
        else:
            raise ProtocolError("argument_shape")
        name = function["name"]
        if name in LOCAL_SCHEMAS:
            validate_local_arguments(name, args)
        elif len(json.dumps(args, ensure_ascii=False).encode("utf-8")) > 64_000:
            raise ProtocolError("argument_size")
        ident = call.get("id")
        if ident is not None and (not isinstance(ident, str) or not ident or len(ident) > 200):
            raise ProtocolError("native_call_shape")
        ident = ident or f"tinybuilder_{step}_{index}"
        if ident in ids:
            raise ProtocolError("duplicate_call_id")
        ids.add(ident)
        normalized.append({"id": ident, "type": "function",
                           "function": {"name": name, "arguments": json.dumps(args, ensure_ascii=False)}})
    return normalized
