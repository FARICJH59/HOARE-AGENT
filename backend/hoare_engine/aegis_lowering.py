"""Lower AEGIS AST into the language-neutral Verification IR."""

from __future__ import annotations

import re

from hoare_engine.aegis_ast import AegisProgram
from hoare_engine.verification_ir import VerificationProgram


class AegisLoweringError(Exception):
    """Raised when AEGIS cannot be represented in Verification IR."""


def _normalize_expression(expression: str) -> str:
    """Normalize AEGIS expressions into the verifier's expression subset."""

    expression = expression.strip()

    # AEGIS collection terminology.
    expression = re.sub(
        r"\blength\s*\(",
        "len(",
        expression,
    )

    # Boolean literals.
    expression = re.sub(
        r"\btrue\b",
        "True",
        expression,
        flags=re.IGNORECASE,
    )

    expression = re.sub(
        r"\bfalse\b",
        "False",
        expression,
        flags=re.IGNORECASE,
    )

    # Logical operators.
    expression = re.sub(
        r"\band\b",
        "and",
        expression,
        flags=re.IGNORECASE,
    )

    expression = re.sub(
        r"\bor\b",
        "or",
        expression,
        flags=re.IGNORECASE,
    )

    expression = re.sub(
        r"\bnot\b",
        "not",
        expression,
        flags=re.IGNORECASE,
    )

    return expression


def lower_aegis(
    program: AegisProgram,
) -> VerificationProgram:
    """Lower an AEGIS AST into Verification IR."""

    ir = VerificationProgram(
        source_language="aegis",
    )

    for assignment in program.assignments:
        expression = _normalize_expression(
            assignment.expression
        )

        ir.add_assignment(
            assignment.target,
            expression,
        )

        # length(...) is abstracted as a non-negative scalar.
        # Do not add the fact here if it is already explicitly
        # declared by the AEGIS program.
        if expression.startswith("len("):
            fact = f"{assignment.target} >= 0"

            if fact not in ir.facts:
                ir.add_fact(fact)

    for fact in program.facts:
        normalized = _normalize_expression(
            fact.expression
        )

        if normalized not in ir.facts:
            ir.add_fact(normalized)

    for return_statement in program.returns:
        ir.add_return(
            _normalize_expression(
                return_statement.expression
            )
        )

    if not (
        ir.assignments
        or ir.facts
        or ir.returns
    ):
        raise AegisLoweringError(
            "AEGIS program produced empty Verification IR"
        )

    return ir
