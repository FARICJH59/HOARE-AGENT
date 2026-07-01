# Week 4 Integration Guide — Tech Fusion Grid

This guide covers the Week 4 integration layer introduced in Hoare-Agent:

- Tech Fusion Grid dashboard module
- Proof log + repair loop visibility
- Schema registry and FSM viewer overlays
- Ecosystem connectors for orchestration and IoT stacks

## 1) Tech Fusion Grid UI module

The dashboard now includes a dedicated **Tech Fusion Grid** panel with:

- **Agent Repair Loop**: attempt-by-attempt verdict and counterexample trace
- **Proof Logs**: verification outcomes per attempt
- **Schema Registry**: tenant-visible schema list from `/schemas`
- **FSM Viewer**: latest finite-state transitions
- **Ecosystem Connectors**: integration readiness and validation controls

## 2) New backend integration APIs

### List all connectors

`GET /integrations/connectors`

Returns metadata and readiness for:

- `langgraph`
- `crewai`
- `autogen`
- `airflow`
- `dagster`
- `mqtt-emqx`

### Validate one connector

`GET /integrations/connectors/{name}/validate`

Re-evaluates required environment variables and returns:

- `ready`
- `readiness_score`
- `configured_env`
- `required_env`

## 3) Connector environment variables

| Connector | Required environment keys |
|---|---|
| LangGraph | `LANGGRAPH_API_URL` |
| CrewAI | `CREWAI_API_URL` |
| AutoGen | `AUTOGEN_ENDPOINT` |
| Airflow | `AIRFLOW_API_URL` |
| Dagster | `DAGSTER_API_URL` |
| MQTT/EMQX | `MQTT_BROKER_URL`, `EMQX_API_URL` |

## 4) Repair loop and proof trace payloads

`/agent/run` now returns per-attempt proof trace in `result.repair_trace`, including:

- `attempt`
- `verified`
- `verdict`
- `counterexample`
- `error_detail`
- `elapsed_ms`

This trace powers the Tech Fusion Grid cards for proof logs and repair loop visuals.
