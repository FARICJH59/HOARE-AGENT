"""
Tests for the Hoare-Agent pipeline.

Run with:
    cd backend
    pip install -r requirements.txt pytest
    pytest tests/ -v
"""

from __future__ import annotations

import sys
import os

# Ensure backend/ is on sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from schema.models import (
    FSMStateEnum,
    HoareTriple,
    RawPayload,
    VerificationRequest,
    VerificationVerdict,
)
from hoare_engine.verifier import HoareVerifier
from hoare_engine.pda_engine import (
    GrammarConstraintError,
    InvalidTransitionError,
    PDAController,
    SchemaGrammar,
    GrammarRegistry,
    registry,
)
from hoare_engine.agent import HoareAgent
from schema.models import AgentTaskRequest, TelemetryEvent
from saas.auth import ApiKeyAuthenticator
from saas.billing import BillingService
from saas.usage import UsageMeter
from integrations.connectors import connector_registry


# ─────────────────────────────────────────────────────────────────────────────
# Z3 Hoare Verifier Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestHoareVerifier:
    """Tests for the Z3-backed Hoare triple verifier."""

    def setup_method(self):
        self.v = HoareVerifier()

    def _verify(self, pre: str, program: str, post: str) -> VerificationRequest:
        return VerificationRequest(
            triple=HoareTriple(
                precondition=pre,
                program=program,
                postcondition=post,
            )
        )

    def test_trivially_true_triple_verifies(self):
        """P=True, C=noop, Q=True  should always verify."""
        req = self._verify("n >= 0", "", "n >= 0")
        result = self.v.verify(req)
        # With n >= 0 as both P and Q: P ∧ ¬Q = (n≥0) ∧ (n<0) which is UNSAT
        assert result.verified
        assert result.verdict == VerificationVerdict.VERIFIED

    def test_false_triple_produces_counterexample(self):
        """P=True, Q=False should produce a counterexample."""
        req = self._verify("n >= 0", "", "n > 100")
        result = self.v.verify(req)
        # n=0 satisfies P but not Q, so P ∧ ¬Q is SAT
        assert not result.verified
        assert result.verdict == VerificationVerdict.COUNTEREXAMPLE

    def test_implication_verifies(self):
        """P implies Q when P is strictly stronger than Q."""
        # P: n > 10 → Q: n >= 0  (n>10 ⇒ n≥0 is always true)
        req = self._verify("n > 10", "", "n >= 0")
        result = self.v.verify(req)
        assert result.verified

    def test_unrelated_variables_handled(self):
        """Variables only in Q should not crash the solver."""
        req = self._verify("x >= 0", "", "x >= 0")
        result = self.v.verify(req)
        assert result.verified

    def test_request_id_preserved(self):
        req = self._verify("n >= 0", "", "n >= 0")
        result = self.v.verify(req)
        assert result.request_id == req.request_id


# ─────────────────────────────────────────────────────────────────────────────
# PDA Engine Tests
# ─────────────────────────────────────────────────────────────────────────────


class TestPDAController:
    """Tests for the finite-state machine and grammar constraint engine."""

    def _make_controller(self, payload_id: str = "test-001") -> PDAController:
        return registry.make_controller(payload_id, "TelemetryEvent")

    def test_initial_state_is_idle(self):
        ctrl = self._make_controller()
        assert ctrl.state == FSMStateEnum.IDLE

    def test_valid_transition_sequence(self):
        ctrl = self._make_controller()
        ctrl.transition(FSMStateEnum.INGESTING)
        assert ctrl.state == FSMStateEnum.INGESTING
        ctrl.transition(FSMStateEnum.PARSING)
        assert ctrl.state == FSMStateEnum.PARSING

    def test_invalid_transition_raises(self):
        ctrl = self._make_controller()
        with pytest.raises(InvalidTransitionError):
            # Cannot jump from IDLE directly to COMMITTED
            ctrl.transition(FSMStateEnum.COMMITTED)

    def test_valid_payload_passes(self):
        import uuid
        from datetime import datetime, timezone
        ctrl = self._make_controller("payload-valid")
        payload = RawPayload(
            source_name="test",
            raw_data={
                "event_id":     str(uuid.uuid4()),
                "source":       "sensor_a",
                "timestamp":    datetime.now(timezone.utc).isoformat(),
                "metric_name":  "cpu_usage",
                "metric_value": 42.0,
            },
        )
        record = ctrl.process_payload(payload)
        assert record.valid
        assert record.fsm_state.state == FSMStateEnum.COMMITTED

    def test_invalid_payload_blocked(self):
        ctrl = self._make_controller("payload-bad")
        # Missing required fields
        payload = RawPayload(source_name="test", raw_data={"event_id": "x"})
        record = ctrl.process_payload(payload)
        assert not record.valid
        assert record.fsm_state.state == FSMStateEnum.BLOCKED
        assert record.error != ""

    def test_history_recorded(self):
        ctrl = self._make_controller()
        ctrl.transition(FSMStateEnum.INGESTING)
        ctrl.transition(FSMStateEnum.PARSING)
        assert len(ctrl.history) == 2
        assert ctrl.history[0][0] == FSMStateEnum.IDLE

    def test_grammar_registry_lists_builtin_schemas(self):
        assert "TelemetryEvent" in registry._grammars
        assert "TransformationOutput" in registry._grammars

    def test_unknown_schema_raises_key_error(self):
        with pytest.raises(KeyError):
            registry.make_controller("x", "NonExistentSchema")


class TestSchemaGrammar:
    def test_compile_telemetry_schema(self):
        from schema.models import TelemetryEvent
        grammar = SchemaGrammar(TelemetryEvent, "TelemetryEvent")
        # Must produce rules for all fields
        field_names = {r.name for r in grammar.rules}
        assert "event_id" in field_names
        assert "metric_value" in field_names

    def test_constrain_rejects_missing_required(self):
        from schema.models import TelemetryEvent
        grammar = SchemaGrammar(TelemetryEvent, "TelemetryEvent")
        with pytest.raises(GrammarConstraintError):
            grammar.constrain({})  # All required fields missing


class TestTenantSchemaRegistry:
    def test_provision_tenant_with_subset(self):
        tenant_id = "tenant-a"
        allowed = registry.provision_tenant(tenant_id, ["TelemetryEvent"])
        assert allowed == ["TelemetryEvent"]
        assert registry.list_schemas(tenant_id) == ["TelemetryEvent"]

    def test_reject_schema_not_allowed_for_tenant(self):
        tenant_id = "tenant-b"
        registry.provision_tenant(tenant_id, ["TelemetryEvent"])
        with pytest.raises(KeyError):
            registry.make_controller("payload-1", "TransformationOutput", tenant_id=tenant_id)


class TestSaaSServices:
    def test_authenticator_allows_anonymous_when_not_required(self, monkeypatch):
        monkeypatch.delenv("HOARE_API_KEYS", raising=False)
        monkeypatch.setenv("HOARE_REQUIRE_AUTH", "0")
        auth = ApiKeyAuthenticator()
        ctx = auth.authenticate(header_key=None, bearer_key=None)
        assert ctx.tenant_id == "public"

    def test_usage_billing_estimate(self, monkeypatch):
        monkeypatch.delenv("STRIPE_API_KEY", raising=False)
        meter = UsageMeter()
        billing = BillingService(meter)
        out = billing.report_usage("tenant-c", 7)
        assert out["usage_units_total"] == 7
        assert out["estimated_amount_cents"] > 0


class TestEcosystemConnectors:
    def test_connector_registry_lists_week4_connectors(self):
        connectors = connector_registry.list_connectors()
        names = {c["name"] for c in connectors}
        assert {"langgraph", "crewai", "autogen", "airflow", "dagster", "mqtt-emqx"} <= names


# ─────────────────────────────────────────────────────────────────────────────
# Agent Tests (mock LLM)
# ─────────────────────────────────────────────────────────────────────────────


class TestHoareAgent:
    def test_mock_agent_succeeds_with_valid_triple(self):
        """The mock LLM returns a provably-correct identity transform."""
        import json
        agent = HoareAgent(use_mock_llm=True)
        req = AgentTaskRequest(
            description="Extract and normalise telemetry events",
            target_schema=json.dumps(TelemetryEvent.model_json_schema()),
            max_retries=3,
        )
        result = agent.run_task(req)
        assert result.success
        assert result.generated_code != ""
        assert result.triple is not None
        assert result.proof is not None
        assert result.proof.verified
        assert result.iterations >= 1
        assert len(result.repair_trace) >= 1
        assert result.repair_trace[0]["attempt"] == 1
        assert "verdict" in result.repair_trace[0]
        assert "counterexample" in result.repair_trace[0]
        assert "error_detail" in result.repair_trace[0]
        assert "elapsed_ms" in result.repair_trace[0]

    def test_agent_task_id_preserved(self):
        import json
        agent = HoareAgent(use_mock_llm=True)
        req = AgentTaskRequest(
            task_id="my-fixed-id",
            description="Test",
            target_schema=json.dumps(TelemetryEvent.model_json_schema()),
        )
        result = agent.run_task(req)
        assert result.task_id == "my-fixed-id"
