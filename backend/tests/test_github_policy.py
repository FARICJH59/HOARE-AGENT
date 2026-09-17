"""AEGIS GitHub gate tests."""

from github.permissions import GitHubAction, GitHubPermissionSet, GitHubRepositoryScope
from github.policy import AegisDecision, AegisGitHubGate, GitHubActionRequest


def _scope(**kwargs):
    permissions = GitHubPermissionSet(
        contents_read=True,
        metadata_read=True,
        pull_requests_read=True,
        branches_write=True,
        contents_write=True,
        pull_requests_write=True,
    )
    return GitHubRepositoryScope(
        tenant_id="tenant-a",
        installation_id="installation-1",
        repository="customer/app",
        permissions=permissions,
        **kwargs,
    )


def test_read_is_allowed_inside_scope() -> None:
    request = GitHubActionRequest(
        tenant_id="tenant-a",
        repository="customer/app",
        action=GitHubAction.READ_CONTENTS,
        request_id="r1",
    )
    decision = AegisGitHubGate().evaluate(request, _scope())
    assert decision.decision is AegisDecision.ALLOW
    assert decision.can_execute is False


def test_wrong_repository_is_denied() -> None:
    request = GitHubActionRequest(
        tenant_id="tenant-a",
        repository="customer/other",
        action=GitHubAction.READ_CONTENTS,
        request_id="r2",
    )
    decision = AegisGitHubGate().evaluate(request, _scope())
    assert decision.decision is AegisDecision.DENY


def test_branch_write_is_allowed_but_merge_escalates() -> None:
    gate = AegisGitHubGate()
    write = GitHubActionRequest(
        tenant_id="tenant-a",
        repository="customer/app",
        action=GitHubAction.CREATE_BRANCH,
        branch="hoare/fix-auth",
        request_id="r3",
    )
    merge = GitHubActionRequest(
        tenant_id="tenant-a",
        repository="customer/app",
        action=GitHubAction.MERGE,
        branch="main",
        request_id="r4",
    )
    assert gate.evaluate(write, _scope()).decision is AegisDecision.ALLOW
    assert gate.evaluate(merge, _scope()).decision is AegisDecision.ESCALATE


def test_production_branch_is_escalated() -> None:
    request = GitHubActionRequest(
        tenant_id="tenant-a",
        repository="customer/app",
        action=GitHubAction.CREATE_PULL_REQUEST,
        branch="main",
        request_id="r5",
    )
    decision = AegisGitHubGate().evaluate(request, _scope())
    assert decision.decision is AegisDecision.ESCALATE


def test_secrets_are_denied_even_if_customer_scope_is_changed() -> None:
    request = GitHubActionRequest(
        tenant_id="tenant-a",
        repository="customer/app",
        action=GitHubAction.READ_SECRETS,
        request_id="r6",
    )
    scope = _scope()
    decision = AegisGitHubGate().evaluate(request, scope)
    assert decision.decision is AegisDecision.DENY
