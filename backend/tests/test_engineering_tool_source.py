from __future__ import annotations

import json

from hoare_engine.engineering_tool_source import EngineeringToolCallSource


def test_mock_engineering_source_returns_structured_tool_call() -> None:
    source = EngineeringToolCallSource(use_mock_llm=True)
    payload = json.loads(source.generate_tool_call("Verify the repair."))
    assert payload["tool_name"] == "run_tests"
    assert payload["arguments"]["command"] == ["pytest", "-q"]


def test_engineering_source_rejects_empty_prompt() -> None:
    source = EngineeringToolCallSource(use_mock_llm=True)
    try:
        source.generate_tool_call("")
    except ValueError as exc:
        assert str(exc) == "engineering_prompt_required"
    else:
        raise AssertionError("empty prompt must be rejected")


def test_engineering_source_reports_existing_model() -> None:
    source = EngineeringToolCallSource(use_mock_llm=True)
    assert source.model_name()