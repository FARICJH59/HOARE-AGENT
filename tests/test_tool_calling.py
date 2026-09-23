from __future__ import annotations

import pytest

from hoare_engine.tool_calling import EngineeringToolRequest, build_tool_messages, parse_tool_request


def test_parse_tool_request_accepts_structured_data() -> None:
    request = parse_tool_request('{"call_id":"c1","tool_name":"write_file","arguments":{"repository":"example/repo","reason":"repair"}}')
    assert isinstance(request, EngineeringToolRequest)
    assert request.call_id == "c1"
    assert request.tool_name == "write_file"
    assert request.arguments["repository"] == "example/repo"


def test_parse_tool_request_rejects_extra_fields() -> None:
    with pytest.raises(ValueError, match="schema_mismatch"):
        parse_tool_request('{"call_id":"c1","tool_name":"write_file","arguments":{},"authorized":true}')


def test_parse_tool_request_rejects_markdown() -> None:
    with pytest.raises(ValueError, match="markdown_fence"):
        parse_tool_request("```json{}")


def test_build_tool_messages_describes_capabilities_without_authority() -> None:
    messages = build_tool_messages("repair the test", {"write_file":"modify a file"})
    assert "write_file" in messages[1]["content"]
    assert "authorization" not in messages[1]["content"].lower()


def test_empty_inputs_rejected() -> None:
    with pytest.raises(ValueError):
        build_tool_messages("", {"write_file":"modify a file"})
    with pytest.raises(ValueError):
        build_tool_messages("repair", {})