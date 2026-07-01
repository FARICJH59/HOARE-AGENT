"""
Connector registry for external orchestration ecosystems.

Week 4 adds lightweight validation for:
  - LangGraph
  - CrewAI
  - AutoGen
  - Airflow
  - Dagster
  - IoT MQTT / EMQX
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List

READINESS_THRESHOLD = 0.5


@dataclass(frozen=True)
class ConnectorSpec:
    name: str
    category: str
    description: str
    env_keys: List[str]


class ConnectorRegistry:
    def __init__(self) -> None:
        self._specs: Dict[str, ConnectorSpec] = {
            "langgraph": ConnectorSpec(
                name="langgraph",
                category="agent-orchestration",
                description="LangGraph workflow bridge for graph-structured agent plans.",
                env_keys=["LANGGRAPH_API_URL"],
            ),
            "crewai": ConnectorSpec(
                name="crewai",
                category="agent-orchestration",
                description="CrewAI connector for multi-agent role/task delegation.",
                env_keys=["CREWAI_API_URL"],
            ),
            "autogen": ConnectorSpec(
                name="autogen",
                category="agent-orchestration",
                description="AutoGen connector for conversational agent collaboration loops.",
                env_keys=["AUTOGEN_ENDPOINT"],
            ),
            "airflow": ConnectorSpec(
                name="airflow",
                category="pipeline-orchestration",
                description="Airflow DAG execution/status connector.",
                env_keys=["AIRFLOW_API_URL"],
            ),
            "dagster": ConnectorSpec(
                name="dagster",
                category="pipeline-orchestration",
                description="Dagster asset/job orchestration connector.",
                env_keys=["DAGSTER_API_URL"],
            ),
            "mqtt-emqx": ConnectorSpec(
                name="mqtt-emqx",
                category="iot-telemetry",
                description="MQTT/EMQX telemetry ingress connector.",
                env_keys=["MQTT_BROKER_URL", "EMQX_API_URL"],
            ),
        }

    def list_connectors(self) -> List[dict]:
        return [self.validate(name) for name in sorted(self._specs)]

    def validate(self, connector_name: str) -> dict:
        spec = self._specs.get(connector_name)
        if spec is None:
            raise KeyError(f"Unknown connector '{connector_name}'")

        configured = [key for key in spec.env_keys if os.getenv(key)]
        configured_count = len(configured)
        readiness_ratio = (configured_count / len(spec.env_keys)) if spec.env_keys else 1.0
        return {
            "name": spec.name,
            "category": spec.category,
            "description": spec.description,
            "required_env": spec.env_keys,
            "configured_env": configured,
            "ready": readiness_ratio >= READINESS_THRESHOLD,
            "readiness_score": round(readiness_ratio, 2),
        }


connector_registry = ConnectorRegistry()
