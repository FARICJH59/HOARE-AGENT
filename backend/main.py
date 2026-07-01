"""
Hoare-Agent — Backend Entry Point
==================================
Run with:

    cd backend
    python main.py

Or via Docker Compose (see docker-compose.yml in the repo root).
"""

from __future__ import annotations

import asyncio
import sys
import os

# Ensure backend/ is on the path regardless of how the script is launched
sys.path.insert(0, os.path.dirname(__file__))

from grpc_server.server import main

if __name__ == "__main__":
    asyncio.run(main())
