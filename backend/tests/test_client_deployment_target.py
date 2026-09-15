"""Tests for client-project deployment target resolution.

Provenance: 2026-09-15
"""

import pytest

from hoare_engine.client_deployment_target import (
    DEFAULT_CLIENT_CLOUD_PROVIDER,
    resolve_client_deployment_target,
)


def test_client_projects_default_to_cloudflare_production():
    target = resolve_client_deployment_target()

    assert DEFAULT_CLIENT_CLOUD_PROVIDER == "cloudflare-prod"
    assert target.provider == "cloudflare"
    assert target.environment == "prod"
    assert target.identifier == "cloudflare-prod"
    assert target.explicit is False


def test_client_projects_can_explicitly_select_cloudflare_production():
    target = resolve_client_deployment_target("cloudflare-prod")

    assert target.identifier == "cloudflare-prod"
    assert target.explicit is True


def test_client_projects_can_override_default_provider():
    target = resolve_client_deployment_target("aws-prod")

    assert target.provider == "aws"
    assert target.environment == "prod"
    assert target.identifier == "aws-prod"
    assert target.explicit is True


def test_invalid_target_form_fails_closed():
    with pytest.raises(ValueError, match="provider-environment"):
        resolve_client_deployment_target("cloudflare")
