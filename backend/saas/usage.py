from __future__ import annotations

from collections import defaultdict
from threading import Lock
from typing import DefaultDict, Dict


class UsageMeter:
    """In-memory per-tenant request and usage counter."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._request_counts: DefaultDict[str, int] = defaultdict(int)
        self._endpoint_counts: DefaultDict[str, DefaultDict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._usage_units: DefaultDict[str, int] = defaultdict(int)

    def record_request(self, tenant_id: str, endpoint: str) -> None:
        with self._lock:
            self._request_counts[tenant_id] += 1
            self._endpoint_counts[tenant_id][endpoint] += 1

    def record_usage_units(self, tenant_id: str, units: int) -> None:
        with self._lock:
            self._usage_units[tenant_id] += max(0, int(units))

    def summary(self, tenant_id: str) -> Dict[str, object]:
        with self._lock:
            return {
                "tenant_id": tenant_id,
                "requests_total": self._request_counts[tenant_id],
                "usage_units_total": self._usage_units[tenant_id],
                "by_endpoint": dict(self._endpoint_counts[tenant_id]),
            }

