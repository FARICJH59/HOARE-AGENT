"""HOARE Case Study #2: govern an already-existing AI agent.

Provenance: 2026-09-16

This test deliberately does not construct a product from an IR. The external
agent/model is treated as an already-existing system and HOARE is tested only
at the governance/admission boundary around a proposed consequential action.
"""

from dataclasses import dataclass
from enum import Enum


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class ExistingAgentProposal:
    tenant_id: str
    agent_id: str
    model_id: str
    project_id: str
    action: str
    resource: str
    evidence_verified: bool
    confidence: float
    execution_mode: str
    human_authority: bool = False


class ExistingAgentGovernanceBoundary:
    """Minimal contract representing HOARE around an external agent."""

    def admit(self, proposal: ExistingAgentProposal) -> Decision:
        if not proposal.tenant_id or not proposal.agent_id:
            return Decision.DENY
        if not proposal.project_id or not proposal.resource:
            return Decision.DENY
        if not proposal.evidence_verified:
            return Decision.DENY
        if proposal.confidence < 0.90:
            return Decision.ESCALATE
        if proposal.execution_mode in {"CONTROLLED", "LIVE"} and not proposal.human_authority:
            return Decision.ESCALATE
        return Decision.ALLOW


def _existing_shelf_scouter_proposal(**overrides):
    values = dict(
        tenant_id="retail-tenant-001",
        agent_id="shelf-scouter-existing-agent",
        model_id="gemma-4-e4b-it",
        project_id="shelf-scouter",
        action="confirm-pick",
        resource="retailer:catalog:sku-001",
        evidence_verified=True,
        confidence=0.97,
        execution_mode="SHADOW",
        human_authority=False,
    )
    values.update(overrides)
    return ExistingAgentProposal(**values)


def test_hoare_governs_existing_agent_without_rebuilding_it():
    existing_agent = _existing_shelf_scouter_proposal()
    governance = ExistingAgentGovernanceBoundary()

    assert existing_agent.agent_id == "shelf-scouter-existing-agent"
    assert existing_agent.model_id == "gemma-4-e4b-it"
    assert governance.admit(existing_agent) is Decision.ALLOW


def test_existing_agent_is_denied_when_evidence_is_untrusted():
    governance = ExistingAgentGovernanceBoundary()

    assert (
        governance.admit(_existing_shelf_scouter_proposal(evidence_verified=False))
        is Decision.DENY
    )


def test_existing_agent_escalates_low_confidence():
    governance = ExistingAgentGovernanceBoundary()

    assert (
        governance.admit(_existing_shelf_scouter_proposal(confidence=0.71))
        is Decision.ESCALATE
    )


def test_existing_agent_requires_human_authority_for_controlled_execution():
    governance = ExistingAgentGovernanceBoundary()

    assert (
        governance.admit(
            _existing_shelf_scouter_proposal(execution_mode="CONTROLLED")
        )
        is Decision.ESCALATE
    )


def test_existing_agent_can_execute_controlled_action_after_explicit_authority():
    governance = ExistingAgentGovernanceBoundary()

    assert (
        governance.admit(
            _existing_shelf_scouter_proposal(
                execution_mode="CONTROLLED",
                human_authority=True,
            )
        )
        is Decision.ALLOW
    )


def test_existing_model_identity_is_preserved():
    proposal = _existing_shelf_scouter_proposal()

    # HOARE governs the existing model; it does not replace the model identity.
    assert proposal.model_id == "gemma-4-e4b-it"
