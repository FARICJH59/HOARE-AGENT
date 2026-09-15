"""Governed GitHub integration boundary for HOARE."""

from .broker import GitHubBroker, GitHubIntegrationError
from .permissions import GitHubAction, GitHubPermissionSet, GitHubRepositoryScope
from .policy import AegisDecision, AegisGitHubGate, GitHubActionRequest

__all__ = [
    "AegisDecision",
    "AegisGitHubGate",
    "GitHubAction",
    "GitHubActionRequest",
    "GitHubBroker",
    "GitHubIntegrationError",
    "GitHubPermissionSet",
    "GitHubRepositoryScope",
]
