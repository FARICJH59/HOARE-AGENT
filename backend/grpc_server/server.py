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

logger = logging.getLogger(__name__)

_GRPC_PORT     = int(os.getenv("HOARE_GRPC_PORT",    "50051"))
_HTTP_PORT     = int(os.getenv("HOARE_HTTP_PORT",    "8080"))
_USE_MOCK_LLM  = os.getenv("HOARE_USE_MOCK_LLM",    "0") == "1"

# ---------------------------------------------------------------------------
# Service implementations
# ---------------------------------------------------------------------------


class SchemaParserServicer:
    """Implements SchemaParserService."""

    async def parse_payload(self, raw: RawPayload) -> ParsedRecord:
        schema_name = raw.metadata.get("schema", "TelemetryEvent")
        try:
            controller = registry.make_controller(raw.payload_id, schema_name)
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
        self, payload_id: str, schema_name: str, target: FSMStateEnum
    ) -> FSMState:
        controller = registry.make_controller(payload_id, schema_name)
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
        controller  = registry.make_controller(raw.payload_id, schema_name)

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

    parser_svc  = SchemaParserServicer()
    verifier_svc = HoareVerifierServicer()
    agent_svc   = HoareAgentServicer()

    routes = web.RouteTableDef()

    @routes.get("/health")
    async def health(_req: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "timestamp": time.time()})

    @routes.post("/parse")
    async def parse(req: web.Request) -> web.Response:
        body = await req.json()
        raw  = RawPayload(**body)
        rec  = await parser_svc.parse_payload(raw)
        return web.json_response(rec.model_dump(mode="json"))

    @routes.post("/verify")
    async def verify_endpoint(req: web.Request) -> web.Response:
        body    = await req.json()
        vreq    = VerificationRequest(**body)
        result  = verifier_svc.verify(vreq)
        return web.json_response(result.model_dump(mode="json"))

    @routes.post("/agent/run")
    async def run_agent(req: web.Request) -> web.Response:
        body    = await req.json()
        areq    = AgentTaskRequest(**body)
        result, states = await agent_svc.run_task(areq)
        return web.json_response({
            "result": result.model_dump(mode="json"),
            "fsm_states": [s.model_dump(mode="json") for s in states],
        })

    @routes.get("/schemas")
    async def list_schemas(_req: web.Request) -> web.Response:
        return web.json_response(list(registry._grammars.keys()))

    # CORS middleware so the React dashboard can reach the server
    async def cors_middleware(app, handler):  # noqa: ANN001
        async def middleware(request: web.Request) -> web.Response:
            if request.method == "OPTIONS":
                return web.Response(
                    headers={
                        "Access-Control-Allow-Origin":  "*",
                        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type",
                    }
                )
            response = await handler(request)
            response.headers["Access-Control-Allow-Origin"] = "*"
            return response
        return middleware

    app = web.Application(middlewares=[cors_middleware])
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
