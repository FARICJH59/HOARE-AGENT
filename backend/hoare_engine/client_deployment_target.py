"""Client-project deployment target policy for HOARE.

Provenance: 2026-09-15

Cloudflare production is the default target for ordinary client application
projects. The target is a deployment preference, not execution authority.
Clients may explicitly select another supported provider/profile, and
verticals with physical or edge constraints may override the default.
"""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_CLIENT_CLOUD_PROVIDER = "cloudflare-prod"


@dataclass(frozen=True)
class ClientDeploymentTarget:
    """Resolved deployment target for a client project."""

    provider: str
    environment: str = "prod"
    explicit: bool = False

    @property
    def identifier(self) -> str:
        return f"{self.provider}-{self.environment}"


def resolve_client_deployment_target(
    requested_target: str | None = None,
) -> ClientDeploymentTarget:
    """Resolve a client project's cloud target without authorizing deployment."""

    target = (requested_target or "").strip()
    if not target:
        return ClientDeploymentTarget(
            provider="cloudflare",
            environment="prod",
            explicit=False,
        )

    if target == DEFAULT_CLIENT_CLOUD_PROVIDER:
        return ClientDeploymentTarget(
            provider="cloudflare",
            environment="prod",
            explicit=True,
        )

    if "-" not in target:
        raise ValueError("deployment target must use provider-environment form")

    provider, environment = target.rsplit("-", 1)
    if not provider or not environment:
        raise ValueError("deployment target must include provider and environment")

    return ClientDeploymentTarget(
        provider=provider,
        environment=environment,
        explicit=True,
    )


__all__ = [
    "DEFAULT_CLIENT_CLOUD_PROVIDER",
    "ClientDeploymentTarget",
    "resolve_client_deployment_target",
]
