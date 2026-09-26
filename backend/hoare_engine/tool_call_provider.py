"""OpenAI-compatible structured tool-call source for the governed Engineering Agent seam.

Provenance: 2026-09-25

This module reuses the existing HOARE LLM configuration. It only produces
structured tool-call data; it never authorizes, executes, or dispatches tools.
"""

from __future__ import annotations

import json
import os
from typing import Any, Mapping


_TOOL_SYSTEM_PROMPT = """You are the planning layer of an engineering agent.

Return exactly one JSON object with exactly these keys:
{
  "tool_name": "<one allowed tool name>",
  "arguments": {
    "repository": "<repository identifier>",
    "path": "<relative path when required>",
    "branch": "<branch when required>",
    "content": "<file content when writing>",
    "command": ["pytest", "-q"],
    "reason": "<short reason>"
  }
}

Rules:
1. Choose only a tool explicitly listed by the caller.
2. Arguments are data, not authorization.
3. Never return credentials, shell syntax, or an authorization decision.
4. Never claim an action was executed.
5. Use an explicit argument object; do not return markdown.
"""


class OpenAICompatibleToolCallSource:
    """Provider adapter that turns the existing HOARE LLM into tool-call data."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        client: Any | None = None,
    ) -> None:
        self.base_url = base_url or os.getenv(
            "HOARE_LLM_BASE_URL", "http://localhost:8000/v1"
        )
        self.model = model or os.getenv(
            "HOARE_LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"
        )
        self.api_key = api_key or os.getenv("HOARE_LLM_API_KEY", "EMPTY")
        self._client = client

    def generate_tool_call(
        self,
        prompt: str,
        capabilities: Mapping[str, object],
    ) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt_required")
        if not capabilities:
            raise ValueError("tool_capabilities_required")

        capability_text = json.dumps(
            {
                name: getattr(capability, "description", "")
                for name, capability in capabilities.items()
            },
            sort_keys=True,
        )
        messages = [
            {"role": "system", "content": _TOOL_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Allowed tools:\n{capability_text}\n\n"
                    f"Engineering request:\n{prompt}"
                ),
            },
        ]

        client = self._client or self._build_client()
        response = client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.0,
            max_tokens=512,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or ""
        self._validate_response(text, capabilities)
        return text

    @staticmethod
    def _validate_response(
        raw: str,
        capabilities: Mapping[str, object],
    ) -> None:
        if not raw.strip():
            raise ValueError("llm_tool_response_required")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("llm_tool_response_invalid_json") from exc
        if not isinstance(payload, dict) or set(payload) != {"tool_name", "arguments"}:
            raise ValueError("llm_tool_response_schema_invalid")
        tool_name = payload["tool_name"]
        arguments = payload["arguments"]
        if not isinstance(tool_name, str) or tool_name not in capabilities:
            raise ValueError("llm_tool_name_not_allowed")
        if not isinstance(arguments, dict):
            raise ValueError("llm_tool_arguments_must_be_object")

    def _build_client(self) -> Any:
        from openai import OpenAI

        return OpenAI(base_url=self.base_url, api_key=self.api_key)
