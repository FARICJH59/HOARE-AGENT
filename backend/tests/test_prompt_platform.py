"""Tests for the main HOARE prompt-to-build platform.

Provenance: 2026-09-16
"""
from hoare_engine.prompt_platform import BuildStage, architect, build_from_prompt, understand_prompt


def test_prompt_becomes_provider_neutral_project_intent():
    intent = understand_prompt(
        "Build a predictive maintenance system for a power grid",
        project_id="grid-001",
    )
    assert intent.project_id == "grid-001"
    assert intent.domain == "energy"
    assert "predictive maintenance" in intent.objective.lower()
    assert "deployment requires explicit authorization" in intent.constraints


def test_architecture_contains_bounded_build_lifecycle():
    intent = understand_prompt("Build a warehouse robot", project_id="robot-001")
    plan = architect(intent)
    assert plan.stages == tuple(BuildStage)
    assert "IntentUnderstanding" in plan.capabilities
    assert "CodeGeneration" in plan.capabilities
    assert "Verification" in plan.capabilities
    assert "robotics" in plan.domain


def test_mock_prompt_build_reaches_staged_without_authority():
    result = build_from_prompt(
        "Build a telemetry transformation service",
        project_id="project-001",
        use_mock_llm=True,
    )
    assert result.agent_result.success is True
    assert result.final_stage is BuildStage.STAGED
    assert result.agent_result.generated_code


def test_empty_prompt_fails_before_agent_execution():
    try:
        build_from_prompt("   ", project_id="project-empty", use_mock_llm=True)
    except ValueError as exc:
        assert str(exc) == "prompt is required"
    else:
        raise AssertionError("empty prompt must fail closed")
