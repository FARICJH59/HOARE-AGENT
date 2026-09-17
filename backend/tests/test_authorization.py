from __future__ import annotations

import pytest

from saas.auth import AuthContext
from saas.authorization import TenantAuthorizationError, require_tenant_access


def test_tenant_owner_can_access_own_tenant():
    require_tenant_access(
        AuthContext(tenant_id="tenant-a", api_key_id="key-a"),
        "tenant-a",
    )


def test_tenant_owner_cannot_access_another_tenant():
    with pytest.raises(TenantAuthorizationError, match="tenant access denied"):
        require_tenant_access(
            AuthContext(tenant_id="tenant-a", api_key_id="key-a"),
            "tenant-b",
        )


def test_missing_tenant_identity_is_denied():
    with pytest.raises(TenantAuthorizationError, match="authenticated tenant is required"):
        require_tenant_access(
            AuthContext(tenant_id="", api_key_id="key-a"),
            "tenant-a",
        )


def test_public_context_cannot_claim_tenant_ownership():
    with pytest.raises(TenantAuthorizationError, match="authenticated tenant is required"):
        require_tenant_access(
            AuthContext(tenant_id="public", api_key_id="anonymous"),
            "tenant-a",
        )


def test_missing_requested_tenant_is_denied():
    with pytest.raises(TenantAuthorizationError, match="tenant_id is required"):
        require_tenant_access(
            AuthContext(tenant_id="tenant-a", api_key_id="key-a"),
            "",
        )
