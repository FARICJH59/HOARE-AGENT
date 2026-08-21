"""Lower supported source programs into Verification IR."""

from __future__ import annotations

import ast

from hoare_engine.verification_ir import VerificationProgram


class LoweringError(Exception):
    """Raised when source cannot be represented safely in Verification IR."""


def lower_python(source: str) -> VerificationProgram:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise LoweringError(
            f"Invalid Python source: {exc}"
        ) from exc

    program = VerificationProgram(
        source_language="python",
        source=source,
    )

    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
    ]

    if not functions:
        raise LoweringError(
            "No supported Python function found"
        )

    if len(functions) != 1:
        raise LoweringError(
            "Only one Python function is supported"
        )

    _lower_function(functions[0], program)

    if not program.assignments and not program.returns:
        raise LoweringError(
            "No supported executable statements found"
        )

    return program


def _lower_function(
    function: ast.FunctionDef,
    program: VerificationProgram,
) -> None:
    for statement in function.body:

        # Ignore function docstrings.
        if isinstance(statement, ast.Expr):
            if (
                isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            ):
                continue

            raise LoweringError(
                "Unsupported expression statement: "
                f"{ast.dump(statement.value, include_attributes=False)}"
            )

        if isinstance(statement, ast.Assign):
            if len(statement.targets) != 1:
                raise LoweringError(
                    "Only single-target assignments are supported"
                )

            target = statement.targets[0]

            if not isinstance(target, ast.Name):
                raise LoweringError(
                    "Only simple variable assignments are supported"
                )

            expression = ast.unparse(statement.value)

            # Semantic abstraction for collection length.
            #
            # The Hoare verifier models scalar integer state. Therefore
            # len(data) is represented by the sound fact that its result
            # is non-negative rather than attempting to model Python
            # dictionary internals inside Z3.
            if (
                isinstance(statement.value, ast.Call)
                and isinstance(statement.value.func, ast.Name)
                and statement.value.func.id == "len"
            ):
                program.add_assignment(
                    target.id,
                    expression,
                )
                program.add_fact(
                    f"{target.id} >= 0"
                )
            else:
                program.add_assignment(
                    target.id,
                    expression,
                )

            continue

        if isinstance(statement, ast.Return):
            expression = (
                "None"
                if statement.value is None
                else ast.unparse(statement.value)
            )

            program.add_return(expression)
            continue

        if isinstance(statement, ast.Pass):
            continue

        raise LoweringError(
            "Unsupported Python statement: "
            f"{type(statement).__name__}"
        )
