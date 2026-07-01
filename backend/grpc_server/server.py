"""
gRPC Server
===========
Binds the Hoare-Agent intelligence layer to a gRPC interface so that
AesirGrid's agents can call it over a high-throughput HTTP/2 connection.

Because generating the full protobuf stubs requires the ``grpcio-tools``
compiler (which may not be available in every environment), this module
provides a *pure-Python* asyncio gRPC server that implements the three
services defined in ``proto/hoare_agent.proto``:

  • SchemaParserService   — PDA-constrained payload parsing
  • HoareVerifierService  — Z3 proof checking
  • HoareAgentService     — end-to-end two-pass agent loop

The server also exposes a lightweight REST/JSON fallback on port 8080
(via aiohttp) so that the React dashboard and quick ad-hoc tests can
reach it without a gRPC client.

Usage
-----
    python -m grpc_server.server

Environment variables:

    HOARE_GRPC_PORT   — gRPC listen port  (default: 50051)
    HOARE_HTTP_PORT   — HTTP  listen port  (default: 8080)
    HOARE_USE_MOCK_LLM — "1" to use the mock LLM (default: "0")
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from urllib.parse import parse_qs
from typing import AsyncIterator

from schema.models import (
    AgentTaskRequest,
    FSMState,
    FSMStateEnum,
    HoareTriple,
    ParsedRecord,
    RawPayload,
    VerificationRequest,
    VerificationResult,
)
from hoare_engine.agent     import HoareAgent, AgentObserver
from hoare_engine.pda_engine import registry
from hoare_engine.verifier   import verifier
from saas.audit import AuditLogger
from saas.auth import ApiKeyAuthenticator, AuthContext
from saas.billing import BillingService
from saas.usage import UsageMeter
from integrations import connector_registry

logger = logging.getLogger(__name__)

_GRPC_PORT     = int(os.getenv("HOARE_GRPC_PORT",    "50051"))
_HTTP_PORT     = int(os.getenv("HOARE_HTTP_PORT",    "8080"))
_USE_MOCK_LLM  = os.getenv("HOARE_USE_MOCK_LLM",    "0") == "1"
_PUBLIC_PATHS = {"/health"}
_DEFAULT_AUTH_CTX = AuthContext(tenant_id="public", api_key_id="public", plan="public")


def _bearer_key_from_header(authz_header: str | None) -> str | None:
    if not authz_header:
        return None
    if not authz_header.startswith("Bearer "):
        return None
    return authz_header[len("Bearer ") :].strip() or None


def _query_limit(query_string: str, default: int = 100) -> int:
    parsed = parse_qs(query_string or "")
    value = parsed.get("limit", [str(default)])[0]
    try:
        return max(1, min(int(value), 500))
    except ValueError:
        return default

# ---------------------------------------------------------------------------
# Service implementations
# ---------------------------------------------------------------------------


class SchemaParserServicer:
    """Implements SchemaParserService."""

    async def parse_payload(self, raw: RawPayload, tenant_id: str = "public") -> ParsedRecord:
        schema_name = raw.metadata.get("schema", "TelemetryEvent")
        try:
            controller = registry.make_controller(raw.payload_id, schema_name, tenant_id=tenant_id)
        except KeyError:
            return ParsedRecord(
                payload_id=raw.payload_id,
                schema_name=schema_name,
                structured={},
                fsm_state=FSMState(
                    state=FSMStateEnum.ERROR,
                    payload_id=raw.payload_id,
                    detail=f"Unknown schema: {schema_name}",
                ),
                valid=False,
                error=f"Unknown schema: {schema_name}",
            )
        return controller.process_payload(raw)

    async def parse_stream(
        self, payloads: AsyncIterator[RawPayload]
    ) -> AsyncIterator[ParsedRecord]:
        async for raw in payloads:
            yield await self.parse_payload(raw)

    async def transition_fsm(
        self, payload_id: str, schema_name: str, target: FSMStateEnum, tenant_id: str = "public"
    ) -> FSMState:
        controller = registry.make_controller(payload_id, schema_name, tenant_id=tenant_id)
        return controller.transition(target)


class HoareVerifierServicer:
    """Implements HoareVerifierService."""

    def verify(self, request: VerificationRequest) -> VerificationResult:
        return verifier.verify(request)


class StreamingObserver(AgentObserver):
    """Collects FSM state changes for streaming to the dashboard."""

    def __init__(self) -> None:
        self._states: list[FSMState] = []

    def on_state_change(self, state: FSMStateEnum, detail: str) -> None:
        self._states.append(
            FSMState(state=state, payload_id="agent", detail=detail)
        )

    @property
    def states(self) -> list[FSMState]:
        return self._states


class HoareAgentServicer:
    """Implements HoareAgentService."""

    async def run_task(self, request: AgentTaskRequest):
        observer = StreamingObserver()
        agent = HoareAgent(use_mock_llm=_USE_MOCK_LLM, observer=observer)
        result = await asyncio.get_event_loop().run_in_executor(
            None, agent.run_task, request
        )
        return result, observer.states

    async def watch_fsm(self, raw: RawPayload) -> AsyncIterator[FSMState]:
        schema_name = raw.metadata.get("schema", "TelemetryEvent")
        tenant_id = raw.metadata.get("tenant_id", "public")
        controller  = registry.make_controller(raw.payload_id, schema_name, tenant_id=tenant_id)

        states = [
            FSMStateEnum.INGESTING,
            FSMStateEnum.PARSING,
            FSMStateEnum.VALIDATING,
            FSMStateEnum.COMMITTING,
            FSMStateEnum.COMMITTED,
        ]
        controller.transition(FSMStateEnum.INGESTING, "Stream started")
        yield controller.current_fsm_state("Stream started")

        for s in states[1:]:
            await asyncio.sleep(0.05)
            try:
                state_obj = controller.transition(s)
            except Exception:  # noqa: BLE001
                break
            yield state_obj


# ---------------------------------------------------------------------------
# Lightweight HTTP server (REST/JSON)
# ---------------------------------------------------------------------------


async def _start_http_server() -> None:
    """Start a minimal aiohttp REST server for the React dashboard."""
    try:
        from aiohttp import web  # type: ignore
    except ImportError:
        logger.warning("aiohttp not installed — HTTP server disabled.  pip install aiohttp")
        return

    parser_svc = SchemaParserServicer()
    verifier_svc = HoareVerifierServicer()
    agent_svc = HoareAgentServicer()
    authenticator = ApiKeyAuthenticator()
    usage_meter = UsageMeter()
    billing = BillingService(usage_meter)
    audit = AuditLogger()

    registry.provision_tenant("public", registry.list_schemas("public"))

    routes = web.RouteTableDef()

    @routes.get("/health")
    async def health(_req: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "timestamp": time.time()})

    @routes.post("/parse")
    async def parse(req: web.Request) -> web.Response:
        body = await req.json()
        auth_ctx: AuthContext = req["auth_ctx"]
        body.setdefault("metadata", {})
        body["metadata"]["tenant_id"] = auth_ctx.tenant_id
        raw = RawPayload(**body)
        rec = await parser_svc.parse_payload(raw, tenant_id=auth_ctx.tenant_id)
        return web.json_response(rec.model_dump(mode="json"))

    @routes.post("/verify")
    async def verify_endpoint(req: web.Request) -> web.Response:
        body    = await req.json()
        vreq    = VerificationRequest(**body)
        result  = verifier_svc.verify(vreq)
        return web.json_response(result.model_dump(mode="json"))

    @routes.post("/agent/run")
    async def run_agent(req: web.Request) -> web.Response:
        body = await req.json()
        areq = AgentTaskRequest(**body)
        result, states = await agent_svc.run_task(areq)
        return web.json_response({
            "result": result.model_dump(mode="json"),
            "fsm_states": [s.model_dump(mode="json") for s in states],
        })

    @routes.get("/schemas")
    async def list_schemas(req: web.Request) -> web.Response:
        auth_ctx: AuthContext = req["auth_ctx"]
        return web.json_response(registry.list_schemas(auth_ctx.tenant_id))

    @routes.post("/tenants/provision")
    async def provision_tenant(req: web.Request) -> web.Response:
        body = await req.json()
        tenant_id = body["tenant_id"]
        schemas = body.get("schemas")
        allowed = registry.provision_tenant(tenant_id, schemas=schemas)
        return web.json_response({"tenant_id": tenant_id, "schemas": allowed})

    @routes.get("/tenants/{tenant_id}/schemas")
    async def tenant_schemas(req: web.Request) -> web.Response:
        tenant_id = req.match_info["tenant_id"]
        return web.json_response({"tenant_id": tenant_id, "schemas": registry.list_schemas(tenant_id)})

    @routes.get("/usage/me")
    async def usage_me(req: web.Request) -> web.Response:
        auth_ctx: AuthContext = req["auth_ctx"]
        return web.json_response(usage_meter.summary(auth_ctx.tenant_id))

    @routes.post("/billing/usage")
    async def bill_usage(req: web.Request) -> web.Response:
        auth_ctx: AuthContext = req["auth_ctx"]
        body = await req.json()
        units = int(body.get("units", 0))
        result = billing.report_usage(auth_ctx.tenant_id, units)
        return web.json_response(result)

    @routes.post("/billing/checkout")
    async def billing_checkout(req: web.Request) -> web.Response:
        auth_ctx: AuthContext = req["auth_ctx"]
        body = await req.json()
        result = billing.create_checkout_session(
            tenant_id=auth_ctx.tenant_id,
            price_id=body["price_id"],
            success_url=body["success_url"],
            cancel_url=body["cancel_url"],
        )
        return web.json_response(result)

    @routes.get("/audit/events")
    async def audit_events(req: web.Request) -> web.Response:
        auth_ctx: AuthContext = req["auth_ctx"]
        limit = _query_limit(req.query_string, default=100)
        return web.json_response(audit.recent(tenant_id=auth_ctx.tenant_id, limit=limit))

    @routes.get("/audit/summary")
    async def audit_summary(req: web.Request) -> web.Response:
        auth_ctx: AuthContext = req["auth_ctx"]
        return web.json_response(audit.summary(tenant_id=auth_ctx.tenant_id))

    @routes.get("/integrations/connectors")
    async def list_connectors(_req: web.Request) -> web.Response:
        return web.json_response(connector_registry.list_connectors())

    @routes.get("/integrations/connectors/{name}/validate")
    async def validate_connector(req: web.Request) -> web.Response:
        name = req.match_info["name"]
        return web.json_response(connector_registry.validate(name))

    # CORS middleware so the React dashboard can reach the server
    @web.middleware
    async def api_gateway_middleware(request: web.Request, handler):  # noqa: ANN001
        start = time.time()
        auth_ctx = _DEFAULT_AUTH_CTX
        try:
            if request.method == "OPTIONS":
                response = web.Response()
            else:
                if request.path in _PUBLIC_PATHS:
                    auth_ctx = _DEFAULT_AUTH_CTX
                else:
                    auth_ctx = authenticator.authenticate(
                        header_key=request.headers.get("x-api-key"),
                        bearer_key=_bearer_key_from_header(request.headers.get("Authorization")),
                    )
                request["auth_ctx"] = auth_ctx
                response = await handler(request)
        except PermissionError as exc:
            auth_ctx = AuthContext(tenant_id="unknown", api_key_id="unauthorized")
            request["auth_ctx"] = auth_ctx
            response = web.json_response({"error": str(exc)}, status=401)
        except KeyError as exc:
            response = web.json_response({"error": str(exc)}, status=404)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled request error")
            response = web.json_response({"error": str(exc)}, status=500)

        tenant_id = auth_ctx.tenant_id
        if request.path not in _PUBLIC_PATHS:
            usage_meter.record_request(tenant_id, request.path)
        audit.log(
            event_type="http_request",
            tenant_id=tenant_id,
            actor=auth_ctx.api_key_id,
            method=request.method,
            path=request.path,
            status=response.status,
            elapsed_ms=round((time.time() - start) * 1000, 2),
        )
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, x-api-key"
        return response

    app = web.Application(middlewares=[api_gateway_middleware])
    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", _HTTP_PORT)  # noqa: S104
    await site.start()
    logger.info("HTTP server listening on port %d", _HTTP_PORT)


# ---------------------------------------------------------------------------
# gRPC server (graceful stub — full impl requires generated protobuf stubs)
# ---------------------------------------------------------------------------


async def _start_grpc_server() -> None:
    """
    Start the gRPC server.

    Requires: grpcio, grpcio-tools, and the generated *_pb2* / *_pb2_grpc*
    modules produced by running:

        python -m grpc_tools.protoc \
            -I proto \
            --python_out=backend/grpc_server \
            --grpc_python_out=backend/grpc_server \
            proto/hoare_agent.proto

    If the generated stubs are not present the server skips gRPC and
    operates in HTTP-only mode.
    """
    try:
        import grpc  # type: ignore
        from grpc_server import hoare_agent_pb2, hoare_agent_pb2_grpc  # type: ignore  # noqa: F401
    except ImportError:
        logger.info(
            "gRPC stubs not found — running in HTTP-only mode.  "
            "Generate stubs with: python -m grpc_tools.protoc …"
        )
        return

    server = grpc.aio.server()
    # hoare_agent_pb2_grpc.add_SchemaParserServiceServicer_to_server(...)
    server.add_insecure_port(f"[::]:{_GRPC_PORT}")
    await server.start()
    logger.info("gRPC server listening on port %d", _GRPC_PORT)
    await server.wait_for_termination()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )
    logger.info("Starting Hoare-Agent server …")
    await asyncio.gather(
        _start_http_server(),
        _start_grpc_server(),
    )


if __name__ == "__main__":
    asyncio.run(main())
