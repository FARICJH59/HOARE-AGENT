from __future__ import annotations

from dataclasses import dataclass

import pytest

from hoare_engine.engineering_tool_source import EngineeringToolSource


@dataclass
class Message:
    content: str


@dataclass
class Choice:
    message: Message


@dataclass
class Response:
    choices: list[Choice]


class FakeCompletions:
    def __init__(self, content: str) -> None:
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return Response([Choice(Message(self.content))])


class FakeClient:
    def __init__(self, content: str) -> None:
        self.chat = type("Chat", (), {})()
        self.chat.completions = FakeCompletions(content)


def test_engineering_tool_source_uses_existing_llm_configuration() -> None:
    fake = FakeClient(
        '{"tool_name":"run_tests","arguments":{"repository":"example/repo","command":["pytest","-q"],"reason":"verify"}}'
    )

    source = EngineeringToolSource(
        base_url="http://llm.test/v1",
        model="test-model",
        api_key="test-key",
        client_factory=lambda **kwargs: fake,
    )

    result = source.generate_tool_call("Verify the repair.")

    assert result.startswith('{"tool_name"')
    assert fake.chat.completions.kwargs["model"] == "test-model"
    assert fake.chat.completions.kwargs["temperature"] == 0.0
    assert fake.chat.completions.kwargs["response_format"] == {"type": "json_object"}
    assert fake.chat.completions.kwargs["messages"][0]["role"] == "system"


@pytest.mark.parametrize(
    "content",
    ["", "not-json", "[]", '{"tool_name":"run_tests"}', '{"tool_name":"run_tests","arguments":[]}', '{"tool_name":"","arguments":{}}'],
)
def test_engineering_tool_source_rejects_invalid_model_output(content: str) -> None:
    source = EngineeringToolSource(client_factory=lambda **kwargs: FakeClient(content))

    with pytest.raises(ValueError):
        source.generate_tool_call("Verify the repair.")
