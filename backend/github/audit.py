"""Structured audit events for governed GitHub operations."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from threading import Lock


@dataclass(frozen=True)
class GitHubAuditEvent:
    event_type: str
    tenant_id: str
    actor: str
    repository: str
    action: str
    decision: str
    request_id: str
    branch: str | None = None
    details: dict | None = None
    timestamp: float = 0.0


class GitHubAuditLog:
    """Bounded in-memory audit log; replace storage with durable audit storage in production."""

    def __init__(self, max_events: int = 5000) -> None:
        self._max_events = max(1, max_events)
        self._events: list[GitHubAuditEvent] = []
        self._lock = Lock()

    def record(self, event: GitHubAuditEvent) -> None:
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                del self._events[: len(self._events) - self._max_events]

    def log(
        self,
        *,
        tenant_id: str,
        actor: str,
        repository: str,
        action: str,
        decision: str,
        request_id: str,
        branch: str | None = None,
        details: dict | None = None,
    ) -> GitHubAuditEvent:
        event = GitHubAuditEvent(
            event_type="github_governed_action",
            tenant_id=tenant_id,
            actor=actor,
            repository=repository,
            action=action,
            decision=decision,
            request_id=request_id,
            branch=branch,
            details=details or {},
            timestamp=time.time(),
        )
        self.record(event)
        return event

    def recent(self, tenant_id: str, limit: int = 100) -> list[dict]:
        with self._lock:
            events = [event for event in self._events if event.tenant_id == tenant_id]
        return [asdict(event) for event in events[-max(1, min(limit, 500)) :]][::-1]


__all__ = ["GitHubAuditEvent", "GitHubAuditLog"]
