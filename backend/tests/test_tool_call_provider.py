import json

import pytest

from hoare_engine.tool_call_provider import OpenAICompatibleToolCallSource


class FakeCompletions:
    def __init__(self, content):
        self.content = content

    def create(self, **kwargs):
        self.kwargs = kwargs

        class Message:
            def __init__(self, content):
                self.content = content

        class Choice:
            def __init__(self, content):
                self.message = Message(content)

        class Response:
            def __init__(self, content):
                self.choices = [Choice(content)]

        return Response(self.content)


class FakeClient:
    def __init__(self, content):
        self.chat = type("Chat", (), {})()
        self.chat.completions = FakeCompletions(content)


CAPABILITIES = {
    "run_tests": type(
        "Capability",
        (),
        {"description": "Run an explicit pytest command."},
    )()
}


def test_provider_returns_structured_tool_call():
    payload = {"tool_name": "run_tests", "arguments": {
        "repository": "example/repo",
        "command": ["pytest", "-q"],
        "reason": "verify",
    }}
    client = FakeClient(json.dumps(payload))
    source = OpenAICompatibleToolCallSource(client=client)

    raw = source.generate_tool_call("verify the repair", CAPABILITIES)

    assert json.loads(raw) == payload
    assert client.chat.completions.kwargs["temperature"] == 0.0
    assert client.chat.completions.kwargs["response_format"] == {"type": "json_object"}


def test_provider_rejects_tool_not_in_capabilities():
    client = FakeClient(json.dumps({
        "tool_name": "delete_everything",
        "arguments": {"repository": "example/repo", "reason": "bad"},
    }))
    source = OpenAICompatibleToolCallSource(client=client)

    with pytest.raises(ValueError, match="llm_tool_name_not_allowed"):
        source.generate_tool_call("do something", CAPABILITIES)


def test_provider_rejects_malformed_model_output():
    client = FakeClient(json.dumps({"tool_name": "run_tests"}))
    source = OpenAICompatibleToolCallSource(client=client)

    with pytest.raises(ValueError, match="llm_tool_response_schema_invalid"):
        source.generate_tool_call("verify", CAPABILITIES)
