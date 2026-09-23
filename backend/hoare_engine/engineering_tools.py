"""Provider-neutral engineering tool-call source for the existing HOARE LLM boundary.

Provenance: 2026-09-23 UTC

This module does not execute tools and does not grant authority. It reuses the
existing HOARE LLM provider boundary and emits the strict JSON payload consumed
by HOARE-CORE's LLMToolBridge.
"""

from __future__ import annotations

import json\nfrom typing import Dict, List

from hoare_engine.agent import _call_llm


_ENGINEERING_TOOL_SYSTEM_PROMPT = """\
You are the engineering planning mode of the HOARE agent.

Return exactly one JSON object with exactly these keys:
{
  "tool_name": "<one governed engineering tool>",
  "arguments": {
    "repository": "<repository identifier>",
    "path": "<relative path when required>",
    "branch": "<branch when required>",
    "content": "<file content when writing>",
    "command": ["pytest", "-q"],
    "reason": "<why the action is requested>"
  }
}

Allowed tool_name values:
- observe_file
- write_file
- run_tests

Rules:
1. Emit a tool request only. Never execute it.
2. Never emit credentials, tokens, secrets, shell pipelines, shell operators,
   or arbitrary shell commands.
3. run_tests may use only pytest or python -m pytest command forms.
4. write_file must identify a repository, relative path, content, and reason.
5. The downstream governed dispatcher is the authority boundary.
6. Do not include markdown fences or explanatory text.
"""


class HoareEngineeringToolSource:
    """LLMToolCallSource-compatible source backed by the existing HOARE LLM."""

    def __init__(self, *, use_mock_llm: bool = False) -> None:
        self._use_mock = use_mock_llm

    def generate_tool_call(self, prompt: str) -> str:
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("engineering_prompt_required")

        if self._use_mock:\n            return json.dumps({"tool_name": "run_tests", "arguments": {"repository": "example/repo", "command": ["pytest", "-q"], "reason": "deterministic engineering tool test"}})\n\n        messages: List[Dict[str, str]] = [
            {"role": "system", "content": _ENGINEERING_TOOL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt.strip()},
        ]
        return _call_llm(messages, use_mock=self._use_mock)


def build_engineering_prompt(
    task: str,
    *,
    repository: str,
    evidence: str = "",
) -> str:
    """Build a bounded planning prompt without creating execution authority."""
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task_required")
    if not isinstance(repository, str) or not repository.strip():
        raise ValueError("repository_required")

    prompt = (
        f"Engineering task: {task.strip()}\n"
        f"Repository: {repository.strip()}\n"
    )
    if evidence:
        prompt += f"Evidence supplied for reasoning only:\n{evidence.strip()}\n"
    return prompt
