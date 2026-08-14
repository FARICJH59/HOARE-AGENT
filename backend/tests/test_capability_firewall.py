import os

import pytest

from saas.capability_firewall import CapabilityFirewall


def test_tenant_can_use_public_capability(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOARE_INTERNAL_SERVICE_KEY", raising=False)
    monkeypatch.delenv("PUBLIC_CAPABILITIES", raising=False)
    decision = CapabilityFirewall().authorize("agent.run", tenant_id="tenant_001")
    assert decision.allowed is True
    assert decision.internal is False


def test_anonymous_tenant_is_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("HOARE_INTERNAL_SERVICE_KEY", raising=False)
    decision = CapabilityFirewall().authorize("agent.run", tenant_id="public")
    assert decision.allowed is False
    assert decision.reason == "authenticated_tenant_required"


def test_private_capability_is_denied_to_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOARE_INTERNAL_SERVICE_KEY", "internal-secret")
    decision = CapabilityFirewall().authorize("enterprise_control", tenant_id="tenant_001")
    assert decision.allowed is False
    assert decision.reason == "private_capability_forbidden"


def test_private_capability_requires_internal_service_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HOARE_INTERNAL_SERVICE_KEY", "internal-secret")
    denied = CapabilityFirewall().authorize(
        "enterprise_control", tenant_id="tenant_001", internal_service_key="wrong"
    )
    allowed = CapabilityFirewall().authorize(
        "enterprise_control", tenant_id="tenant_001", internal_service_key="internal-secret"
    )
    assert denied.allowed is False
    assert allowed.allowed is True
    assert allowed.internal is True


def test_unknown_capability_is_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PUBLIC_CAPABILITIES", raising=False)
    decision = CapabilityFirewall().authorize("brain.secret", tenant_id="tenant_001")
    assert decision.allowed is False
    assert decision.reason == "private_capability_forbidden"


def test_custom_public_allowlist_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_CAPABILITIES", "agent.run,custom.read")
    firewall = CapabilityFirewall()
    assert firewall.authorize("custom.read", tenant_id="tenant_001").allowed is True
    assert firewall.authorize("pasor.execute", tenant_id="tenant_001").allowed is False
