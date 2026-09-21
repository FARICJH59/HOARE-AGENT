from __future__ import annotations

import pytest

from hoare_engine.engineering_tool_bridge import (
    EngineeringToolBridge,
    LLMToolCall,
    parse_llm_tool_call,
)


def test_parse_llm_tool_call_is_structured_data_only() -> None:
    call = parse_llm_tool_call(
        '{"call_id":"c1","tool_name":"write_file",'
        '"arguments":{"repository":"example/repo","reason":"repair"}}'
    )
    assert call.call_id == "c1"
    assert call.tool_name == "write_file"
    assert call.arguments["repository"] == "example/repo"


def test_parser_rejects_extra_fields() -> None:
    with pytest.raises(ValueError, match="unexpected"):
        parse_llm_tool_call(
            '{"call_id":"c1","tool_name":"write_file","arguments":{},'
            '"authorized":true}'
        )


def test_bridge_requires_explicit_dispatcher() -> None:
    seen = []

    def dispatcher(call):
        seen.append(call)
        return {"status": "accepted", "call_id": call.call_id}

    bridge = EngineeringToolBridge(dispatcher)
    call = LLMToolCall(
        "c1", "observe_file",
        {"repository": "example/repo", "reason": "inspect"},
    )
    result = bridge.dispatch(call)

    assert result == {"status": "accepted", "call_id": "c1"}
    assert seen == [call]


def test_llm_tool_call_rejects_missing_identity() -> None:
    with pytest.raises(ValueError):
        LLMToolCall("", "observe_file", {})
    with pytest.raises(ValueError):
        LLMToolCall("c1", "", {})
