from __future__ import annotations

import json

from hoare_engine.engineering_tools import EngineeringToolLLMSource


def test_mock_source_returns_structured_tool_call():
    source = EngineeringToolLLMSource(use_mock=True)
    payload = json.loads(
        source.generate_tool_call(
            "Run the repository tests.",
            capabilities={"run_tests": "Run an explicit test command."},
        )
    )
    assert set(payload) == {"tool_name", "arguments"}
    assert payload["tool_name"] in {"observe_file", "write_file", "run_tests"}
    assert isinstance(payload["arguments"], dict)


def test_source_rejects_empty_prompt():
    source = EngineeringToolLLMSource(use_mock=True)
    try:
        source.generate_tool_call(" ")
    except ValueError as exc:
        assert str(exc) == "engineering_tool_prompt_required"
    else:
        raise AssertionError("empty prompt was accepted")


def test_source_is_provider_configuration_compatible(monkeypatch):
    monkeypatch.setenv("HOARE_LLM_MODEL", "test-model")
    source = EngineeringToolLLMSource(use_mock=True)
    assert source is not None
