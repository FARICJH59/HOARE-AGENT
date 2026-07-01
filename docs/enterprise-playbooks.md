# Enterprise Playbooks

These playbooks provide repeatable operational patterns for production deployment of Hoare-Agent.

## 1) CI/CD proof gate playbook

1. Add `FARICJH59/HOARE-AGENT/action@v1` as a required check.
2. Verify high-risk transformations on every pull request.
3. Block merge when proof verdict is not `VERIFIED`.
4. Publish `result_json` artifacts for audit retention.
5. Track proof duration (`elapsed_ms`) for regression monitoring.

## 2) ML pipeline playbook

1. Use Airflow/Dagster connectors to trigger verification stages before materialization.
2. Require schema parse + Hoare verification for every model-generated transform.
3. Promote only `COMMITTED` outputs to downstream feature stores.
4. Route `BLOCKED`/`ERROR` outputs to quarantine with counterexample metadata.
5. Review repair loop traces to tune prompts and guardrails.

## 3) IoT telemetry validation playbook

1. Ingest telemetry via MQTT/EMQX into Hoare-Agent parsing endpoints.
2. Enforce `TelemetryEvent` grammar constraints at ingress.
3. Reject schema violations into `BLOCKED` state and alert operations.
4. Use FSM viewer timelines to correlate ingest failures with source devices.
5. Store audit summaries for compliance evidence and root-cause analysis.

## 4) SaaS tenant isolation playbook

1. Require API-key gateway auth (`HOARE_REQUIRE_AUTH=1`).
2. Provision tenant-specific schema allowlists via `/tenants/provision`.
3. Segment usage/billing and audit monitoring by tenant ID.
4. Prevent cross-tenant schema access by enforcing registry checks.
5. Apply tenant-scoped incident response using `/audit/events` and `/usage/me`.
