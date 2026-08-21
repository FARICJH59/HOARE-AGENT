"""Small semantic IR used between source programs and the Hoare verifier."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class IRAssignment:
    target: str
    expression: str


@dataclass(frozen=True)
class IRReturn:
    expression: str


@dataclass
class VerificationProgram:
    """Verifier-facing semantic representation of a program."""

    assignments: List[IRAssignment] = field(
        default_factory=list
    )

    returns: List[IRReturn] = field(
        default_factory=list
    )

    facts: List[str] = field(
        default_factory=list
    )

    # Source metadata is deliberately non-semantic.
    source_language: str = "unknown"
    source: str = ""

    def add_assignment(
        self,
        target: str,
        expression: str,
    ) -> None:
        self.assignments.append(
            IRAssignment(
                target=target,
                expression=expression,
            )
        )

    def add_return(
        self,
        expression: str,
    ) -> None:
        self.returns.append(
            IRReturn(
                expression=expression,
            )
        )

    def add_fact(
        self,
        expression: str,
    ) -> None:
        self.facts.append(expression)
