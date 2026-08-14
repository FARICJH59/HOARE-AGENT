"""
gRPC/HTTP server for Hoare-Agent.

Tenant-facing requests are authenticated and pass through the capability
firewall before agent execution. Privileged HOARE control capabilities require
the separate internal service key and are never tenant-authorized.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from urllib.parse import parse_qs
from typing import AsyncIterator

from schema.models import AgentTaskRequest, FSMState, FSMStateEnum, ParsedRecord, RawPayload, VerificationRequest, VerificationResult
from hoare_engine.agent import HoareAgent, AgentObserver
from hoare_engine.pda_engine import registry
from hoare_engine.verifier import verifier
from saas.audit import AuditLogger
from saas.auth import ApiKeyAuthenticator, AuthContext
from saas.billing import BillingService
from saas.capability_firewall import CapabilityFirewall
from saas.usage import UsageMeter
from integrations import connector_registry

logger = logging.getLogger(__name__)
_GRPC_PORT = int(os.getenv("HOARE_GRPC_PORT", "50051"))
_HTTP_PORT = int(os.getenv("HOARE_HTTP_PORT", "8080"))
_USE_MOCK_LLM = os.getenv("HOARE_USE_MOCK_LLM", "0") == "1"
_PUBLIC_PATHS = {"/health"}
_DEFAULT_AUTH_CTX = AuthContext(tenant_id="public", api_key_id="public", plan="public")


def _bearer_key_from_header(authz_header: str | None) -> str | None:
    if not authz_header or not authz_header.startswith("Bearer "):
        return None
    return authz_header[len("Bearer ") :].strip() or None


def _query_limit(query_string: str, default: int = 100) -> int:
    parsed = parse_qs(query_string or "")
    try:
        return max(1, min(int(parsed.get("limit", [str(default)])[0]), 500))
    except ValueError:
        return default


class SchemaParserServicer:
    async def parse_payload(self, raw: RawPayload, tenant_id: str = "public") -> ParsedRecord:
        schema_name = raw.metadata.get("schema", "TelemetryEvent")
        try:
            controller = registry.make_controller(raw.payload_id, schema_name, tenant_id=tenant_id)
        except KeyError:
            return ParsedRecord(payload_id=raw.payload_id, schema_name=schema_name, structured={}, fsm_state=FSMState(state=FSMStateEnum.ERROR, payload_id=raw.payload_id, detail=f"Unknown schema: {schema_name}"), valid=False, error=f"Unknown schema: {schema_name}")
        return controller.process_payload(raw)

    async def parse_stream(self, payloads: AsyncIterator[RawPayload]) -> AsyncIterator[ParsedRecord]:
        async for raw in payloads:
            yield await self.parse_payload(raw)

    async def transition_fsm(self, payload_id: str, schema_name: str, target: FSMStateEnum, tenant_id: str = "public") -> FSMState:
        controller = registry.make_controller(payload_id, schema_name, tenant_id=tenant_id)
        return controller.transition(target)


class HoareVerifierServicer:
    def verify(self, request: VerificationRequest) -> VerificationResult:
        return verifier.verify(request)


class StreamingObserver(AgentObserver):
    def __init__(self) -> None:
        self._states: list[FSMState] = []

    def on_state_change(self, state: FSMStateEnum, detail: str) -> None:
        self._states.append(FSMState(state=state, payload_id="agent", detail=detail))

    @property
    def states(self) -> list[FSMState]:
        return self._states


class HoareAgentServicer:
    async def run_task(self, request: AgentTaskRequest):
        observer = StreamingObserver()
        agent = HoareAgent(use_mock_llm=_USE_MOCK_LLM, observer=observer)
        result = await asyncio.get_event_loop().run_in_executor(None, agent.run_task, request)
        return result, observer.states

    async def watch_fsm(self, raw: RawPayload) -> AsyncIterator[FSMState]:
        schema_name = raw.metadata.get("schema", "TelemetryEvent")
        tenant_id = raw.metadata.get("tenant_id", "public")
        controller = registry.make_controller(raw.payload_id, schema_name, tenant_id=tenant_id)
        states = [FSMStateEnum.INGESTING, FSMStateEnum.PARSING, FSMStateEnum.VALIDATING, FSMStateEnum.COMMITTING, FSMStateEnum.COMMITTED]
        controller.transition(FSMStateEnum.INGESTING, "Stream started")
        yield controller.current_fsm_state("Stream started")
        for state in states[1:]:
            await asyncio.sleep(0.05)
            try:
                state_obj = controller.transition(state)
            except Exception:
                break
            yield state_obj


async def _start_http_server() -> None:
    try:
        from aiohttp import web
    except ImportError:
        logger.warning("aiohttp not installed — HTTP server disabled")
        return

    parser_svc, verifier_svc, agent_svc = SchemaParserServicer(), HoareVerifierServicer(), HoareAgentServicer()
    authenticator, firewall = ApiKeyAuthenticator(), CapabilityFirewall()
    usage_meter, billing, audit = UsageMeter(), None, AuditLogger()
    billing = BillingService(usage_meter)
    registry.provision_tenant("public", registry.list_schemas("public"))
    routes = web.RouteTableDef()

    @routes.get("/health")
    async def health(_req: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "timestamp": time.time()})

    @routes.post("/parse")
    async def parse(req: web.Request) -> web.Response:
        body = await req.json()
        auth_ctx = req["auth_ctx"]
        body.setdefault("metadata", {})["tenant_id"] = auth_ctx.tenant_id
        rec = await parser_svc.parse_payload(RawPayload(**body), tenant_id=auth_ctx.tenant_id)
        return web.json_response(rec.model_dump(mode="json"))

    @routes.post("/verify")
    async def verify_endpoint(req: web.Request) -> web.Response:
        result = verifier_svc.verify(VerificationRequest(**(await req.json())))
        return web.json_response(result.model_dump(mode="json"))

    @routes.post("/agent/run")
    async def run_agent(req: web.Request) -> web.Response:
        areq = AgentTaskRequest(**(await req.json()))
        auth_ctx = req["auth_ctx"]
        decision = firewall.authorize(areq.capability, tenant_id=auth_ctx.tenant_id, internal_service_key=req.headers.get("x-hoare-service-key"), entitled=True)
        audit.log(event_type="capability_decision", tenant_id=auth_ctx.tenant_id, actor=auth_ctx.api_key_id, capability=areq.capability, allowed=decision.allowed, reason=decision.reason, internal=decision.internal)
        if not decision.allowed:
            return web.json_response({"error": "CAPABILITY_FORBIDDEN", "capability": areq.capability, "reason": decision.reason}, status=403)
        result, states = await agent_svc.run_task(areq)
        return web.json_response({"result": result.model_dump(mode="json"), "fsm_states": [s.model_dump(mode="json") for s in states]})

    @routes.get("/schemas")
    async def list_schemas(req: web.Request) -> web.Response:
        return web.json_response(registry.list_schemas(req["auth_ctx"].tenant_id))

    @routes.post("/tenants/provision")
    async def provision_tenant(req: web.Request) -> web.Response:
        body = await req.json()
        allowed = registry.provision_tenant(body["tenant_id"], schemas=body.get("schemas"))
        return web.json_response({"tenant_id": body["tenant_id"], "schemas": allowed})

    @routes.get("/tenants/{tenant_id}/schemas")
    async def tenant_schemas(req: web.Request) -> web.Response:
        tenant_id = req.match_info["tenant_id"]
        return web.json_response({"tenant_id": tenant_id, "schemas": registry.list_schemas(tenant_id)})

    @routes.get("/usage/me")
    async def usage_me(req: web.Request) -> web.Response:
        return web.json_response(usage_meter.summary(req["auth_ctx"].tenant_id))

    @routes.post("/billing/usage")
    async def bill_usage(req: web.Request) -> web.Response:
        auth_ctx = req["auth_ctx"]
        return web.json_response(billing.report_usage(auth_ctx.tenant_id, int((await req.json()).get("units", 0))))

    @routes.post("/billing/checkout")
    async def billing_checkout(req: web.Request) -> web.Response:
        auth_ctx, body = req["auth_ctx"], await req.json()
        return web.json_response(billing.create_checkout_session(tenant_id=auth_ctx.tenant_id, price_id=body["price_id"], success_url=body["success_url"], cancel_url=body["cancel_url"]))

    @routes.get("/audit/events")
    async def audit_events(req: web.Request) -> web.Response:
        return web.json_response(audit.recent(tenant_id=req["auth_ctx"].tenant_id, limit=_query_limit(req.query_string)))

    @routes.get("/audit/summary")
    async def audit_summary(req: web.Request) -> web.Response:
        return web.json_response(audit.summary(tenant_id=req["auth_ctx"].tenant_id))

    @routes.get("/integrations/connectors")
    async def list_connectors(_req: web.Request) -> web.Response:
        return web.json_response(connector_registry.list_connectors())

    @routes.get("/integrations/connectors/{name}/validate")
    async def validate_connector(req: web.Request) -> web.Response:
        return web.json_response(connector_registry.validate(req.match_info["name"]))

    @web.middleware
    async def api_gateway_middleware(request: web.Request, handler):
        start = time.time()
        auth_ctx = _DEFAULT_AUTH_CTX
        try:
            if request.method == "OPTIONS":
                response = web.Response()
            elif request.path in _PUBLIC_PATHS:
                request["auth_ctx"] = auth_ctx
                response = await handler(request)
            else:
                internal_key = request.headers.get("x-hoare-service-key")
                configured_internal = os.getenv("HOARE_INTERNAL_SERVICE_KEY", "")
                if internal_key and configured_internal and __import__("hmac").compare_digest(internal_key, configured_internal):
                    auth_ctx = AuthContext(tenant_id="hoare-internal", api_key_id="internal-service", plan="internal")
                else:
                    auth_ctx = authenticator.authenticate(header_key=request.headers.get("x-api-key"), bearer_key=_bearer_key_from_header(request.headers.get("Authorization")))
                request["auth_ctx"] = auth_ctx
                response = await handler(request)
        except PermissionError as exc:
            auth_ctx = AuthContext(tenant_id="unknown", api_key_id="unauthorized")
            request["auth_ctx"] = auth_ctx
            response = web.json_response({"error": "UNAUTHORIZED", "detail": str(exc)}, status=401)
        except KeyError as exc:
            response = web.json_response({"error": str(exc)}, status=404)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as exc:
            logger.exception("Unhandled request error")
            response = web.json_response({"error": str(exc)}, status=500)

        tenant_id = auth_ctx.tenant_id
        if request.path not in _PUBLIC_PATHS:
            usage_meter.record_request(tenant_id, request.path)
        audit.log(event_type="http_request", tenant_id=tenant_id, actor=auth_ctx.api_key_id, method=request.method, path=request.path, status=response.status, elapsed_ms=round((time.time() - start) * 1000, 2))
        response.headers["Access-Control-Allow-Origin"] = os.getenv("HOARE_CORS_ORIGIN", "")
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, x-api-key, x-hoare-service-key"
        return response

    app = web.Application(middlewares=[api_gateway_middleware])
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", _HTTP_PORT).start()
    logger.info("HTTP server listening on port %d", _HTTP_PORT)


async def _start_grpc_server() -> None:
    try:
        import grpc
        from grpc_server import hoare_agent_pb2, hoare_agent_pb2_grpc  # noqa: F401
    except ImportError:
        logger.info("gRPC stubs not found — running in HTTP-only mode")
        return
    server = grpc.aio.server()
    server.add_insecure_port(f"[::]:{_GRPC_PORT}")
    await server.start()
    logger.info("gRPC server listening on port %d", _GRPC_PORT)
    await server.wait_for_termination()


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
    logger.info("Starting Hoare-Agent server …")
    await asyncio.gather(_start_http_server(), _start_grpc_server())


if __name__ == "__main__":
    asyncio.run(main())
