"""GitHub permission boundary tests."""

import pytest

from github.permissions import GitHubAction, GitHubPermissionSet, GitHubRepositoryScope


def test_read_only_scope_cannot_write() -> None:
    permissions = GitHubPermissionSet(contents_read=True, metadata_read=True)
    assert permissions.allows(GitHubAction.READ_CONTENTS)
    assert not permissions.allows(GitHubAction.CREATE_BRANCH)
    assert not permissions.allows(GitHubAction.CREATE_PULL_REQUEST)


def test_customer_can_grant_branch_and_pr_write_without_merge() -> None:
    permissions = GitHubPermissionSet(
        contents_read=True,
        metadata_read=True,
        pull_requests_read=True,
        branches_write=True,
        contents_write=True,
        pull_requests_write=True,
    )
    assert permissions.allows(GitHubAction.CREATE_BRANCH)
    assert permissions.allows(GitHubAction.WRITE_CONTENTS)
    assert permissions.allows(GitHubAction.CREATE_PULL_REQUEST)
    assert not permissions.allows(GitHubAction.MERGE)
    assert not permissions.allows(GitHubAction.READ_SECRETS)


def test_repository_scope_is_tenant_bound() -> None:
    scope = GitHubRepositoryScope(
        tenant_id="tenant-a",
        installation_id="installation-1",
        repository="customer/app",
        permissions=GitHubPermissionSet(metadata_read=True),
    )
    assert scope.owns_repository("customer/app")
    assert not scope.owns_repository("customer/other")
    assert scope.tenant_id == "tenant-a"
