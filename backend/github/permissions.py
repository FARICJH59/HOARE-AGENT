"""GitHub permission and repository-scope contracts.

Provenance: 2026-09-13

The agent never receives these permissions directly. The broker evaluates an
explicit action request against the customer-granted repository scope first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class GitHubAction(str, Enum):
    READ_REPOSITORY = "read_repository"
    READ_CONTENTS = "read_contents"
    READ_METADATA = "read_metadata"
    READ_PULL_REQUESTS = "read_pull_requests"
    READ_ISSUES = "read_issues"
    ANALYZE = "analyze"
    CREATE_BRANCH = "create_branch"
    WRITE_CONTENTS = "write_contents"
    CREATE_PULL_REQUEST = "create_pull_request"
    MODIFY_PULL_REQUEST = "modify_pull_request"
    MERGE = "merge"
    DEPLOY = "deploy"
    READ_SECRETS = "read_secrets"
    WRITE_SECRETS = "write_secrets"


READ_ACTIONS = frozenset(
    {
        GitHubAction.READ_REPOSITORY,
        GitHubAction.READ_CONTENTS,
        GitHubAction.READ_METADATA,
        GitHubAction.READ_PULL_REQUESTS,
        GitHubAction.READ_ISSUES,
        GitHubAction.ANALYZE,
    }
)

WRITE_ACTIONS = frozenset(
    {
        GitHubAction.CREATE_BRANCH,
        GitHubAction.WRITE_CONTENTS,
        GitHubAction.CREATE_PULL_REQUEST,
        GitHubAction.MODIFY_PULL_REQUEST,
    }
)

RESTRICTED_ACTIONS = frozenset(
    {
        GitHubAction.MERGE,
        GitHubAction.DEPLOY,
        GitHubAction.READ_SECRETS,
        GitHubAction.WRITE_SECRETS,
    }
)


@dataclass(frozen=True)
class GitHubPermissionSet:
    """Customer-granted permission capabilities."""

    contents_read: bool = False
    metadata_read: bool = False
    pull_requests_read: bool = False
    issues_read: bool = False
    branches_write: bool = False
    pull_requests_write: bool = False
    contents_write: bool = False
    merge: bool = False
    deploy: bool = False
    secrets_read: bool = False
    secrets_write: bool = False

    def allows(self, action: GitHubAction) -> bool:
        mapping = {
            GitHubAction.READ_REPOSITORY: self.metadata_read,
            GitHubAction.READ_CONTENTS: self.contents_read,
            GitHubAction.READ_METADATA: self.metadata_read,
            GitHubAction.READ_PULL_REQUESTS: self.pull_requests_read,
            GitHubAction.READ_ISSUES: self.issues_read,
            GitHubAction.ANALYZE: self.contents_read and self.metadata_read,
            GitHubAction.CREATE_BRANCH: self.branches_write,
            GitHubAction.WRITE_CONTENTS: self.contents_write,
            GitHubAction.CREATE_PULL_REQUEST: self.pull_requests_write,
            GitHubAction.MODIFY_PULL_REQUEST: self.pull_requests_write,
            GitHubAction.MERGE: self.merge,
            GitHubAction.DEPLOY: self.deploy,
            GitHubAction.READ_SECRETS: self.secrets_read,
            GitHubAction.WRITE_SECRETS: self.secrets_write,
        }
        return bool(mapping.get(action, False))

    def to_dict(self) -> dict[str, bool]:
        return {
            "contents_read": self.contents_read,
            "metadata_read": self.metadata_read,
            "pull_requests_read": self.pull_requests_read,
            "issues_read": self.issues_read,
            "branches_write": self.branches_write,
            "pull_requests_write": self.pull_requests_write,
            "contents_write": self.contents_write,
            "merge": self.merge,
            "deploy": self.deploy,
            "secrets_read": self.secrets_read,
            "secrets_write": self.secrets_write,
        }


@dataclass(frozen=True)
class GitHubRepositoryScope:
    """Tenant-bound repository authorization scope."""

    tenant_id: str
    installation_id: str
    repository: str
    permissions: GitHubPermissionSet
    allowed_branches: tuple[str, ...] = ()
    production_branches: tuple[str, ...] = ("main", "master", "production")
    metadata: dict[str, str] = field(default_factory=dict)

    def owns_repository(self, repository: str) -> bool:
        return repository == self.repository

    def branch_allowed(self, branch: str) -> bool:
        return not self.allowed_branches or branch in self.allowed_branches

    def is_production_branch(self, branch: str) -> bool:
        return branch in self.production_branches


__all__ = [
    "GitHubAction",
    "GitHubPermissionSet",
    "GitHubRepositoryScope",
    "READ_ACTIONS",
    "RESTRICTED_ACTIONS",
    "WRITE_ACTIONS",
]
