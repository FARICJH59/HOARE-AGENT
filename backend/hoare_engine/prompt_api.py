"""REST route registrar for the main HOARE prompt-to-build platform.

Provenance: 2026-09-16

The registrar is additive: it plugs into the existing aiohttp RouteTableDef.
Authentication remains the existing server middleware responsibility. Build
execution remains bounded by the prompt-platform orchestration layer.
"""
from __future__ import annotations

import uuid

from hoare_engine.prompt_platform import build_from_prompt, result_to_dict


def register_prompt_platform_routes(routes, *, use_mock_llm: bool = False) -> None:
    """Register the primary natural-language project entry point."""

    from aiohttp import web

    @routes.post("/hoare/projects/build")
    async def build_project(req: web.Request) -> web.Response:
        body = await req.json()
        prompt = str(body.get("prompt", "")).strip()
        project_id = str(body.get("project_id") or f"hoare-{uuid.uuid4().hex[:12]}")
        max_retries = int(body.get("max_retries", 3))

        result = await __import__("asyncio").get_running_loop().run_in_executor(
            None,
            lambda: build_from_prompt(
                prompt,
                project_id=project_id,
                use_mock_llm=use_mock_llm,
                max_retries=max_retries,
            ),
        )
        return web.json_response(result_to_dict(result))

    @routes.get("/hoare/projects/build/capabilities")
    async def build_capabilities(_req: web.Request) -> web.Response:
        return web.json_response(
            {
                "entrypoint": "/hoare/projects/build",
                "input": "natural-language prompt",
                "pipeline": [
                    "INTENT",
                    "UNDERSTAND",
                    "ARCHITECT",
                    "PLAN",
                    "BUILD",
                    "VERIFY",
                    "STAGED",
                ],
                "execution_authorized_by_generation": False,
                "deployment_authorized_by_generation": False,
            }
        )
