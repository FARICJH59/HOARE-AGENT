"""Safely wire the main HOARE prompt endpoint into the existing HTTP server.

Provenance: 2026-09-16

The script is intentionally fail-closed: it refuses to modify the server if
expected anchors are missing or the route is already wired. It creates a
backup before writing. Run from the repository root.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

SERVER = Path("backend/grpc_server/server.py")
IMPORT_ANCHOR = "from integrations import connector_registry\n"
ROUTE_ANCHOR = "    routes = web.RouteTableDef()\n"
IMPORT = "from hoare_engine.prompt_api import register_prompt_platform_routes\n"
WIRING = "    register_prompt_platform_routes(routes, use_mock_llm=_USE_MOCK_LLM)\n"


def main() -> None:
    if not SERVER.exists():
        raise SystemExit(f"missing server file: {SERVER}")

    text = SERVER.read_text()
    if IMPORT in text or WIRING in text:
        raise SystemExit("prompt platform wiring already present; refusing duplicate edit")
    if IMPORT_ANCHOR not in text or ROUTE_ANCHOR not in text:
        raise SystemExit("expected server anchors not found; refusing speculative edit")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = SERVER.with_name(f"{SERVER.name}.pre-prompt-platform-{stamp}.bak")
    backup.write_text(text)

    updated = text.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT, 1)
    updated = updated.replace(ROUTE_ANCHOR, ROUTE_ANCHOR + WIRING, 1)
    SERVER.write_text(updated)
    print(f"wired prompt platform into {SERVER}")
    print(f"backup: {backup}")


if __name__ == "__main__":
    main()
