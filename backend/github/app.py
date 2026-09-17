"""HTTP onboarding and governed GitHub operations for HOARE."""

from __future__ import annotations

import os

from .broker import GitHubBroker, GitHubIntegrationError
from .permissions import GitHubAction, GitHubPermissionSet
from .repository import GitHubTransportError


def register_github_routes(routes, broker: GitHubBroker | None = None):  # noqa: ANN001
    """Register additive GitHub routes on an existing aiohttp RouteTableDef.

    The existing server middleware remains responsible for tenant/API-key
    authentication. These routes add the GitHub-specific authorization layer.
    """
    try:
        from aiohttp import web  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("aiohttp is required for GitHub routes") from exc

    github_broker = broker or GitHubBroker()

    @routes.post("/integrations/github/install")
    async def github_install(req: web.Request) -> web.Response:
        auth_ctx = req["auth_ctx"]
        body = await req.json()
        token = str(body.get("token") or os.getenv("HOARE_GITHUB_TOKEN", ""))
        if not token:
            return web.json_response(
                {"error": "GitHub installation credential is required"}, status=400
            )

        raw_permissions = body.get("permissions") or {}
        permissions = GitHubPermissionSet(
            contents_read=bool(raw_permissions.get("contents_read", True)),
            metadata_read=bool(raw_permissions.get("metadata_read", True)),
            pull_requests_read=bool(raw_permissions.get("pull_requests_read", True)),
            issues_read=bool(raw_permissions.get("issues_read", False)),
            branches_write=bool(raw_permissions.get("branches_write", False)),
            pull_requests_write=bool(raw_permissions.get("pull_requests_write", False)),
            contents_write=bool(raw_permissions.get("contents_write", False)),
            merge=bool(raw_permissions.get("merge", False)),
            deploy=bool(raw_permissions.get("deploy", False)),
            secrets_read=False,
            secrets_write=False,
        )

        try:
            result = github_broker.install(
                tenant_id=auth_ctx.tenant_id,
                installation_id=str(body["installation_id"]),
                repositories=[str(item) for item in body["repositories"]],
                permissions=permissions,
                token=token,
            )
        except (KeyError, ValueError, GitHubIntegrationError, GitHubTransportError) as exc:
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response(result, status=201)

    @routes.get("/integrations/github/repositories")
    async def github_repositories(req: web.Request) -> web.Response:
        auth_ctx = req["auth_ctx"]
        scopes = [
            scope.repository
            for (tenant_id, _repo), scope in github_broker._scopes.items()  # noqa: SLF001
            if tenant_id == auth_ctx.tenant_id
        ]
        return web.json_response({"repositories": scopes})

    @routes.get("/integrations/github/repositories/{owner}/{repo}")
    async def github_repository(req: web.Request) -> web.Response:
        auth_ctx = req["auth_ctx"]
        repository = f"{req.match_info['owner']}/{req.match_info['repo']}"
        try:
            result = github_broker.repository(
                actor=auth_ctx.api_key_id,
                tenant_id=auth_ctx.tenant_id,
                repository=repository,
            )
        except (PermissionError, GitHubIntegrationError) as exc:
            return web.json_response({"error": str(exc)}, status=403)
        return web.json_response(result)

    @routes.post("/integrations/github/analyze")
    async def github_analyze(req: web.Request) -> web.Response:
        auth_ctx = req["auth_ctx"]
        body = await req.json()
        repository = str(body["repository"])
        path = str(body.get("path", "README.md"))
        ref = body.get("ref")
        try:
            result = github_broker.contents(
                actor=auth_ctx.api_key_id,
                tenant_id=auth_ctx.tenant_id,
                repository=repository,
                path=path,
                ref=ref,
            )
        except (KeyError, PermissionError, GitHubIntegrationError) as exc:
            return web.json_response({"error": str(exc)}, status=403)
        return web.json_response({"repository": repository, "path": path, "content": result})

    @routes.post("/integrations/github/branch")
    async def github_branch(req: web.Request) -> web.Response:
        auth_ctx = req["auth_ctx"]
        body = await req.json()
        try:
            result = github_broker.create_branch(
                actor=auth_ctx.api_key_id,
                tenant_id=auth_ctx.tenant_id,
                repository=str(body["repository"]),
                branch=str(body["branch"]),
                base_sha=str(body["base_sha"]),
            )
        except (KeyError, PermissionError, GitHubIntegrationError) as exc:
            return web.json_response({"error": str(exc)}, status=403)
        return web.json_response(result, status=201)

    @routes.post("/integrations/github/pull-request")
    async def github_pull_request(req: web.Request) -> web.Response:
        auth_ctx = req["auth_ctx"]
        body = await req.json()
        try:
            result = github_broker.create_pull_request(
                actor=auth_ctx.api_key_id,
                tenant_id=auth_ctx.tenant_id,
                repository=str(body["repository"]),
                title=str(body["title"]),
                head=str(body["head"]),
                base=str(body["base"]),
                body=str(body.get("body", "")),
            )
        except (KeyError, PermissionError, GitHubIntegrationError) as exc:
            return web.json_response({"error": str(exc)}, status=403)
        return web.json_response(result, status=201)

    @routes.post("/integrations/github/action")
    async def github_action(req: web.Request) -> web.Response:
        """Evaluate an arbitrary GitHub action without bypassing AEGIS."""
        auth_ctx = req["auth_ctx"]
        body = await req.json()
        try:
            action = GitHubAction(str(body["action"]))
            request = github_broker._request(  # noqa: SLF001
                auth_ctx.tenant_id,
                str(body["repository"]),
                action,
                branch=body.get("branch"),
            )
            decision = github_broker.evaluate(actor=auth_ctx.api_key_id, request=request)
        except (KeyError, ValueError) as exc:
            return web.json_response({"error": str(exc)}, status=400)
        return web.json_response(decision.to_dict())

    @routes.get("/integrations/github/audit")
    async def github_audit(req: web.Request) -> web.Response:
        auth_ctx = req["auth_ctx"]
        try:
            limit = max(1, min(int(req.query.get("limit", "100")), 500))
        except ValueError:
            limit = 100
        return web.json_response(
            {"events": github_broker.audit.recent(auth_ctx.tenant_id, limit)}
        )

    return github_broker


__all__ = ["register_github_routes"]
