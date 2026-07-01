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

## Running Tests

```bash
cd backend
pip install -r requirements.txt pytest
pytest tests/ -v
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