from __future__ import annotations

import json

import pytest

import hoare_engine.engineering_tool_source as source


def test_source_reuses_existing_llm_provider_boundary(monkeypatch):
    captured = {}

    def fake_call(messages):
        captured["messages"] = messages
        return '{"tool_name":"run_tests","arguments":{"repository":"example/repo","command":["pytest","-q"],"reason":"verify"}}'

    monkeypatch.setattr(source, "_try_openai_call", fake_call)
    result = source.OpenAICompatibleEngineeringToolSource().generate_tool_call("Verify the repair.")

    assert json.loads(result)["tool_name"] == "run_tests"
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][1]["content"] == "Verify the repair."


@pytest.mark.parametrize(
    "raw,error",
    [
        ("", "llm_tool_response_required"),
        ("not-json", "llm_tool_response_invalid_json"),
        ("[]", "llm_tool_response_schema_invalid"),
        ('{"tool_name":"run_tests"}', "llm_tool_response_schema_invalid"),
        ('{"tool_name":"run_tests","arguments":[]}', "llm_tool_arguments_must_be_object"),
    ],
)
def test_source_validation_is_strict_and_non_authorizing(raw, error):
    with pytest.raises(ValueError, match=error):
        source.OpenAICompatibleEngineeringToolSource.validate_response(raw)


def test_source_does_not_authorize_or_execute():
    payload = source.OpenAICompatibleEngineeringToolSource.validate_response(
        '{"tool_name":"write_file","arguments":{"repository":"example/repo","path":"README.md","content":"x","reason":"repair"}}'
    )
    assert payload["tool_name"] == "write_file"
    assert "status" not in payload
    assert "authorized" not in payload
