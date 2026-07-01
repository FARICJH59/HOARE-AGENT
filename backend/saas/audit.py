from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Deque, Dict, List

logger = logging.getLogger("audit")


class AuditLogger:
    """Structured JSON audit log with in-memory event retention."""

    def __init__(self, max_events: int = 1000) -> None:
        self._events: Deque[Dict[str, Any]] = deque(maxlen=max_events)
        self._lock = Lock()

    def log(self, event_type: str, tenant_id: str, actor: str, **details: Any) -> Dict[str, Any]:
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "tenant_id": tenant_id,
            "actor": actor,
            "details": details,
        }
        with self._lock:
            self._events.appendleft(event)
        logger.info(json.dumps(event, sort_keys=True))
        return event

    def recent(self, tenant_id: str | None = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            events = list(self._events)
        if tenant_id:
            events = [e for e in events if e["tenant_id"] == tenant_id]
        return events[: max(1, min(limit, 500))]

    def summary(self, tenant_id: str | None = None) -> Dict[str, Any]:
        events = self.recent(tenant_id=tenant_id, limit=500)
        counts: Dict[str, int] = {}
        for event in events:
            key = event["event_type"]
            counts[key] = counts.get(key, 0) + 1
        return {
            "tenant_id": tenant_id or "all",
            "events_sampled": len(events),
            "event_type_counts": counts,
        }

