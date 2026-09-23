from __future__ import annotations

import json

import pytest

import hoare_engine.engineering_tool_agent as module
from hoare_engine.engineering_tool_agent import EngineeringToolCallGenerator


def test_generator_reuses_existing_provider_boundary(monkeypatch) -> None:
    captured = {}

    def fake_call(messages):
        captured["messages"] = messages
        return json.dumps({
            "tool_name": "run_tests",
            "arguments": {
                "repository": "example/repo",
                "command": ["pytest", "-q"],
                "reason": "verify repair",
            },
        })

    monkeypatch.setattr(module, "_try_openai_call", fake_call)

    result = EngineeringToolCallGenerator().generate(
        "verify the repair",
        allowed_tools=("run_tests",),
    )

    assert result["tool_name"] == "run_tests"
    assert result["arguments"]["command"] == ["pytest", "-q"]
    assert captured["messages"][0]["role"] == "system"


def test_generator_rejects_tool_outside_allowed_capabilities(monkeypatch) -> None:
    monkeypatch.setattr(
        module,
        "_try_openai_call",
        lambda _messages: '{"tool_name":"write_file","arguments":{}}',
    )

    with pytest.raises(ValueError, match="engineering_tool_not_allowed"):
        EngineeringToolCallGenerator().generate(
            "write a file",
            allowed_tools=("run_tests",),
        )


@pytest.mark.parametrize(
    "raw,error",
    [
        ("", "engineering_tool_response_required"),
        ("not-json", "engineering_tool_response_invalid_json"),
        ("[]", "engineering_tool_response_schema_invalid"),
        ('{"tool_name":"run_tests"}', "engineering_tool_response_schema_invalid"),
        ('{"tool_name":"run_tests","arguments":[]}', "engineering_tool_arguments_must_be_object"),
    ],
)
def test_generator_rejects_malformed_provider_output(monkeypatch, raw, error) -> None:
    monkeypatch.setattr(module, "_try_openai_call", lambda _messages: raw)

    with pytest.raises(ValueError, match=error):
        EngineeringToolCallGenerator().generate(
            "verify",
            allowed_tools=("run_tests",),
        )
