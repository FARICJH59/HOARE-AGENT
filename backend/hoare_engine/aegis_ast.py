"""Minimal AEGIS source AST.

The AEGIS AST is intentionally separate from Python AST and from the
verifier-facing Verification IR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class AegisAssignment:
    target: str
    expression: str


@dataclass(frozen=True)
class AegisReturn:
    expression: str


@dataclass(frozen=True)
class AegisFact:
    expression: str


@dataclass
class AegisProgram:
    name: str
    parameters: List[str] = field(default_factory=list)
    assignments: List[AegisAssignment] = field(default_factory=list)
    returns: List[AegisReturn] = field(default_factory=list)
    facts: List[AegisFact] = field(default_factory=list)
