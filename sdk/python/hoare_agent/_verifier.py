"""
Z3-backed Hoare triple verifier — standalone SDK edition.

Adapted from the backend hoare_engine.verifier module so that the SDK can
run offline without importing the full backend package.
"""

from __future__ import annotations

import ast
import re
import time
from typing import Dict, List, Optional

from hoare_agent._models import HoareTriple, VerificationResult, VerificationVerdict

try:
    import z3  # type: ignore
    _Z3_AVAILABLE = True
except ImportError:
    _Z3_AVAILABLE = False


_IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")

_KEYWORDS = frozenset({
    "and", "or", "not", "True", "False", "None",
    "if", "else", "in", "is", "lambda",
    "And", "Or", "Not", "Int", "Real", "Bool",
})


def _extract_identifiers(expr: str) -> List[str]:
    return list({m for m in _IDENT_RE.findall(expr) if m not in _KEYWORDS})


class _Z3Builder(ast.NodeVisitor):
    def __init__(self, env: Dict[str, "z3.ExprRef"]) -> None:
        self._env = env

    def build(self, expr_str: str) -> "z3.BoolRef":
        try:
            tree = ast.parse(expr_str, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Syntax error in expression {expr_str!r}: {exc}") from exc
        return self.visit(tree.body)

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
        if isinstance(op, ast.Eq):    return left == right
        if isinstance(op, ast.NotEq): return left != right
        if isinstance(op, ast.Lt):    return left < right
        if isinstance(op, ast.LtE):   return left <= right
        if isinstance(op, ast.Gt):    return left > right
        if isinstance(op, ast.GtE):   return left >= right
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
    return _Z3Builder(env).build(expr)


def _build_smt2_declarations(all_ids: List[str]) -> str:
    return "\n".join(f"(declare-const {name} Int)" for name in all_ids)


def run_z3(triple: HoareTriple, timeout_ms: int = 5_000) -> VerificationResult:
    """Run Z3 on the given Hoare triple and return a VerificationResult."""
    if not _Z3_AVAILABLE:
        return VerificationResult(
            verified=False,
            verdict=VerificationVerdict.ERROR,
            error_detail="z3-solver is not installed.  Run: pip install z3-solver",
        )

    t0 = time.monotonic()
    solver = z3.Solver()
    solver.set("timeout", timeout_ms)

    pre  = triple.precondition
    post = triple.postcondition

    all_ids = list(set(_extract_identifiers(pre) + _extract_identifiers(post)))
    env: Dict[str, z3.ExprRef] = {name: z3.Int(name) for name in all_ids}
    decls_smt2 = _build_smt2_declarations(all_ids)

    try:
        # Encode pre-condition
        if pre.lstrip().startswith("("):
            for c in z3.parse_smt2_string(f"{decls_smt2}\n(assert {pre})", decls={}):
                solver.add(c)
        else:
            solver.add(_python_expr_to_z3(pre, env))

        # Add loop invariants
        for inv in triple.loop_invariants:
            if inv.lstrip().startswith("("):
                for c in z3.parse_smt2_string(f"{decls_smt2}\n(assert {inv})", decls={}):
                    solver.add(c)
            else:
                solver.add(_python_expr_to_z3(inv, env))

        # Encode negation of post-condition
        if post.lstrip().startswith("("):
            for c in z3.parse_smt2_string(
                f"{decls_smt2}\n(assert (not {post}))", decls={}
            ):
                solver.add(c)
        else:
            solver.add(z3.Not(_python_expr_to_z3(post, env)))

        result_str = str(solver.check())
    except (ValueError, z3.Z3Exception) as exc:
        elapsed = int((time.monotonic() - t0) * 1000)
        return VerificationResult(
            verified=False,
            verdict=VerificationVerdict.ERROR,
            error_detail=str(exc),
            elapsed_ms=elapsed,
        )

    elapsed = int((time.monotonic() - t0) * 1000)

    if result_str == "unsat":
        return VerificationResult(
            verified=True,
            verdict=VerificationVerdict.VERIFIED,
            elapsed_ms=elapsed,
        )
    elif result_str == "sat":
        model = solver.model()
        ce = "; ".join(f"{d.name()} = {model[d]}" for d in model.decls())
        return VerificationResult(
            verified=False,
            verdict=VerificationVerdict.COUNTEREXAMPLE,
            counterexample=ce,
            elapsed_ms=elapsed,
        )
    else:
        return VerificationResult(
            verified=False,
            verdict=VerificationVerdict.TIMEOUT,
            error_detail="Z3 solver returned 'unknown' (timeout or incompleteness)",
            elapsed_ms=elapsed,
        )
