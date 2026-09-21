"""LLM-to-engineering tool bridge.

This module is an integration seam only. It does not execute tools, authorize
actions, or import the HOARE-CORE runtime. A caller supplies the governed
dispatcher explicitly.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping


@dataclass(frozen=True)
class LLMToolCall:
    """Validated, execution-neutral tool call emitted by an LLM."""

    call_id: str
    tool_name: str
    arguments: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.call_id.strip():
            raise ValueError("call_id is required")
        if not self.tool_name.strip():
            raise ValueError("tool_name is required")
        if not isinstance(self.arguments, Mapping):
            raise TypeError("arguments must be a mapping")


def parse_llm_tool_call(text: str) -> LLMToolCall:
    """Parse one strict JSON tool-call envelope; never execute it."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("tool call payload is required")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("tool call payload must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("tool call payload must be an object")

    allowed = {"call_id", "tool_name", "arguments"}
    unexpected = set(payload) - allowed
    missing = allowed - set(payload)
    if missing:
        raise ValueError("tool call field missing")
    if unexpected:
        raise ValueError("unexpected tool call field")

    return LLMToolCall(
        call_id=payload["call_id"],
        tool_name=payload["tool_name"],
        arguments=payload["arguments"],
    )


class EngineeringToolBridge:
    """Pass a validated LLM tool call to an injected governed dispatcher."""

    def __init__(self, dispatcher: Callable[[Any], Any]) -> None:
        if not callable(dispatcher):
            raise TypeError("dispatcher must be callable")
        self._dispatcher = dispatcher

    def dispatch(self, call: LLMToolCall) -> Any:
        """Adapt the call without granting authority or executing locally."""
        return self._dispatcher(call)
