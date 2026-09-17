from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from saas.auth import ApiKeyAuthenticator


def test_auth_requires_configuration_by_default(monkeypatch):
    monkeypatch.delenv("HOARE_API_KEYS", raising=False)
    monkeypatch.delenv("HOARE_REQUIRE_AUTH", raising=False)

    auth = ApiKeyAuthenticator()

    with pytest.raises(PermissionError, match="Authentication required"):
        auth.authenticate(header_key=None, bearer_key=None)


def test_auth_can_be_explicitly_disabled_for_development(monkeypatch):
    monkeypatch.delenv("HOARE_API_KEYS", raising=False)
    monkeypatch.setenv("HOARE_REQUIRE_AUTH", "0")

    auth = ApiKeyAuthenticator()
    ctx = auth.authenticate(header_key=None, bearer_key=None)

    assert ctx.tenant_id == "public"
    assert ctx.api_key_id == "anonymous"
