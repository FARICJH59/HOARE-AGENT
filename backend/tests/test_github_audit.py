"""GitHub governance audit tests."""

from github.audit import GitHubAuditLog


def test_audit_events_are_tenant_scoped() -> None:
    audit = GitHubAuditLog()
    audit.log(
        tenant_id="tenant-a",
        actor="api-key-1",
        repository="customer/app",
        action="create_branch",
        decision="ALLOW",
        request_id="r1",
    )
    audit.log(
        tenant_id="tenant-b",
        actor="api-key-2",
        repository="other/app",
        action="read_contents",
        decision="ALLOW",
        request_id="r2",
    )

    events = audit.recent("tenant-a")
    assert len(events) == 1
    assert events[0]["repository"] == "customer/app"
    assert events[0]["request_id"] == "r1"
