# HOARE Phase 31.1 — Autonomous Test Runtime & Remediation

Phase 31.1 converts the observed Termux test failure into an explicit autonomous runtime capability.

## Verified incident

The backend suite initially reported three `grpc.FutureTimeoutError` failures because the E2E client expected `127.0.0.1:50051` while no local gRPC service was listening.

Starting `python -m grpc_server.server` under `PYTHONPATH=backend` made the three gRPC E2E tests pass. The backend implementation therefore did not require a parser/FSM code change for this incident.

## Remediation

`backend/tests/conftest.py` now provides a session fixture that:

1. checks whether `127.0.0.1:50051` is already ready;
2. starts `python -m grpc_server.server` only when needed;
3. waits for TCP readiness;
4. runs the test session;
5. terminates only the process created by the fixture.

`scripts/phase31.1-termux-autonomous-remediation.sh` establishes `backend/` as the Python import root, runs the backend suite, validates the frontend without destructive dependency repair, records the final Git SHA, and pushes only remediation-owned files.

## Safety invariants

- no `git reset --hard`;
- no `git clean -fd`;
- no force push;
- no credential creation;
- no replacement of an existing working Node/Python installation;
- no staging of unrelated user changes;
- production cloud services remain external capabilities.

## Next autonomous layer

The same failure-classification mechanism can later manage Redis, HTTP sidecars, MQTT test brokers, and other local test dependencies through explicit service adapters. Production deployment remains governed by the Phase 32 target-adapter framework.
