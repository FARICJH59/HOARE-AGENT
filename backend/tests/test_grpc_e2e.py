import uuid
import grpc

from grpc_server import hoare_agent_pb2
from grpc_server import hoare_agent_pb2_grpc


GRPC_TARGET = "127.0.0.1:50051"


def _channel():
    channel = grpc.insecure_channel(GRPC_TARGET)
    grpc.channel_ready_future(channel).result(timeout=5)
    return channel


def test_transition_fsm_persists_state():
    channel = _channel()

    try:
        stub = hoare_agent_pb2_grpc.SchemaParserServiceStub(channel)

        payload_id = f"test-grpc-fsm-persistent-{uuid.uuid4()}"

        # IDLE -> INGESTING
        response = stub.TransitionFSM(
            hoare_agent_pb2.FSMTransitionRequest(
                payload_id=payload_id,
                target_state=hoare_agent_pb2.FSMStateEnum.INGESTING,
            ),
            timeout=10,
        )

        assert response.allowed is True
        assert (
            hoare_agent_pb2.FSMStateEnum.Name(response.new_state)
            == "INGESTING"
        )

        # The same controller must now be INGESTING.
        # Therefore the next legal transition is INGESTING -> PARSING.
        response = stub.TransitionFSM(
            hoare_agent_pb2.FSMTransitionRequest(
                payload_id=payload_id,
                target_state=hoare_agent_pb2.FSMStateEnum.PARSING,
            ),
            timeout=10,
        )

        assert response.allowed is True
        assert (
            hoare_agent_pb2.FSMStateEnum.Name(response.new_state)
            == "PARSING"
        )

    finally:
        channel.close()

def test_parse_payload_valid_reaches_committed():
    channel = _channel()

    try:
        stub = hoare_agent_pb2_grpc.SchemaParserServiceStub(channel)

        request = hoare_agent_pb2.RawPayload(
            payload_id="test-grpc-valid-committed",
            source_name="pytest",
            raw_data=(
                b'{"event_id":"evt-pytest-001",'
                b'"source":"pytest",'
                b'"timestamp":"2026-08-21T17:20:00Z",'
                b'"metric_name":"temperature",'
                b'"metric_value":72}'
            ),
            metadata={
                "schema": "TelemetryEvent",
                "tenant_id": "public",
            },
        )

        response = stub.ParsePayload(request, timeout=10)

        assert response.payload_id == "test-grpc-valid-committed"
        assert response.schema_name == "TelemetryEvent"
        assert response.valid is True
        assert (
            response.fsm_state.state
            == hoare_agent_pb2.FSMStateEnum.COMMITTED
        )
        assert (
            hoare_agent_pb2.FSMStateEnum.Name(response.fsm_state.state)
            == "COMMITTED"
        )
        assert response.error == ""

    finally:
        channel.close()


def test_parse_payload_missing_metric_value_is_blocked():
    channel = _channel()

    try:
        stub = hoare_agent_pb2_grpc.SchemaParserServiceStub(channel)

        request = hoare_agent_pb2.RawPayload(
            payload_id="test-grpc-invalid-metric-value",
            source_name="pytest",
            raw_data=(
                b'{"event_id":"evt-pytest-002",'
                b'"source":"pytest",'
                b'"timestamp":"2026-08-21T17:20:00Z",'
                b'"metric_name":"temperature"}'
            ),
            metadata={
                "schema": "TelemetryEvent",
                "tenant_id": "public",
            },
        )

        response = stub.ParsePayload(request, timeout=10)

        assert response.payload_id == "test-grpc-invalid-metric-value"
        assert response.schema_name == "TelemetryEvent"
        assert response.valid is False
        assert (
            response.fsm_state.state
            == hoare_agent_pb2.FSMStateEnum.BLOCKED
        )
        assert (
            hoare_agent_pb2.FSMStateEnum.Name(response.fsm_state.state)
            == "BLOCKED"
        )
        assert "metric_value" in response.error

    finally:
        channel.close()
