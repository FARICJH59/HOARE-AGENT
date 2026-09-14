"""Tests for the additive GitHub HTTP route registration surface.

Provenance: 2026-09-13
"""

from __future__ import annotations

import pytest


aiohttp = pytest.importorskip("aiohttp")

from github.app import register_github_routes  # noqa: E402


def test_register_github_routes_adds_governed_endpoints():
    from aiohttp import web

    routes = web.RouteTableDef()
    register_github_routes(routes)

    paths = {
        resource.canonical
        for resource in routes
        if hasattr(resource, "canonical")
    }

    expected = {
        "/integrations/github/install",
        "/integrations/github/repositories",
        "/integrations/github/repositories/{owner}/{repo}",
        "/integrations/github/analyze",
        "/integrations/github/branch",
        "/integrations/github/pull-request",
        "/integrations/github/action",
        "/integrations/github/audit",
    }

    assert expected <= paths
