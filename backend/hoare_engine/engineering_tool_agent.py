"""LLM-facing engineering tool-call proposal mode.

Provenance: 2026-09-21

This module reuses the existing HOARE Agent LLM provider boundary. It only
produces structured, untrusted tool-call data. It never authorizes or executes
the requested action; HOARE-CORE remains responsible for admission, execution,
observation, verification, and receipts.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, field_validator

from hoare_engine.agent import _call_llm

logger = logging.getLogger(__name__)


class EngineeringToolCall(BaseModel):
    """Untrusted structured action proposal emitted by the existing LLM."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)

    @field_validator("call_id", "tool_name")
    @classmethod
    def non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("tool_call_identity_required")
        return value


class EngineeringToolCallResult(BaseModel):
    """LLM proposal result; this is not an execution receipt."""

    task_id: str
    tool_call: EngineeringToolCall | None = None
    success: bool = False
    error: str = ""


_SYSTEM_PROMPT = """\
You are the planning layer of a governed engineering system.

Return exactly one JSON object:
{
  "call_id": "<unique call identifier>",
  "tool_name": "<one allowed tool name>",
  "arguments": {
    "repository": "<repository identifier>",
    "path": "<optional path>",
    "branch": "<optional branch>",
    "content": "<optional file content>",
    "command": ["<optional command token>", "..."],
    "reason": "<why this action is needed>"
  }
}

Rules:
1. Produce a proposal only. Never claim that an action was executed.
2. Arguments are structured data, not shell syntax or credentials.
3. Use only one of the explicitly supplied allowed tool names.
4. Do not invent authorization, approval, leases, policy decisions, receipts,
   or execution results.
5. Do not include markdown fences or explanatory text outside the JSON object.
"""


class EngineeringToolCallAgent:
    """Generate a structured engineering tool proposal using the existing LLM."""

    def __init__(self, *, use_mock_llm: bool = False) -> None:
        self._use_mock = use_mock_llm

    def propose(
        self,
        *,
        task_id: str,
        description: str,
        allowed_tools: tuple[str, ...],
    ) -> EngineeringToolCallResult:
        if not task_id.strip():
            raise ValueError("task_id_required")
        if not description.strip():
            raise ValueError("description_required")
        if not allowed_tools:
            raise ValueError("allowed_tools_required")

        prompt = (
            f"Task: {description.strip()}\n\n"
            f"Allowed tools: {json.dumps(list(allowed_tools), sort_keys=True)}"
        )
        raw = _call_llm(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            use_mock=self._use_mock,
        )
        try:
            payload = json.loads(raw)
            call = EngineeringToolCall.model_validate(payload)
        except Exception as exc:
            logger.error("Invalid engineering tool-call response: %s", exc)
            return EngineeringToolCallResult(
                task_id=task_id,
                success=False,
                error=f"invalid_tool_call:{type(exc).__name__}",
            )

        if call.tool_name not in allowed_tools:
            return EngineeringToolCallResult(
                task_id=task_id,
                tool_call=call,
                success=False,
                error="tool_not_allowed_by_requested_capabilities",
            )

        return EngineeringToolCallResult(
            task_id=task_id,
            tool_call=call,
            success=True,
        )
