"""Provider-neutral engineering tool-call source for the existing HOARE LLM boundary.

This module does not create a second model or execution engine. It reuses the
existing OpenAI-compatible configuration and asks the configured model for one
strict, structured engineering tool-call payload. Authorization and execution
remain outside this module.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable


_ENGINEERING_TOOL_SYSTEM_PROMPT = """You are the planning interface for a governed engineering agent.

Return exactly one JSON object:
{
  "tool_name": "<capability name>",
  "arguments": { "<argument>": "<value>" }
}

Rules:
1. The JSON describes a requested capability; it does not authorize execution.
2. Never include credentials, bearer tokens, approval decisions, or claims of authorization.
3. Do not emit shell syntax. Test commands must be structured as an arguments.command array.
4. Do not invent tool names outside the capabilities supplied by the caller.
5. Return JSON only.
"""


@dataclass(frozen=True)
class EngineeringToolSource:
    """Generate structured engineering tool calls with the existing HOARE LLM config."""

    base_url: str | None = None
    model: str | None = None
    api_key: str | None = None
    client_factory: Callable[..., Any] | None = None

    def generate_tool_call(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("engineering_tool_prompt_required")

        base_url = self.base_url or os.getenv(
            "HOARE_LLM_BASE_URL", "http://localhost:8000/v1"
        )
        model = self.model or os.getenv(
            "HOARE_LLM_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"
        )
        api_key = self.api_key or os.getenv("HOARE_LLM_API_KEY", "EMPTY")

        client = self._client(base_url=base_url, api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _ENGINEERING_TOOL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=512,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if not isinstance(content, str) or not content.strip():
            raise ValueError("engineering_tool_response_empty")
        self._validate_json_object(content)
        return content

    def _client(self, *, base_url: str, api_key: str) -> Any:
        if self.client_factory is not None:
            return self.client_factory(base_url=base_url, api_key=api_key)
        try:
            import openai  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "openai package not installed; run: pip install openai"
            ) from exc
        return openai.OpenAI(base_url=base_url, api_key=api_key)

    @staticmethod
    def _validate_json_object(content: str) -> None:
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ValueError("engineering_tool_response_invalid_json") from exc
        if not isinstance(payload, dict):
            raise ValueError("engineering_tool_response_must_be_object")
        if set(payload) != {"tool_name", "arguments"}:
            raise ValueError("engineering_tool_response_schema_invalid")
        if not isinstance(payload["tool_name"], str) or not payload["tool_name"].strip():
            raise ValueError("engineering_tool_name_required")
        if not isinstance(payload["arguments"], dict):
            raise ValueError("engineering_tool_arguments_must_be_object")
