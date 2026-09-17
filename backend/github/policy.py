"""AEGIS admission policy for GitHub operations.

Provenance: 2026-09-13

This module is deliberately independent from the GitHub transport. A transport
can fetch or mutate GitHub only after this policy layer returns ALLOW.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .permissions import GitHubAction, GitHubRepositoryScope


class AegisDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class GitHubActionRequest:
    tenant_id: str
    repository: str
    action: GitHubAction
    branch: str | None = None
    production: bool = False
    reason: str = ""
    request_id: str = ""


@dataclass(frozen=True)
class AegisGitHubDecision:
    decision: AegisDecision
    reasons: tuple[str, ...]
    request: GitHubActionRequest
    authority: str = "aegis-github-gate"
    can_execute: bool = False

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reasons": list(self.reasons),
            "request": {
                "tenant_id": self.request.tenant_id,
                "repository": self.request.repository,
                "action": self.request.action.value,
                "branch": self.request.branch,
                "production": self.request.production,
                "reason": self.request.reason,
                "request_id": self.request.request_id,
            },
            "authority": self.authority,
            "can_execute": self.can_execute,
        }


class AegisGitHubGate:
    """Evaluate customer-scoped GitHub operations before transport."""

    def evaluate(
        self,
        request: GitHubActionRequest,
        scope: GitHubRepositoryScope | None,
    ) -> AegisGitHubDecision:
        if scope is None:
            return self._deny(request, "no repository scope is bound to this tenant")

        if request.tenant_id != scope.tenant_id:
            return self._deny(request, "tenant identity does not match repository scope")

        if not scope.owns_repository(request.repository):
            return self._deny(request, "repository is outside the granted scope")

        if request.branch and not scope.branch_allowed(request.branch):
            return self._deny(request, "branch is outside the granted scope")

        if request.action in {GitHubAction.MERGE, GitHubAction.DEPLOY}:
            return self._escalate(
                request,
                "consequential production operation requires explicit human authorization",
            )

        if request.action in {GitHubAction.READ_SECRETS, GitHubAction.WRITE_SECRETS}:
            return self._deny(request, "secret access is outside the GitHub agent boundary")

        if request.production or (
            request.branch is not None and scope.is_production_branch(request.branch)
        ):
            return self._escalate(
                request,
                "production repository state requires explicit human authorization",
            )

        if not scope.permissions.allows(request.action):
            return self._deny(request, "customer-granted GitHub permissions do not allow this action")

        return AegisGitHubDecision(
            decision=AegisDecision.ALLOW,
            reasons=("repository identity, scope, branch, and permission checks passed",),
            request=request,
            can_execute=False,
        )

    @staticmethod
    def _deny(request: GitHubActionRequest, reason: str) -> AegisGitHubDecision:
        return AegisGitHubDecision(AegisDecision.DENY, (reason,), request)

    @staticmethod
    def _escalate(request: GitHubActionRequest, reason: str) -> AegisGitHubDecision:
        return AegisGitHubDecision(AegisDecision.ESCALATE, (reason,), request)


__all__ = [
    "AegisDecision",
    "AegisGitHubDecision",
    "AegisGitHubGate",
    "GitHubActionRequest",
]
