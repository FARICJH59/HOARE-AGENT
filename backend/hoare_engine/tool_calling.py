from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from hoare_engine.agent import _call_llm


@dataclass(frozen=True)
class EngineeringToolRequest:
    """Untrusted structured LLM output; never an authorization decision."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.call_id.strip():
            raise ValueError("call_id is required")
        if not self.tool_name.strip():
            raise ValueError("tool_name is required")
        if not isinstance(self.arguments, dict):
            raise TypeError("arguments must be an object")


_SYSTEM = """You are the planning component of an engineering agent.
Return exactly one JSON object with keys call_id, tool_name, and arguments.
Arguments are structured data, never shell syntax or credentials.
Do not claim authorization or execution. Do not emit markdown."""


def build_tool_messages(task: str, capabilities: dict[str, str]) -> list[dict[str, str]]:
    if not task.strip():
        raise ValueError("task is required")
    if not capabilities:
        raise ValueError("capabilities are required")
    return [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": f"Task: {task.strip()}\nAvailable tools: {json.dumps(capabilities, sort_keys=True)}\nReturn one structured tool request."},
    ]


def parse_tool_request(text: str) -> EngineeringToolRequest:
    if not text.strip():
        raise ValueError("empty LLM response")
    if text.strip().startswith("```"):
        raise ValueError("markdown_fence_not_allowed")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_tool_request_json") from exc
    if not isinstance(payload, dict) or set(payload) != {"call_id", "tool_name", "arguments"}:
        raise ValueError("tool_request_schema_mismatch")
    return EngineeringToolRequest(payload["call_id"], payload["tool_name"], payload["arguments"])


def request_tool(task: str, capabilities: dict[str, str], *, use_mock_llm: bool = False) -> EngineeringToolRequest:
    """Use the existing LLM transport; no adapter, AEGIS, or execution occurs here."""
    raw = _call_llm(build_tool_messages(task, capabilities), use_mock=use_mock_llm)
    return parse_tool_request(raw)
