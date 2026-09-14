"""HOARE GitHub Broker.

Provenance: 2026-09-13

The broker is the only supported path from a HOARE agent to GitHub. Every
operation is evaluated by AEGIS before the transport is invoked.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass

from .audit import GitHubAuditLog
from .permissions import GitHubAction, GitHubRepositoryScope
from .policy import AegisDecision, AegisGitHubDecision, AegisGitHubGate, GitHubActionRequest
from .repository import GitHubRepositoryClient


class GitHubIntegrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubInstallation:
    tenant_id: str
    installation_id: str
    repositories: tuple[str, ...]
    permissions: object


class GitHubBroker:
    """Governed broker between HOARE and customer GitHub repositories."""

    def __init__(self, *, gate: AegisGitHubGate | None = None, audit: GitHubAuditLog | None = None) -> None:
        self._gate = gate or AegisGitHubGate()
        self._audit = audit or GitHubAuditLog()
        self._scopes: dict[tuple[str, str], GitHubRepositoryScope] = {}
        self._clients: dict[tuple[str, str], GitHubRepositoryClient] = {}

    @property
    def audit(self) -> GitHubAuditLog:
        return self._audit

    def install(
        self,
        *,
        tenant_id: str,
        installation_id: str,
        repositories: list[str],
        permissions,
        token: str,
    ) -> dict:
        if not tenant_id.strip() or not installation_id.strip():
            raise GitHubIntegrationError("tenant_id and installation_id are required")
        if not repositories:
            raise GitHubIntegrationError("at least one repository must be granted")
        client = GitHubRepositoryClient(token)
        for repository in repositories:
            client.repository(repository)
            scope = GitHubRepositoryScope(
                tenant_id=tenant_id,
                installation_id=installation_id,
                repository=repository,
                permissions=permissions,
            )
            self._scopes[(tenant_id, repository)] = scope
            self._clients[(tenant_id, repository)] = client
        return {
            "tenant_id": tenant_id,
            "installation_id": installation_id,
            "repositories": repositories,
            "permissions": permissions.to_dict(),
            "credential_storage": "process-memory-only",
        }

    def scope(self, tenant_id: str, repository: str) -> GitHubRepositoryScope | None:
        return self._scopes.get((tenant_id, repository))

    def _client(self, tenant_id: str, repository: str) -> GitHubRepositoryClient:
        try:
            return self._clients[(tenant_id, repository)]
        except KeyError as exc:
            raise GitHubIntegrationError("GitHub repository is not installed for this tenant") from exc

    def evaluate(
        self,
        *,
        actor: str,
        request: GitHubActionRequest,
    ) -> AegisGitHubDecision:
        decision = self._gate.evaluate(request, self.scope(request.tenant_id, request.repository))
        self._audit.log(
            tenant_id=request.tenant_id,
            actor=actor,
            repository=request.repository,
            action=request.action.value,
            decision=decision.decision.value,
            request_id=request.request_id,
            branch=request.branch,
            details={"reasons": list(decision.reasons)},
        )
        return decision

    def repository(self, *, actor: str, tenant_id: str, repository: str) -> dict:
        request = self._request(tenant_id, repository, GitHubAction.READ_REPOSITORY)
        decision = self.evaluate(actor=actor, request=request)
        self._require_allow(decision)
        return self._client(tenant_id, repository).repository(repository)

    def contents(self, *, actor: str, tenant_id: str, repository: str, path: str = "", ref: str | None = None):
        action = GitHubAction.ANALYZE if path else GitHubAction.READ_CONTENTS
        request = self._request(tenant_id, repository, action, branch=ref)
        decision = self.evaluate(actor=actor, request=request)
        self._require_allow(decision)
        return self._client(tenant_id, repository).contents(repository, path, ref)

    def create_branch(
        self,
        *,
        actor: str,
        tenant_id: str,
        repository: str,
        branch: str,
        base_sha: str,
    ) -> dict:
        request = self._request(tenant_id, repository, GitHubAction.CREATE_BRANCH, branch=branch)
        decision = self.evaluate(actor=actor, request=request)
        self._require_allow(decision)
        return self._client(tenant_id, repository).create_branch(repository, branch, base_sha)

    def update_file(
        self,
        *,
        actor: str,
        tenant_id: str,
        repository: str,
        path: str,
        branch: str,
        content: str,
        message: str,
        sha: str | None = None,
    ) -> dict:
        request = self._request(tenant_id, repository, GitHubAction.WRITE_CONTENTS, branch=branch)
        decision = self.evaluate(actor=actor, request=request)
        self._require_allow(decision)
        return self._client(tenant_id, repository).update_file(
            repository,
            path,
            content=content,
            message=message,
            branch=branch,
            sha=sha,
        )

    def create_pull_request(
        self,
        *,
        actor: str,
        tenant_id: str,
        repository: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
    ) -> dict:
        request = self._request(tenant_id, repository, GitHubAction.CREATE_PULL_REQUEST, branch=head)
        decision = self.evaluate(actor=actor, request=request)
        self._require_allow(decision)
        return self._client(tenant_id, repository).create_pull_request(
            repository, title=title, head=head, base=base, body=body
        )

    @staticmethod
    def _request(
        tenant_id: str,
        repository: str,
        action: GitHubAction,
        branch: str | None = None,
    ) -> GitHubActionRequest:
        return GitHubActionRequest(
            tenant_id=tenant_id,
            repository=repository,
            action=action,
            branch=branch,
            request_id=secrets.token_urlsafe(18),
        )

    @staticmethod
    def _require_allow(decision: AegisGitHubDecision) -> None:
        if decision.decision is AegisDecision.ALLOW:
            return
        raise PermissionError(
            f"GitHub action {decision.request.action.value} {decision.decision.value}: "
            + "; ".join(decision.reasons)
        )


__all__ = ["GitHubBroker", "GitHubInstallation", "GitHubIntegrationError"]
