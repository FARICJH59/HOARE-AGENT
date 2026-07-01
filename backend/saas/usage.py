from __future__ import annotations

from threading import Lock
from typing import Dict


class UsageMeter:
    """In-memory per-tenant request and usage counter."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._request_counts: Dict[str, int] = {}
        self._endpoint_counts: Dict[str, Dict[str, int]] = {}
        self._usage_units: Dict[str, int] = {}

    def record_request(self, tenant_id: str, endpoint: str) -> None:
        with self._lock:
            self._request_counts[tenant_id] = self._request_counts.get(tenant_id, 0) + 1
            tenant_endpoints = self._endpoint_counts.setdefault(tenant_id, {})
            tenant_endpoints[endpoint] = tenant_endpoints.get(endpoint, 0) + 1

    def record_usage_units(self, tenant_id: str, units: int) -> None:
        try:
            safe_units = max(0, int(units))
        except (TypeError, ValueError):
            safe_units = 0
        with self._lock:
            self._usage_units[tenant_id] = self._usage_units.get(tenant_id, 0) + safe_units

    def summary(self, tenant_id: str) -> Dict[str, object]:
        with self._lock:
            return {
                "tenant_id": tenant_id,
                "requests_total": self._request_counts.get(tenant_id, 0),
                "usage_units_total": self._usage_units.get(tenant_id, 0),
                "by_endpoint": dict(self._endpoint_counts.get(tenant_id, {})),
            }
