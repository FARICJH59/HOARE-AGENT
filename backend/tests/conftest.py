"""Phase 31.1 test-runtime fixtures.

The gRPC E2E suite requires the local Hoare-Agent server on 127.0.0.1:50051.
This fixture makes that dependency autonomous: reuse an already-running server,
or start an isolated local server for the test session and terminate only the
process started by this fixture.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOST = os.getenv("HOARE_GRPC_TEST_HOST", "127.0.0.1")
PORT = int(os.getenv("HOARE_GRPC_TEST_PORT", "50051"))
READY_TIMEOUT = float(os.getenv("HOARE_GRPC_READY_TIMEOUT", "15"))


def _ready() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.25)
        return sock.connect_ex((HOST, PORT)) == 0


def _wait_ready(timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _ready():
            return True
        time.sleep(0.1)
    return _ready()


@pytest.fixture(scope="session", autouse=True)
def hoare_grpc_test_runtime():
    """Ensure the gRPC E2E dependency is ready for the test session."""
    if _ready():
        yield
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{ROOT / 'backend'}{os.pathsep}{env.get('PYTHONPATH', '')}".rstrip(os.pathsep)

    process = subprocess.Popen(
        [sys.executable, "-m", "grpc_server.server"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )

    try:
        if not _wait_ready(READY_TIMEOUT):
            output = ""
            if process.stdout is not None:
                try:
                    output = process.stdout.read(4000)
                except Exception:
                    pass
            raise RuntimeError(
                f"HOARE gRPC test server did not become ready on {HOST}:{PORT}. "
                f"Process exit={process.poll()}\n{output}"
            )
        yield
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
