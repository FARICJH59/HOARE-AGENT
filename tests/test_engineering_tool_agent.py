from __future__ import annotations

from hoare_engine.engineering_tool_agent import EngineeringToolCallAgent


def test_engineering_tool_agent_fails_closed_on_non_tool_model_output() -> None:
    result = EngineeringToolCallAgent(use_mock_llm=True).propose(
        task_id="task-1",
        description="Inspect README.md in example/repo",
        allowed_tools=("observe_file",),
    )

    assert result.task_id == "task-1"
    assert result.success is False
    assert result.error.startswith("invalid_tool_call:")


def test_engineering_tool_agent_rejects_empty_identity() -> None:
    try:
        EngineeringToolCallAgent().propose(
            task_id="",
            description="inspect a file",
            allowed_tools=("observe_file",),
        )
    except ValueError as exc:
        assert str(exc) == "task_id_required"
    else:
        raise AssertionError("expected task_id_required")
