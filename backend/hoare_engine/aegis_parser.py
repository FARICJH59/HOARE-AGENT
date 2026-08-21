"""Parser for the initial AEGIS verification-oriented language."""

from __future__ import annotations

import re

from hoare_engine.aegis_ast import (
    AegisAssignment,
    AegisFact,
    AegisProgram,
    AegisReturn,
)


class AegisSyntaxError(Exception):
    """Raised when AEGIS source cannot be parsed."""


_HEADER_RE = re.compile(
    r"^\s*agent\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)\s*$"
)

_LET_RE = re.compile(
    r"^\s*let\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$"
)

_FACT_RE = re.compile(
    r"^\s*fact\s+(.+?)\s*$"
)

_RETURN_RE = re.compile(
    r"^\s*return\s+(.+?)\s*$"
)


_IDENTIFIER_RE = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)


def parse_aegis(source: str) -> AegisProgram:
    """Parse AEGIS source into an AEGIS AST."""

    lines = [
        line.strip()
        for line in source.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not lines:
        raise AegisSyntaxError("Empty AEGIS program")

    header = _HEADER_RE.match(lines[0])

    if not header:
        raise AegisSyntaxError(
            "Expected: agent <name>(<parameters>)"
        )

    name = header.group(1)

    parameters = [
        parameter.strip()
        for parameter in header.group(2).split(",")
        if parameter.strip()
    ]

    for parameter in parameters:
        if not _IDENTIFIER_RE.fullmatch(parameter):
            raise AegisSyntaxError(
                f"Invalid parameter name: {parameter}"
            )

    if lines[-1] != "end":
        raise AegisSyntaxError(
            "AEGIS agent must terminate with 'end'"
        )

    program = AegisProgram(
        name=name,
        parameters=parameters,
    )

    for line_number, line in enumerate(lines[1:-1], start=2):

        match = _LET_RE.match(line)

        if match:
            expression = match.group(2).strip()

            if not expression:
                raise AegisSyntaxError(
                    f"Line {line_number}: assignment requires an expression"
                )

            program.assignments.append(
                AegisAssignment(
                    target=match.group(1),
                    expression=expression,
                )
            )

            continue

        match = _FACT_RE.match(line)

        if match:
            expression = match.group(1).strip()

            if not expression:
                raise AegisSyntaxError(
                    f"Line {line_number}: fact requires an expression"
                )

            program.facts.append(
                AegisFact(
                    expression=expression,
                )
            )

            continue

        match = _RETURN_RE.match(line)

        if match:
            expression = match.group(1).strip()

            if not expression:
                raise AegisSyntaxError(
                    f"Line {line_number}: return requires an expression"
                )

            program.returns.append(
                AegisReturn(
                    expression=expression,
                )
            )

            continue

        raise AegisSyntaxError(
            f"Line {line_number}: unsupported AEGIS statement: {line}"
        )

    if not (
        program.assignments
        or program.facts
        or program.returns
    ):
        raise AegisSyntaxError(
            "AEGIS agent contains no executable or verification statements"
        )

    return program
