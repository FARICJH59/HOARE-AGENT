# Hoare-Agent — Self-Verifying Code Pipeline

> **"Don't guess what code should look like.  Prove it."**

Hoare-Agent is a formally-verified, self-healing agentic data pipeline that
couples a sub-billion-parameter LLM with a Z3 SMT theorem prover and a
Pushdown Automaton (PDA) grammar engine.  Unlike traditional AI coding
assistants that rely on probabilistic token prediction, every piece of
agent-generated code must pass a mathematical proof before it can reach the
data warehouse.

---

## Architecture

```
                   [ AESIRGRID CORE DATA FABRIC ]
                                  │
                                  ▼
        [ Ingestion Stream / NVIDIA Triton Inference Server ]
                                  │
             ┌────────────────────┴────────────────────┐
             ▼                                         ▼
  [ Ultra-Fast Micro-Model ]                [ Hoare Verification Engine ]
     (Structural Parsing)                      (Constraint Checking via Z3)
             │                                         │
             └────────────────────┬────────────────────┘
                                  ▼
                  [ Deterministic Schema Commit ]
                       (Azure / BigQuery Fabric)
```

---

## Three Proprietary Engines

### 1. Constrained Grammar Engine (PDA Compiler)
Compiles Pydantic schemas into a Finite State Machine that enforces
structural conformance at the token-generation boundary.  The FSM blocks any
output that violates the target schema — eliminating hallucinations at the
data-ingestion layer.

### 2. Hoare Logic Prompting & Verification Engine (Z3)
A dual-pass pipeline:
- **Pass 1** — the LLM generates a transformation function *and* annotates it
  with pre-conditions, post-conditions, and loop invariants.
- **Pass 2** — the Z3 SMT prover checks the Hoare triple `{P} C {Q}`.
  If the proof fails a structured counterexample is fed back to the agent,
  which refactors the code until it is mathematically proven correct.

### 3. Visual Wireframe Dashboard
A React + ReactFlow web application that maps FSM state transitions in
real-time as a live node graph — replacing terminal logs with an animated
pipeline visualisation.

---

## Quick Start

### Option A — Docker Compose (recommended)

```bash
# Clone the repo
git clone https://github.com/FARICJH59/HOARE-AGENT.git
cd HOARE-AGENT

# Start backend + dashboard (uses mock LLM — no GPU required)
HOARE_USE_MOCK_LLM=1 docker compose up --build

# Open the dashboard
open http://localhost:3000
```

To include the real vLLM micro-model (requires NVIDIA GPU):

```bash
export HF_TOKEN=<your_huggingface_token>
docker compose --profile llm up --build
```

### Option B — PowerShell (Windows / WSL)

```powershell
# Mock LLM (no GPU)
.\scripts\bootstrap.ps1 -MockLLM

# Real vLLM container
.\scripts\bootstrap.ps1 -StartLLM -Model "Qwen/Qwen2.5-0.5B-Instruct"
```

### Option C — Manual

```bash
# Backend
cd backend
pip install -r requirements.txt
HOARE_USE_MOCK_LLM=1 python main.py

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Week 2 — Developer Experience (SDK · CLI · GitHub Action)

### Python SDK

```bash
pip install hoare-agent
```

```python
from hoare_agent import verify

result = verify(
    precondition="n >= 0",
    postcondition="n >= 0",
    program="def transform(data): return data",
)

if result:
    print(f"✓ Verified in {result.elapsed_ms} ms")
else:
    print(f"✗ {result}")   # COUNTEREXAMPLE / TIMEOUT / ERROR
```

Delegate to a running backend instead of the local Z3 solver:

```python
result = verify(
    precondition="n >= 0",
    postcondition="n >= 0",
    backend_url="http://localhost:8080",
)
```

See [`sdk/python/README.md`](sdk/python/README.md) for the full API reference.

---

### CLI (`hoare-agent`)

The Python SDK installs a command-line tool:

```bash
# Verify a Python file with inline annotations
hoare-agent verify mymodule.py

# Verify with explicit pre/post-conditions
hoare-agent verify --pre "n >= 0" --post "n >= 0" mymodule.py

# Verify a JSON triple file
hoare-agent verify triple.json

# Output JSON result (CI-friendly)
hoare-agent verify --json mymodule.py

# Delegate to a running backend
hoare-agent verify --backend http://localhost:8080 mymodule.py
```

#### Inline annotation format

Add `# @pre:` and `# @post:` comments anywhere in your Python file:

```python
# @pre:  n >= 0
# @post: result >= 0
# @inv:  i >= 0    # optional, repeatable
def transform(data: dict) -> dict:
    ...
```

#### JSON triple format

```json
{
  "precondition":    "n >= 0",
  "program":         "def transform(data): return data",
  "postcondition":   "n >= 0",
  "loop_invariants": []
}
```

| Exit code | Meaning |
|-----------|---------|
| `0` | Triple verified |
| `1` | Usage error (bad arguments, file not found, missing annotations) |
| `2` | Verification failed (counterexample or error) |

---

### Node.js SDK

```bash
npm install hoare-agent
```

```javascript
const { verify } = require('hoare-agent');

const result = await verify({
  precondition:  'n >= 0',
  postcondition: 'n >= 0',
  program:       'def transform(data): return data',
}, { backendUrl: 'http://localhost:8080' });

if (result.verified) {
  console.log(`✓ Verified in ${result.elapsed_ms} ms`);
} else {
  console.error(`✗ ${result.verdict}: ${result.counterexample || result.error_detail}`);
}
```

See [`sdk/node/README.md`](sdk/node/README.md) for the full API reference.

---

### GitHub Action — CI/CD Proof Gate

Use `FARICJH59/HOARE-AGENT/action@v1` as a required check in any workflow:

```yaml
# .github/workflows/proof-gate.yml
name: Proof Gate

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Verify a file with inline annotations
      - name: Hoare proof gate
        uses: FARICJH59/HOARE-AGENT/action@v1
        with:
          file: src/transform.py

      # Or verify with explicit conditions
      - name: Hoare proof gate (explicit)
        uses: FARICJH59/HOARE-AGENT/action@v1
        with:
          file:  src/transform.py
          pre:   "n >= 0"
          post:  "n >= 0"

      # Or delegate to a running backend
      - name: Hoare proof gate (backend)
        uses: FARICJH59/HOARE-AGENT/action@v1
        with:
          file:        src/transform.py
          backend_url: ${{ secrets.HOARE_BACKEND_URL }}
```

Outputs available after the step:

| Output | Description |
|--------|-------------|
| `verified`    | `'true'` if the triple was formally proved |
| `verdict`     | `VERIFIED` \| `COUNTEREXAMPLE` \| `TIMEOUT` \| `ERROR` |
| `elapsed_ms`  | Z3 solver time in milliseconds |
| `result_json` | Full `VerificationResult` as JSON |

See [`action/action.yml`](action/action.yml) for all available inputs.

---

## Week 3 — SaaS Productization

### 1) Cloud workers + autoscaling deployment

The repository now includes a cloud-worker deployment blueprint with autoscaling:

- `deploy/cloud-workers/cloudrun-service.yaml`

This profile is designed for stateless backend replicas behind a managed gateway.

### 2) API gateway authentication + usage metering

The backend HTTP service now supports API-key authentication and tenant-level metering.

Set these environment variables:

| Variable | Description |
|---|---|
| `HOARE_REQUIRE_AUTH` | `1` to enforce authentication on all protected API routes |
| `HOARE_API_KEYS` | JSON map of API keys to tenant metadata |
| `HOARE_USAGE_UNIT_PRICE_CENTS` | Usage-unit price for estimated billing totals |

Example `HOARE_API_KEYS`:

```json
{
  "dev-key-tenant-a": { "tenant_id": "tenant-a", "plan": "pro" },
  "dev-key-tenant-b": { "tenant_id": "tenant-b", "plan": "starter" }
}
```

### 3) Stripe billing for subscription + usage pricing

Set `STRIPE_API_KEY` to enable live Stripe Checkout session creation.

Without `STRIPE_API_KEY`, billing endpoints run in safe mock mode for local development.

### 4) Multi-tenant schema registry isolation

Schemas are now tenant-scoped through the registry API:

- `POST /tenants/provision`
- `GET /tenants/{tenant_id}/schemas`
- `GET /schemas` (returns schemas allowed for the authenticated tenant)

### 5) Structured JSON audit logging + dashboard visibility

Every request emits a structured audit JSON event. Dashboard sidebar now includes:

- API key entry for gateway auth
- Usage totals (`/usage/me`)
- Audit summary (`/audit/summary`)

### 6) SaaS onboarding quick flow

1. Provision API keys and tenants via environment variables / tenant API.
2. Configure frontend with tenant API key.
3. Create subscription checkout session (`POST /billing/checkout`).
4. Report usage units (`POST /billing/usage`) for metered pricing.
5. Monitor tenant activity via `/audit/events` and dashboard metrics.

---

## Week 4 — Integration + Enterprise Operations

### 1) Tech Fusion Grid dashboard module

The frontend now includes a **Tech Fusion Grid** side panel that surfaces:

- Proof logs from the Hoare verification lifecycle
- Schema registry visibility
- FSM transition viewer
- Agent repair loop attempt visualization
- Ecosystem connector readiness checks

### 2) Ecosystem connector support

New backend connector registry and validation APIs cover:

- LangGraph
- CrewAI
- AutoGen
- Airflow
- Dagster
- IoT MQTT / EMQX

### 3) Enterprise guides and playbooks

- Integration guide: [`docs/week4-integration-guide.md`](docs/week4-integration-guide.md)
- Enterprise playbooks: [`docs/enterprise-playbooks.md`](docs/enterprise-playbooks.md)

---

## Running Tests

```bash
# Backend tests
cd backend
pip install -r requirements.txt pytest
pytest tests/ -v

# Python SDK tests
cd sdk/python
pip install -e ".[dev]"
pytest tests/ -v

# Node.js SDK tests
cd sdk/node
node test/test.js
```

---

## Repository Layout

```
HOARE-AGENT/
├── proto/
│   └── hoare_agent.proto          # gRPC contract (3 services)
├── backend/
│   ├── main.py                    # Entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── hoare_engine/
│   │   ├── verifier.py            # Z3 Hoare triple verifier
│   │   ├── pda_engine.py          # PDA / grammar constraint engine
│   │   └── agent.py               # Two-pass self-verifying agent loop
│   ├── grpc_server/
│   │   └── server.py              # gRPC + HTTP/REST server
│   ├── schema/
│   │   └── models.py              # Pydantic data models
│   └── tests/
│       └── test_pipeline.py       # pytest test suite
├── sdk/
│   ├── python/                    # pip install hoare-agent
│   │   ├── pyproject.toml
│   │   ├── hoare_agent/           # SDK package + CLI entry point
│   │   └── tests/                 # SDK unit tests
│   └── node/                      # npm install hoare-agent
│       ├── package.json
│       ├── index.js               # verify() function
│       ├── index.d.ts             # TypeScript declarations
│       └── test/                  # Node.js SDK unit tests
├── action/
│   └── action.yml                 # GitHub Action (CI/CD proof gate)
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── store.js               # Zustand state store
│   │   └── components/
│   │       ├── NodeMap.jsx        # React Flow node graph
│   │       └── StatePanel.jsx     # Live event log + agent runner
│   ├── Dockerfile
│   └── package.json
├── scripts/
│   └── bootstrap.ps1              # PowerShell local-dev launcher
└── docker-compose.yml             # Full stack (backend + frontend + vLLM)
```

---

## Environment Variables

| Variable              | Default                          | Description                                      |
|-----------------------|----------------------------------|--------------------------------------------------|
| `HOARE_HTTP_PORT`     | `8080`                           | Backend REST server port                         |
| `HOARE_GRPC_PORT`     | `50051`                          | Backend gRPC server port                         |
| `HOARE_LLM_BASE_URL`  | `http://localhost:8000/v1`       | OpenAI-compatible LLM endpoint                   |
| `HOARE_LLM_MODEL`     | `Qwen/Qwen2.5-0.5B-Instruct`    | Model ID                                         |
| `HOARE_LLM_API_KEY`   | `EMPTY`                          | API key (use `EMPTY` for local vLLM)             |
| `HOARE_USE_MOCK_LLM`  | `0`                              | Set to `1` to use the built-in deterministic mock|

---

## gRPC Services

Defined in [`proto/hoare_agent.proto`](proto/hoare_agent.proto):

| Service                  | Methods                                       |
|--------------------------|-----------------------------------------------|
| `SchemaParserService`    | `ParsePayload`, `ParseStream`, `TransitionFSM`|
| `HoareVerifierService`   | `Verify`                                      |
| `HoareAgentService`      | `RunTask`, `WatchFSM`                         |

Generate stubs:

```bash
python -m grpc_tools.protoc \
    -I proto \
    --python_out=backend/grpc_server \
    --grpc_python_out=backend/grpc_server \
    proto/hoare_agent.proto
```

---

## REST API (HTTP fallback)

| Method | Path           | Body / Response                              |
|--------|----------------|----------------------------------------------|
| GET    | `/health`      | `{ "status": "ok", "timestamp": … }`         |
| GET    | `/schemas`     | `["TelemetryEvent", "TransformationOutput"]` |
| POST   | `/parse`       | `RawPayload` → `ParsedRecord`                |
| POST   | `/verify`      | `VerificationRequest` → `VerificationResult` |
| POST   | `/agent/run`   | `AgentTaskRequest` → `{ result, fsm_states }`|
| GET    | `/integrations/connectors` | Connector readiness inventory |
| GET    | `/integrations/connectors/{name}/validate` | Connector-specific readiness check |

---

## Technology Stack

| Layer              | Technology                                              |
|--------------------|---------------------------------------------------------|
| Inference engine   | vLLM / SGLang (OpenAI-compatible)                       |
| Micro-model        | Qwen2.5-0.5B-Instruct / Phi-4-mini                      |
| Formal verification| Z3 SMT solver (`z3-solver`)                             |
| Schema enforcement | Pydantic v2 + custom PDA grammar engine                 |
| Transport          | gRPC (HTTP/2) + aiohttp REST fallback                   |
| Data models        | Pydantic v2                                             |
| Frontend           | React 18, React Flow, Zustand, Vite                     |
| Containerisation   | Docker + Docker Compose                                 |
| Cloud targets      | Azure Data Factory / BigQuery (schema-commit layer)     |