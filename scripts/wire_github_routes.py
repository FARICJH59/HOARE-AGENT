#!/usr/bin/env python3
"""Safely wire the governed GitHub routes into the existing HOARE HTTP server.

Provenance: 2026-09-13

This migration is intentionally additive. It refuses to edit the server if the
expected integration points are missing or if the wiring is already present.
It creates a timestamped backup before changing the file.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


SERVER = Path("backend/grpc_server/server.py")
IMPORT_ANCHOR = "from integrations import connector_registry\n"
IMPORT_LINE = "from github.app import register_github_routes\n"
ROUTE_ANCHOR = "    routes = web.RouteTableDef()\n"
ROUTE_LINE = "    register_github_routes(routes)\n"


def main() -> int:
    if not SERVER.exists():
        raise SystemExit(f"Missing expected server file: {SERVER}")

    text = SERVER.read_text(encoding="utf-8")

    if IMPORT_LINE in text or ROUTE_LINE in text:
        raise SystemExit("GitHub governed routes are already wired; refusing to duplicate them.")

    if IMPORT_ANCHOR not in text:
        raise SystemExit("Expected import anchor was not found; refusing speculative edit.")

    if ROUTE_ANCHOR not in text:
        raise SystemExit("Expected RouteTableDef anchor was not found; refusing speculative edit.")

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = SERVER.with_name(f"{SERVER.name}.pre-github-{stamp}.bak")
    backup.write_text(text, encoding="utf-8")

    updated = text.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_LINE, 1)
    updated = updated.replace(ROUTE_ANCHOR, ROUTE_ANCHOR + ROUTE_LINE, 1)

    SERVER.write_text(updated, encoding="utf-8")
    print(f"Wired governed GitHub routes into {SERVER}")
    print(f"Backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
