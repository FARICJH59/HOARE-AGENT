"""LLM-facing engineering tool-call generation.

This module reuses the existing HOARE-AGENT OpenAI-compatible provider boundary.
It generates structured tool-call data only; it never authorizes or executes it.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping

from hoare_engine.agent import _try_openai_call

_ENGINEERING_TOOL_SYSTEM_PROMPT = """You are the engineering tool-planning mode of the HOARE Agent.

Return exactly one JSON object:
{"tool_name":"<capability>","arguments":{...}}

The output is DATA ONLY. It does not authorize execution.

Rules:
1. Never include credentials, tokens, leases, authorization decisions, or shell syntax.
2. Use only a tool capability explicitly named by the caller.
3. Arguments must be a JSON object.
4. For file changes, include repository, path, content, and reason.
5. For tests, include repository, command as an array of argv strings, and reason.
6. Do not include markdown or explanatory text.
"""


@dataclass(frozen=True)
class EngineeringToolCallGenerator:
    """Generate one structured tool call through the existing LLM provider."""

    model_prompt: str = _ENGINEERING_TOOL_SYSTEM_PROMPT

    def generate(
        self,
        task: str,
        *,
        allowed_tools: tuple[str, ...],
    ) -> Mapping[str, Any]:
        if not isinstance(task, str) or not task.strip():
            raise ValueError("engineering_task_required")
        if not allowed_tools:
            raise ValueError("allowed_tools_required")

        prompt = (
            f"{self.model_prompt}\n\n"
            f"Allowed tools: {json.dumps(list(allowed_tools))}\n"
            f"Engineering task: {task.strip()}"
        )
        raw = _try_openai_call([
            {"role": "system", "content": self.model_prompt},
            {"role": "user", "content": prompt},
        ])
        return self._parse(raw, allowed_tools=allowed_tools)

    @staticmethod
    def _parse(raw: str, *, allowed_tools: tuple[str, ...]) -> Mapping[str, Any]:
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("engineering_tool_response_required")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("engineering_tool_response_invalid_json") from exc
        if not isinstance(payload, dict) or set(payload) != {"tool_name", "arguments"}:
            raise ValueError("engineering_tool_response_schema_invalid")

        tool_name = payload["tool_name"]
        arguments = payload["arguments"]
        if not isinstance(tool_name, str) or tool_name not in allowed_tools:
            raise ValueError("engineering_tool_not_allowed")
        if not isinstance(arguments, dict):
            raise ValueError("engineering_tool_arguments_must_be_object")
        return {"tool_name": tool_name, "arguments": dict(arguments)}
