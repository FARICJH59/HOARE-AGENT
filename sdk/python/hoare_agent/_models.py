"""
Lightweight Pydantic models for the hoare-agent SDK.

These are self-contained and do not import from the backend package.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class VerificationVerdict(str, Enum):
    VERIFIED       = "VERIFIED"
    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    TIMEOUT        = "TIMEOUT"
    ERROR          = "ERROR"


class HoareTriple(BaseModel):
    """Represents a Hoare triple  {P} C {Q}."""

    precondition:    str = Field(..., description="Pre-condition P")
    program:         str = Field(default="", description="Transformation program C")
    postcondition:   str = Field(..., description="Post-condition Q")
    loop_invariants: List[str] = Field(default_factory=list)


class VerificationResult(BaseModel):
    verified:       bool
    verdict:        VerificationVerdict
    counterexample: str = ""
    error_detail:   str = ""
    elapsed_ms:     int = 0

    def __bool__(self) -> bool:
        return self.verified

    def __str__(self) -> str:
        if self.verified:
            return f"✓ VERIFIED ({self.elapsed_ms} ms)"
        if self.verdict == VerificationVerdict.COUNTEREXAMPLE:
            return f"✗ COUNTEREXAMPLE — {self.counterexample}"
        if self.verdict == VerificationVerdict.TIMEOUT:
            return "✗ TIMEOUT — Z3 solver timed out"
        return f"✗ ERROR — {self.error_detail}"
