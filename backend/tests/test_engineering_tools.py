from __future__ import annotations

import json

import pytest

from hoare_engine.engineering_tools import EngineeringToolLoop


def test_tool_loop_normalizes_structured_call_and_returns_governed_result():
    seen = []

    def llm(messages, tools):
        seen.append((messages, tools))
        if len(seen) == 1:
            return {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "function": {
                                "name": "write_file",
                                "arguments": json.dumps(
                                    {
                                        "repository": "example/repo",
                                        "path": "README.md",
                                        "content": "new",
                                        "reason": "repair",
                                    }
                                ),
                            },
                        }
                    ],
                }
            }
        return {"message": {"role": "assistant", "content": "completed"}}

    def handler(payload):
        assert payload["call_id"] == "call-1"
        assert payload["tool_name"] == "write_file"
        assert payload["arguments"]["path"] == "README.md"
        return {
            "call_id": payload["call_id"],
            "status": "completed",
            "detail": "verified",
        }

    transcript, final = EngineeringToolLoop(
        llm_call=llm,
        tool_handler=handler,
    ).run(
        [{"role": "user", "content": "repair the file"}],
        [{"type": "function", "function": {"name": "write_file"}}],
    )

    assert final["content"] == "completed"
    assert transcript[-2]["role"] == "tool"
    assert json.loads(transcript[-2]["content"])["status"] == "completed"
    assert len(seen) == 2


def test_tool_loop_rejects_malformed_tool_call_before_handler():
    def llm(_messages, _tools):
        return {
            "message": {
                "role": "assistant",
                "tool_calls": [{"function": {"name": "write_file", "arguments": "{}"}}],
            }
        }

    called = False

    def handler(_payload):
        nonlocal called
        called = True
        return {}

    with pytest.raises(ValueError, match="invalid_tool_call_identity"):
        EngineeringToolLoop(llm_call=llm, tool_handler=handler).run([], [])

    assert called is False


def test_tool_loop_bounds_repeated_tool_requests():
    def llm(_messages, _tools):
        return {
            "message": {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call-loop",
                        "function": {"name": "observe_file", "arguments": "{}"},
                    }
                ],
            }
        }

    with pytest.raises(RuntimeError, match="max_rounds"):
        EngineeringToolLoop(
            llm_call=llm,
            tool_handler=lambda payload: {"call_id": payload["call_id"]},
            max_rounds=2,
        ).run([], [])


def test_tool_loop_does_not_execute_tools_itself():
    def llm(_messages, _tools):
        return {
            "message": {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": "call-data",
                        "function": {"name": "run_tests", "arguments": "{}"},
                    }
                ],
            }
        }

    calls = []

    def handler(payload):
        calls.append(payload)
        return {"status": "rejected", "detail": "aegis"}

    transcript, _ = EngineeringToolLoop(
        llm_call=llm,
        tool_handler=handler,
        max_rounds=1,
    ).run([], [])

    assert calls[0]["tool_name"] == "run_tests"
    assert json.loads(transcript[-1]["content"])["detail"] == "aegis"
