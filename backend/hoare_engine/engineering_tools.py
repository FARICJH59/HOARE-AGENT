"""LLM-to-engineering tool-call bridge.

This module extends the existing HOARE Agent LLM boundary without adding a
second model or execution engine. The bridge exposes provider-neutral tool
schemas to the same OpenAI-compatible endpoint, converts returned tool calls
into plain dictionaries, and delegates execution to a caller-supplied
governed handler such as HOARE-CORE's ToolDispatcher.

The bridge itself never authorizes or executes an engineering action.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol


class ToolCallHandler(Protocol):
    def __call__(self, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class EngineeringToolTurn:
    """One model turn plus any governed tool results returned to the model."""

    assistant_message: Mapping[str, Any]
    tool_results: tuple[Mapping[str, Any], ...] = ()


class EngineeringToolLoop:
    """Run a bounded tool-calling loop against the existing LLM provider."""

    def __init__(
        self,
        *,
        llm_call: Callable[[list[dict[str, Any]], list[dict[str, Any]]], Mapping[str, Any]],
        tool_handler: ToolCallHandler,
        max_rounds: int = 8,
    ) -> None:
        if max_rounds < 1:
            raise ValueError("max_rounds_must_be_positive")
        self._llm_call = llm_call
        self._tool_handler = tool_handler
        self._max_rounds = max_rounds

    def run(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
        if not isinstance(messages, list) or not isinstance(tools, list):
            raise TypeError("messages_and_tools_must_be_lists")

        transcript = [dict(message) for message in messages]

        for _ in range(self._max_rounds):
            response = self._llm_call(transcript, tools)
            message = response.get("message") if isinstance(response, Mapping) else None
            if not isinstance(message, Mapping):
                raise ValueError("llm_response_message_required")

            assistant = dict(message)
            transcript.append(assistant)
            tool_calls = assistant.get("tool_calls") or []
            if not tool_calls:
                return transcript, assistant

            for raw_call in tool_calls:
                payload = self._normalize_tool_call(raw_call)
                result = dict(self._tool_handler(payload))
                transcript.append(
                    {
                        "role": "tool",
                        "tool_call_id": payload["call_id"],
                        "content": json.dumps(result, sort_keys=True),
                    }
                )

        raise RuntimeError("engineering_tool_loop_max_rounds_exceeded")

    @staticmethod
    def _normalize_tool_call(raw_call: object) -> dict[str, Any]:
        if not isinstance(raw_call, Mapping):
            raise ValueError("invalid_tool_call")
        call_id = raw_call.get("id") or raw_call.get("call_id")
        function = raw_call.get("function")
        if not call_id or not isinstance(function, Mapping):
            raise ValueError("invalid_tool_call_identity")

        name = function.get("name")
        arguments = function.get("arguments", {})
        if not isinstance(name, str) or not name:
            raise ValueError("tool_name_required")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise ValueError("tool_arguments_must_be_json") from exc
        if not isinstance(arguments, Mapping):
            raise ValueError("tool_arguments_must_be_mapping")

        return {
            "call_id": str(call_id),
            "tool_name": name,
            "arguments": dict(arguments),
        }


def openai_compatible_tool_call(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> Mapping[str, Any]:
    """Call the existing HOARE OpenAI-compatible LLM endpoint with tools.

    Configuration is shared with the existing HoareAgent environment. No
    credentials or provider-specific execution logic is exposed to tools.
    """

    try:
        import openai  # type: ignore
    except ImportError as exc:
        raise RuntimeError("openai package not installed") from exc

    client = openai.OpenAI(
        base_url=os.getenv("HOARE_LLM_BASE_URL", "http://localhost:8000/v1"),
        api_key=os.getenv("HOARE_LLM_API_KEY", "EMPTY"),
    )
    response = client.chat.completions.create(
        model=os.getenv("HOARE_LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"),
        messages=messages,
        tools=tools,
        temperature=0.0,
        max_tokens=1024,
    )
    choice = response.choices[0]
    return {"message": choice.message.model_dump(exclude_none=True)}
