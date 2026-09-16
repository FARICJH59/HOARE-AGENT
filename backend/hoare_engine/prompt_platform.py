"""Main HOARE prompt-to-build control plane.

Provenance: 2026-09-16

Natural-language prompt -> intent -> provider-neutral plan -> existing
self-verifying agent. Generation never grants execution or deployment authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from hoare_engine.agent import HoareAgent
from schema.models import AgentTaskRequest, AgentTaskResult


class BuildStage(str, Enum):
    INTENT = "INTENT"
    UNDERSTAND = "UNDERSTAND"
    ARCHITECT = "ARCHITECT"
    PLAN = "PLAN"
    BUILD = "BUILD"
    VERIFY = "VERIFY"
    STAGED = "STAGED"


@dataclass(frozen=True)
class ProjectIntent:
    prompt: str
    project_id: str
    domain: str
    objective: str
    constraints: tuple[str, ...]


@dataclass(frozen=True)
class ProjectPlan:
    project_id: str
    domain: str
    stages: tuple[BuildStage, ...]
    capabilities: tuple[str, ...]
    artifact_schema: str


@dataclass(frozen=True)
class AutonomousBuildResult:
    intent: ProjectIntent
    plan: ProjectPlan
    agent_result: AgentTaskResult
    final_stage: BuildStage


def _infer_domain(prompt: str) -> str:
    text = prompt.lower()
    keywords = {
        "energy": ("energy", "grid", "power", "utility", "substation", "battery"),
        "retail": ("grocery", "retail", "shelf", "sku", "store"),
        "manufacturing": ("factory", "manufacturing", "production", "machine"),
        "robotics": ("robot", "robotics", "arm", "autonomous vehicle"),
        "aerospace": ("aerospace", "aircraft", "satellite", "aviation"),
        "healthcare": ("healthcare", "hospital", "clinical", "medical"),
        "logistics": ("logistics", "warehouse", "fleet", "shipping"),
        "agriculture": ("agriculture", "farm", "crop", "irrigation"),
    }
    for domain, terms in keywords.items():
        if any(term in text for term in terms):
            return domain
    return "general"


def understand_prompt(prompt: str, *, project_id: str) -> ProjectIntent:
    normalized = " ".join(prompt.strip().split())
    if not normalized:
        raise ValueError("prompt is required")
    return ProjectIntent(
        prompt=normalized,
        project_id=project_id,
        domain=_infer_domain(normalized),
        objective=normalized,
        constraints=(
            "generated artifacts require verification",
            "execution authority is separate from generation",
            "deployment requires explicit authorization",
        ),
    )


def architect(intent: ProjectIntent) -> ProjectPlan:
    capabilities = ["IntentUnderstanding", "Architecture", "CodeGeneration", "Verification"]
    if intent.domain != "general":
        capabilities.append(f"{intent.domain.title()}DomainPack")
    artifact_schema = (
        '{"type":"object","required":["project_id","domain","artifacts"],'
        '"properties":{"project_id":{"type":"string"},'
        '"domain":{"type":"string"},"artifacts":{"type":"array"}}}'
    )
    return ProjectPlan(
        project_id=intent.project_id,
        domain=intent.domain,
        stages=tuple(BuildStage),
        capabilities=tuple(capabilities),
        artifact_schema=artifact_schema,
    )


def build_from_prompt(prompt: str, *, project_id: str, use_mock_llm: bool = False, max_retries: int = 3) -> AutonomousBuildResult:
    intent = understand_prompt(prompt, project_id=project_id)
    plan = architect(intent)
    request = AgentTaskRequest(
        task_id=project_id,
        description=f"Build the first verified artifact for project '{project_id}'. Domain: {intent.domain}. Objective: {intent.objective}",
        target_schema=plan.artifact_schema,
        max_retries=max_retries,
    )
    result = HoareAgent(use_mock_llm=use_mock_llm).run_task(request)
    return AutonomousBuildResult(intent, plan, result, BuildStage.STAGED if result.success else BuildStage.VERIFY)


def result_to_dict(result: AutonomousBuildResult) -> dict[str, Any]:
    return {
        "project_id": result.intent.project_id,
        "intent": {"prompt": result.intent.prompt, "domain": result.intent.domain, "objective": result.intent.objective, "constraints": list(result.intent.constraints)},
        "plan": {"stages": [stage.value for stage in result.plan.stages], "capabilities": list(result.plan.capabilities)},
        "build": result.agent_result.model_dump(mode="json"),
        "final_stage": result.final_stage.value,
        "execution_authorized": False,
        "deployment_authorized": False,
    }
