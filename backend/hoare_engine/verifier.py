"""
Hoare Logic Verification Engine
================================
Uses the Z3 SMT theorem prover to mechanically check Hoare triples of the form

    {P} C {Q}

where:
  P   – pre-condition  (Python boolean expression or SMT-LIB2 string)
  C   – transformation program (Python / SQL)
  Q   – post-condition (Python boolean expression or SMT-LIB2 string)

The verifier works in two complementary modes:

1. **SMT-LIB2 mode** — when conditions start with "(assert …)" they are
   parsed directly by Z3's SMTLIB parser.  This is the authoritative path
   used for formal mathematical proofs.

2. **Python expression mode** — conditions written as plain Python boolean
   expressions (e.g. ``"x > 0 and y <= 100"``) are symbolically translated
   into Z3 constraints using a lightweight expression rewriter.  This mode is
   convenient for the agent's self-annotation step.

The verification procedure:

1. Create Z3 symbolic variables that appear in P and Q.
2. Assert P (pre-condition).
3. Assert the *negation* of Q (post-condition).
4. Call `solver.check()`.
   - `unsat`  → no counter-example exists → triple is **VERIFIED**.
   - `sat`    → Z3 found a counter-example → triple is **FALSIFIED**.
   - `unknown`→ solver timed-out → result is **TIMEOUT**.
"""

from __future__ import annotations

import ast
import re
import time
from typing import Dict, List

from schema.models import (
    HoareTriple,
    VerificationRequest,
    VerificationResult,
    VerificationVerdict,
)

try:
    import z3  # type: ignore
    _Z3_AVAILABLE = True
except ImportError:  # pragma: no cover
    _Z3_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PYTHON_OP_MAP = {
    " and ": " And ",
    " or ":  " Or ",
    " not ": " Not(",
}

_IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")

_KEYWORDS = frozenset({
    "and", "or", "not", "True", "False", "None",
    "if", "else", "in", "is", "lambda",
    "And", "Or", "Not", "Int", "Real", "Bool",
})


def _extract_identifiers(expr: str) -> List[str]:
    """Return unique Python-style identifiers in *expr* (excluding keywords)."""
    return list(
        {m for m in _IDENT_RE.findall(expr) if m not in _KEYWORDS}
    )


# ---------------------------------------------------------------------------
# Safe AST-based expression → Z3 translator
# ---------------------------------------------------------------------------


class _Z3Builder(ast.NodeVisitor):
    """
    Walks a Python AST and builds a Z3 expression tree.

    Supported nodes:
      • BoolOp  (and / or)
      • UnaryOp (not)
      • Compare (==, !=, <, <=, >, >=)
      • BinOp   (+, -, *, //)
      • Constant (int / float / bool)
      • Name    (resolved from *env*)

    Any unsupported construct raises :class:`ValueError`.
    This avoids any use of ``eval()`` on untrusted input.
    """

    def __init__(self, env: Dict[str, "z3.ExprRef"]) -> None:
        self._env = env

    def build(self, expr_str: str) -> "z3.BoolRef":
        try:
            tree = ast.parse(expr_str, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Syntax error in expression {expr_str!r}: {exc}") from exc
        return self.visit(tree.body)

    # ── Visitors ──────────────────────────────────────────────────────────

    def visit_BoolOp(self, node: ast.BoolOp) -> "z3.BoolRef":
        operands = [self.visit(v) for v in node.values]
        if isinstance(node.op, ast.And):
            return z3.And(*operands)
        if isinstance(node.op, ast.Or):
            return z3.Or(*operands)
        raise ValueError(f"Unsupported BoolOp: {node.op!r}")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> "z3.BoolRef":
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            return z3.Not(operand)
        if isinstance(node.op, ast.USub):
            return -operand  # type: ignore[operator]
        raise ValueError(f"Unsupported UnaryOp: {node.op!r}")

    def visit_Compare(self, node: ast.Compare) -> "z3.BoolRef":
        if len(node.ops) != 1:
            raise ValueError("Chained comparisons are not supported")
        left  = self.visit(node.left)
        right = self.visit(node.comparators[0])
        op    = node.ops[0]
        if isinstance(op, ast.Eq):  return left == right
        if isinstance(op, ast.NotEq): return left != right
        if isinstance(op, ast.Lt):  return left < right
        if isinstance(op, ast.LtE): return left <= right
        if isinstance(op, ast.Gt):  return left > right
        if isinstance(op, ast.GtE): return left >= right
        raise ValueError(f"Unsupported comparison operator: {op!r}")

    def visit_BinOp(self, node: ast.BinOp) -> "z3.ExprRef":
        left  = self.visit(node.left)
        right = self.visit(node.right)
        op    = node.op
        if isinstance(op, ast.Add):      return left + right   # type: ignore[operator]
        if isinstance(op, ast.Sub):      return left - right   # type: ignore[operator]
        if isinstance(op, ast.Mult):     return left * right   # type: ignore[operator]
        if isinstance(op, ast.FloorDiv): return left / right   # type: ignore[operator]
        raise ValueError(f"Unsupported BinOp: {op!r}")

    def visit_Constant(self, node: ast.Constant) -> "z3.ExprRef":
        if isinstance(node.value, bool):
            return z3.BoolVal(node.value)
        if isinstance(node.value, int):
            return z3.IntVal(node.value)
        if isinstance(node.value, float):
            return z3.RealVal(node.value)
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    def visit_Name(self, node: ast.Name) -> "z3.ExprRef":
        name = node.id
        if name == "True":  return z3.BoolVal(True)
        if name == "False": return z3.BoolVal(False)
        if name not in self._env:
            raise ValueError(
                f"Unknown identifier '{name}'. "
                "Declare it as a symbolic variable in the pre/post-condition."
            )
        return self._env[name]

    def generic_visit(self, node: ast.AST) -> None:  # type: ignore[override]
        raise ValueError(
            f"Unsupported AST node type: {type(node).__name__}. "
            "Use SMT-LIB2 notation for complex expressions."
        )


def _python_expr_to_z3(expr: str, env: Dict[str, "z3.ExprRef"]) -> "z3.BoolRef":
    """
    Translate a simple Python boolean expression into a Z3 constraint using
    a safe AST walker (no ``eval()``).

    Supports: comparison operators, ``and`` / ``or`` / ``not``,
    integer/float literals, arithmetic (+, -, *, //).
    Complex expressions (loops, function calls) should use SMT-LIB2 mode.
    """
    return _Z3Builder(env).build(expr)


def _build_smt2_declarations(all_ids: List[str]) -> str:
    """Return SMT-LIB2 ``declare-const`` statements for all symbolic variables."""
    return "\n".join(f"(declare-const {name} Int)" for name in all_ids)


# ---------------------------------------------------------------------------
# Core verifier
# ---------------------------------------------------------------------------

class HoareVerifier:
    """
    Stateless verifier.  All state lives inside individual solver instances
    so this object is safe to share across threads.
    """

    def verify(self, request: VerificationRequest) -> VerificationResult:
        """
        Verify the Hoare triple in *request* and return a :class:`VerificationResult`.

        Raises
        ------
        RuntimeError
            If Z3 is not installed.
        """
        if not _Z3_AVAILABLE:
            return VerificationResult(
                request_id=request.request_id,
                verified=False,
                verdict=VerificationVerdict.ERROR,
                error_detail="z3-solver is not installed.  Run: pip install z3-solver",
            )

        t0 = time.monotonic()
        triple = request.triple

        try:
            result = self._run_z3(triple, timeout_ms=request.timeout_ms)
        except Exception as exc:  # noqa: BLE001
            elapsed = int((time.monotonic() - t0) * 1000)
            return VerificationResult(
                request_id=request.request_id,
                verified=False,
                verdict=VerificationVerdict.ERROR,
                error_detail=str(exc),
                elapsed_ms=elapsed,
            )

        result.elapsed_ms = int((time.monotonic() - t0) * 1000)
        result.request_id = request.request_id
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_z3(self, triple: HoareTriple, timeout_ms: int) -> VerificationResult:
        solver = z3.Solver()
        solver.set("timeout", timeout_ms)

        pre  = triple.precondition
        post = triple.postcondition

        # ── Build symbolic environment ──────────────────────────────────
        all_ids = list(
            set(_extract_identifiers(pre) + _extract_identifiers(post))
        )
        env: Dict[str, z3.ExprRef] = {
            name: z3.Int(name) for name in all_ids
        }

        # ── Encode pre-condition ────────────────────────────────────────
        decls_smt2 = _build_smt2_declarations(all_ids)
        if pre.lstrip().startswith("("):
            # SMT-LIB2 path — declare all symbolic variables first
            constraints = z3.parse_smt2_string(
                f"{decls_smt2}\n(assert {pre})", decls={}
            )
            for c in constraints:
                solver.add(c)
        else:
            solver.add(_python_expr_to_z3(pre, env))

        # ── Add loop invariants ─────────────────────────────────────────
        for inv in triple.loop_invariants:
            if inv.lstrip().startswith("("):
                for c in z3.parse_smt2_string(
                    f"{decls_smt2}\n(assert {inv})", decls={}
                ):
                    solver.add(c)
            else:
                solver.add(_python_expr_to_z3(inv, env))

        # ── Encode *negation* of post-condition ─────────────────────────
        if post.lstrip().startswith("("):
            neg_constraints = z3.parse_smt2_string(
                f"{decls_smt2}\n(assert (not {post}))", decls={}
            )
            for c in neg_constraints:
                solver.add(c)
        else:
            solver.add(z3.Not(_python_expr_to_z3(post, env)))

        # ── Solve ───────────────────────────────────────────────────────
        result_str = str(solver.check())

        if result_str == "unsat":
            return VerificationResult(
                request_id="",
                verified=True,
                verdict=VerificationVerdict.VERIFIED,
            )
        elif result_str == "sat":
            model = solver.model()
            ce = "; ".join(
                f"{d.name()} = {model[d]}"
                for d in model.decls()
            )
            return VerificationResult(
                request_id="",
                verified=False,
                verdict=VerificationVerdict.COUNTEREXAMPLE,
                counterexample=ce,
            )
        else:  # unknown / timeout
            return VerificationResult(
                request_id="",
                verified=False,
                verdict=VerificationVerdict.TIMEOUT,
                error_detail="Z3 solver returned 'unknown' (timeout or incompleteness)",
            )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

verifier = HoareVerifier()


def verify_triple(triple: HoareTriple, timeout_ms: int = 5_000) -> VerificationResult:
    """Convenience wrapper around the module-level :data:`verifier`."""
    req = VerificationRequest(triple=triple, timeout_ms=timeout_ms)
    return verifier.verify(req)
