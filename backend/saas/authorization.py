from __future__ import annotations

from saas.auth import AuthContext


class TenantAuthorizationError(PermissionError):
    """Raised when an authenticated principal targets another tenant."""


def require_tenant_access(auth_ctx: AuthContext, requested_tenant_id: str) -> None:
    """Require an authenticated context to operate on its own tenant.

    Authentication establishes who the caller is; this function enforces the
    separate tenant-ownership boundary before tenant-scoped resources are
    accessed or mutated.
    """
    if not auth_ctx.tenant_id or auth_ctx.tenant_id in {"unknown", "public"}:
        raise TenantAuthorizationError("authenticated tenant is required")
    if not requested_tenant_id:
        raise TenantAuthorizationError("tenant_id is required")
    if auth_ctx.tenant_id != requested_tenant_id:
        raise TenantAuthorizationError("tenant access denied")
