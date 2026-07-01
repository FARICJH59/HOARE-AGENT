from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class AuthContext:
    tenant_id: str
    api_key_id: str
    plan: str = "free"


class ApiKeyAuthenticator:
    """API-key authenticator for gateway-style tenant isolation."""

    def __init__(self) -> None:
        self.require_auth = os.getenv("HOARE_REQUIRE_AUTH", "0") == "1"
        self._keys = self._load_keys()

    @staticmethod
    def _load_keys() -> Dict[str, AuthContext]:
        raw = os.getenv("HOARE_API_KEYS", "")
        if not raw:
            return {}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError("HOARE_API_KEYS must be valid JSON") from exc

        keys: Dict[str, AuthContext] = {}
        for api_key, info in payload.items():
            if isinstance(info, str):
                keys[api_key] = AuthContext(tenant_id=info, api_key_id=api_key)
                continue
            keys[api_key] = AuthContext(
                tenant_id=info.get("tenant_id", "public"),
                api_key_id=api_key,
                plan=info.get("plan", "free"),
            )
        return keys

    def authenticate(self, header_key: str | None, bearer_key: str | None) -> AuthContext:
        api_key = header_key or bearer_key
        if not self._keys:
            if self.require_auth:
                raise PermissionError("Authentication required but HOARE_API_KEYS is empty")
            return AuthContext(tenant_id="public", api_key_id="anonymous", plan="free")

        if not api_key or api_key not in self._keys:
            raise PermissionError("Invalid or missing API key")
        return self._keys[api_key]

