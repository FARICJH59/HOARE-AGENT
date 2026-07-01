"""
Pydantic data models shared across the Hoare-Agent pipeline.

These models act as the ground-truth schema definitions that are compiled
into PDA grammar constraints and used for structured LLM extraction.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# FSM State
# ---------------------------------------------------------------------------

class FSMStateEnum(str, Enum):
    IDLE       = "IDLE"
    INGESTING  = "INGESTING"
    PARSING    = "PARSING"
    VALIDATING = "VALIDATING"
    VERIFYING  = "VERIFYING"
    COMMITTING = "COMMITTING"
    COMMITTED  = "COMMITTED"
    BLOCKED    = "BLOCKED"
    ERROR      = "ERROR"


class FSMState(BaseModel):
    state:      FSMStateEnum
    payload_id: str
    detail:     str = ""
    timestamp:  datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Ingestion / Parsing
# ---------------------------------------------------------------------------

class RawPayload(BaseModel):
    payload_id:  str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_name: str
    raw_data:    Dict[str, Any]
    metadata:    Dict[str, str] = Field(default_factory=dict)


class ParsedRecord(BaseModel):
    payload_id:  str
    schema_name: str
    structured:  Dict[str, Any]
    fsm_state:   FSMState
    valid:       bool
    error:       str = ""


# ---------------------------------------------------------------------------
# Hoare Logic
# ---------------------------------------------------------------------------

class HoareTriple(BaseModel):
    """Represents a Hoare triple  {P} C {Q}."""

    precondition:   str = Field(..., description="Pre-condition P (SMT-LIB2 or Python boolean expression)")
    program:        str = Field(..., description="Transformation program C (Python / SQL)")
    postcondition:  str = Field(..., description="Post-condition Q (SMT-LIB2 or Python boolean expression)")
    loop_invariants: List[str] = Field(default_factory=list)

    @field_validator("precondition", "postcondition", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class VerificationRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    triple:     HoareTriple
    timeout_ms: int = 5_000


class VerificationVerdict(str, Enum):
    VERIFIED        = "VERIFIED"
    COUNTEREXAMPLE  = "COUNTEREXAMPLE"
    TIMEOUT         = "TIMEOUT"
    ERROR           = "ERROR"


class VerificationResult(BaseModel):
    request_id:      str
    verified:        bool
    verdict:         VerificationVerdict
    counterexample:  str = ""
    error_detail:    str = ""
    elapsed_ms:      int = 0


# ---------------------------------------------------------------------------
# Agent Task
# ---------------------------------------------------------------------------

class AgentTaskRequest(BaseModel):
    task_id:       str = Field(default_factory=lambda: str(uuid.uuid4()))
    description:   str
    target_schema: str = Field(..., description="JSON-serialised target schema")
    max_retries:   int = Field(default=3, ge=1, le=10)


class AgentTaskResult(BaseModel):
    task_id:        str
    generated_code: str
    triple:         Optional[HoareTriple] = None
    proof:          Optional[VerificationResult] = None
    repair_trace:   List[Dict[str, Any]] = Field(default_factory=list)
    iterations:     int = 0
    success:        bool = False
    failure_reason: str = ""


# ---------------------------------------------------------------------------
# Structured extraction targets (used by the constrained grammar engine)
# ---------------------------------------------------------------------------

class TelemetryEvent(BaseModel):
    """Canonical schema for AesirGrid telemetry events."""

    event_id:     str
    source:       str
    timestamp:    datetime
    metric_name:  str
    metric_value: float
    tags:         Dict[str, str] = Field(default_factory=dict)

    @field_validator("metric_value")
    @classmethod
    def finite_value(cls, v: float) -> float:
        import math
        if not math.isfinite(v):
            raise ValueError("metric_value must be a finite number")
        return v


class TransformationOutput(BaseModel):
    """Validated output of an agent-generated data transformation."""

    output_id:      str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_payload: str
    schema_name:    str
    rows:           List[Dict[str, Any]]
    row_count:      int = Field(ge=0, description="Number of rows in the output")
    verified:       bool = False

    @field_validator("row_count", mode="before")
    @classmethod
    def validate_row_count(cls, v: int) -> int:
        if int(v) < 0:
            raise ValueError("row_count must be a non-negative integer")
        return int(v)
