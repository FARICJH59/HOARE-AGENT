"""Broker tests prove transport is behind AEGIS."""

import pytest

from github.broker import GitHubBroker
from github.permissions import GitHubPermissionSet
from github.policy import AegisDecision, GitHubActionRequest


class FakeClient:
    def __init__(self):
        self.calls = []

    def repository(self, repository):
        self.calls.append(("repository", repository))
        return {"full_name": repository}

    def contents(self, repository, path="", ref=None):
        self.calls.append(("contents", repository, path, ref))
        return {"path": path, "ref": ref}


def _install(broker: GitHubBroker) -> None:
    broker.install(
        tenant_id="tenant-a",
        installation_id="installation-1",
        repositories=["customer/app"],
        permissions=GitHubPermissionSet(contents_read=True, metadata_read=True),
        token="test-token",
    )


def test_broker_allows_scoped_read() -> None:
    broker = GitHubBroker()
    _install(broker)
    broker._clients[("tenant-a", "customer/app")] = FakeClient()  # noqa: SLF001

    result = broker.contents(
        actor="api-key",
        tenant_id="tenant-a",
        repository="customer/app",
        path="README.md",
    )

    assert result["path"] == "README.md"
    assert broker.audit.recent("tenant-a")[0]["decision"] == AegisDecision.ALLOW.value


def test_broker_denies_out_of_scope_repository_before_transport() -> None:
    broker = GitHubBroker()
    _install(broker)
    with pytest.raises(PermissionError, match="DENY"):
        broker.contents(
            actor="api-key",
            tenant_id="tenant-a",
            repository="customer/other",
            path="README.md",
        )


def test_broker_does_not_expose_secret_permission() -> None:
    broker = GitHubBroker()
    _install(broker)
    decision = broker.evaluate(
        actor="api-key",
        request=GitHubActionRequest(
            tenant_id="tenant-a",
            repository="customer/app",
            action="read_secrets",
            request_id="secret-test",
        ),
    )
    assert decision.decision is AegisDecision.DENY
