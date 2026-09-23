from __future__ import annotations

import json

from hoare_engine.engineering_tools import HoareEngineeringToolSource, build_engineering_prompt


def test_engineering_source_uses_existing_llm_boundary() -> None:
    source = HoareEngineeringToolSource(use_mock_llm=True)
    payload = json.loads(source.generate_tool_call("Run the repository tests."))
    assert set(payload) == {"tool_name", "arguments"}
    assert payload["tool_name"] in {"observe_file", "write_file", "run_tests"}


def test_engineering_prompt_can_carry_external_evidence_without_authority() -> None:
    prompt = build_engineering_prompt(
        "Inspect the failing test and repair it.",
        repository="example/repo",
        evidence="Observed CI failure: test_metering_summarizes_durable_usage",
    )
    assert "Observed CI failure" in prompt
    assert "example/repo" in prompt


def test_empty_task_is_rejected() -> None:
    try:
        build_engineering_prompt("", repository="example/repo")
    except ValueError as exc:
        assert str(exc) == "task_required"
    else:
        raise AssertionError("expected ValueError")
