"""
Core verification logic for the hoare-agent Python SDK.

This module is intentionally self-contained so the SDK can be used without
having the full HOARE-AGENT backend running.  Z3 is the only required
dependency for local verification.
"""

from __future__ import annotations

import ast
import functools
import inspect
import re
import textwrap
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class HoareResult:
    """Result of a Hoare triple verification."""

    verified: bool
    """``True`` when the triple was formally proved."""

    verdict: str
    """One of ``"VERIFIED"``, ``"COUNTEREXAMPLE"``, ``"TIMEOUT"``, ``"ERROR"``."""

    counterexample: str = ""
    """Human-readable counter-example (only set when verdict is ``"COUNTEREXAMPLE"``)."""

    error_detail: str = ""
    """Error or timeout message (only set when verdict is ``"ERROR"`` or ``"TIMEOUT"``)."""

    elapsed_ms: int = 0
    """Wall-clock time the Z3 solver took, in milliseconds."""

    def __bool__(self) -> bool:  # noqa: D105
        return self.verified

    def __repr__(self) -> str:  # noqa: D105
        icon = "\u2713" if self.verified else "\u2717"
        parts = [f"{icon} {self.verdict}"]
        if self.counterexample:
            parts.append(f"counterexample={self.counterexample!r}")
        if self.error_detail:
            parts.append(f"error={self.error_detail!r}")
        parts.append(f"elapsed={self.elapsed_ms}ms")
        return f"HoareResult({', '.join(parts)})"

    def __str__(self) -> str:  # noqa: D105
        icon = "\u2713" if self.verified else "\u2717"
        suffix = f": {self.counterexample}" if self.counterexample else ""
        return f"{icon} {self.verdict}{suffix}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def verify(
    code: Union[Callable, str],
    *,
    pre: Optional[str] = None,
    post: Optional[str] = None,
    loop_invariants: Optional[List[str]] = None,
    timeout_ms: int = 5_000,
) -> HoareResult:
    """Verify the Hoare triple ``{pre} code {post}`` using Z3.

    Parameters
    ----------
    code:
        A Python callable or source-code string to verify.
    pre:
        Pre-condition as a Python boolean expression (e.g. ``"x >= 0"``).
        When *pre* is ``None`` the function's docstring is searched for a
        ``:pre: <expr>`` field.  Falls back to ``"True"``.
    post:
        Post-condition as a Python boolean expression (e.g. ``"result >= 0"``).
        When *post* is ``None`` the docstring is searched for ``:post: <expr>``.
        Falls back to ``"True"``.
    loop_invariants:
        Optional list of loop invariant expressions.
    timeout_ms:
        Z3 solver timeout in milliseconds (default 5 000).

    Returns
    -------
    HoareResult
        Verification outcome.  Evaluates as ``True`` when verified.

    Examples
    --------
    >>> from hoareagent import verify
    >>> result = verify(code="x > 0", pre="x > 0", post="x > 0")
    >>> bool(result)
    True
    """
    if callable(code):
        doc = inspect.getdoc(code) or ""
        extracted_pre, extracted_post = _parse_docstring_conditions(doc)
        resolved_pre  = pre  if pre  is not None else extracted_pre
        resolved_post = post if post is not None else extracted_post
    else:
        extracted_pre, extracted_post = _parse_source_conditions(code)
        resolved_pre  = pre  if pre  is not None else extracted_pre
        resolved_post = post if post is not None else extracted_post

    return _run_z3(
        pre=resolved_pre or "True",
        post=resolved_post or "True",
        invariants=loop_invariants or [],
        timeout_ms=timeout_ms,
    )


def verified(
    *,
    pre: str = "True",
    post: str = "True",
    loop_invariants: Optional[List[str]] = None,
    timeout_ms: int = 5_000,
    raise_on_failure: bool = False,
) -> Callable:
    """Decorator that verifies a Hoare triple at decoration time.

    The verification result is stored on the wrapped function as
    ``fn.hoare_result``.

    Parameters
    ----------
    pre:
        Pre-condition expression.
    post:
        Post-condition expression.
    loop_invariants:
        Optional loop invariants.
    timeout_ms:
        Z3 solver timeout.
    raise_on_failure:
        If ``True``, raise :class:`AssertionError` when the triple cannot be
        verified (useful in strict CI pipelines).

    Examples
    --------
    >>> from hoareagent import verified
    >>> @verified(pre="x >= 0", post="result >= 0")
    ... def double(x):
    ...     return x * 2
    >>> double.hoare_result.verified
    True
    """
    def decorator(fn: Callable) -> Callable:
        result = verify(fn, pre=pre, post=post,
                        loop_invariants=loop_invariants, timeout_ms=timeout_ms)
        if raise_on_failure and not result.verified:
            raise AssertionError(
                f"Hoare verification failed for {fn.__qualname__!r}: {result}"
            )

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):  # type: ignore[misc]
            return fn(*args, **kwargs)

        wrapper.hoare_result = result  # type: ignore[attr-defined]
        wrapper.hoare_pre    = pre     # type: ignore[attr-defined]
        wrapper.hoare_post   = post    # type: ignore[attr-defined]
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Docstring / source condition extraction
# ---------------------------------------------------------------------------

_PRE_RE  = re.compile(r":pre:\s*(.+?)(?:\n|$)",  re.MULTILINE)
_POST_RE = re.compile(r":post:\s*(.+?)(?:\n|$)", re.MULTILINE)

# Also support ``# pre: ...`` and ``# post: ...`` comment style
_PRE_COMMENT_RE  = re.compile(r"#\s*pre:\s*(.+?)(?:\n|$)",  re.MULTILINE)
_POST_COMMENT_RE = re.compile(r"#\s*post:\s*(.+?)(?:\n|$)", re.MULTILINE)


def _parse_docstring_conditions(doc: str) -> tuple[str, str]:
    pre_m  = _PRE_RE.search(doc)
    post_m = _POST_RE.search(doc)
    return (
        pre_m.group(1).strip()  if pre_m  else "True",
        post_m.group(1).strip() if post_m else "True",
    )


def _parse_source_conditions(source: str) -> tuple[str, str]:
    """Extract ``# pre:`` / ``# post:`` annotations from raw source."""
    pre_m  = _PRE_COMMENT_RE.search(source)
    post_m = _POST_COMMENT_RE.search(source)
    return (
        pre_m.group(1).strip()  if pre_m  else "True",
        post_m.group(1).strip() if post_m else "True",
    )


# ---------------------------------------------------------------------------
# Identifier extraction
# ---------------------------------------------------------------------------

_IDENT_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")
_KEYWORDS = frozenset({
    "and", "or", "not", "True", "False", "None",
    "if", "else", "in", "is", "lambda",
    "And", "Or", "Not", "Int", "Real", "Bool",
})


def _extract_ids(expr: str) -> List[str]:
    return list({m for m in _IDENT_RE.findall(expr) if m not in _KEYWORDS})


# ---------------------------------------------------------------------------
# Safe AST → Z3 translator (no eval)
# ---------------------------------------------------------------------------

class _Z3Builder(ast.NodeVisitor):
    """Walk a Python AST and build a Z3 expression tree."""

    def __init__(self, env: Dict) -> None:
        self._env = env

    def build(self, expr_str: str):
        try:
            tree = ast.parse(expr_str, mode="eval")
        except SyntaxError as exc:
            raise ValueError(f"Syntax error in {expr_str!r}: {exc}") from exc
        return self.visit(tree.body)

    def visit_BoolOp(self, node: ast.BoolOp):
        import z3  # type: ignore
        ops = [self.visit(v) for v in node.values]
        return z3.And(*ops) if isinstance(node.op, ast.And) else z3.Or(*ops)

    def visit_UnaryOp(self, node: ast.UnaryOp):
        import z3  # type: ignore
        operand = self.visit(node.operand)
        if isinstance(node.op, ast.Not):
            return z3.Not(operand)
        if isinstance(node.op, ast.USub):
            return -operand
        raise ValueError(f"Unsupported UnaryOp: {node.op!r}")

    def visit_Compare(self, node: ast.Compare):
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
        raise ValueError(f"Unsupported comparison: {op!r}")

    def visit_BinOp(self, node: ast.BinOp):
        left  = self.visit(node.left)
        right = self.visit(node.right)
        op    = node.op
        if isinstance(op, ast.Add):      return left + right
        if isinstance(op, ast.Sub):      return left - right
        if isinstance(op, ast.Mult):     return left * right
        if isinstance(op, ast.FloorDiv): return left / right
        raise ValueError(f"Unsupported BinOp: {op!r}")

    def visit_Constant(self, node: ast.Constant):
        import z3  # type: ignore
        if isinstance(node.value, bool):  return z3.BoolVal(node.value)
        if isinstance(node.value, int):   return z3.IntVal(node.value)
        if isinstance(node.value, float): return z3.RealVal(node.value)
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    def visit_Name(self, node: ast.Name):
        import z3  # type: ignore
        if node.id == "True":  return z3.BoolVal(True)
        if node.id == "False": return z3.BoolVal(False)
        if node.id not in self._env:
            raise ValueError(
                f"Unknown identifier '{node.id}'. "
                "Declare it as a symbolic variable in the pre/post-condition."
            )
        return self._env[node.id]

    def generic_visit(self, node: ast.AST):  # type: ignore[override]
        raise ValueError(
            f"Unsupported AST node '{type(node).__name__}'. "
            "Use SMT-LIB2 notation for complex expressions."
        )


def _expr_to_z3(expr: str, env: Dict):
    return _Z3Builder(env).build(expr)


# ---------------------------------------------------------------------------
# Core Z3 runner
# ---------------------------------------------------------------------------

def _run_z3(
    pre: str,
    post: str,
    invariants: List[str],
    timeout_ms: int,
) -> HoareResult:
    try:
        import z3  # type: ignore
    except ImportError:
        return HoareResult(
            verified=False,
            verdict="ERROR",
            error_detail=(
                "z3-solver is not installed. "
                "Run: pip install z3-solver  (or: pip install hoare-agent[z3])"
            ),
        )

    t0 = time.monotonic()
    try:
        solver = z3.Solver()
        solver.set("timeout", timeout_ms)

        all_ids = list(set(_extract_ids(pre) + _extract_ids(post)))
        for inv in invariants:
            all_ids = list(set(all_ids + _extract_ids(inv)))
        env = {name: z3.Int(name) for name in all_ids}
        decls = "\n".join(f"(declare-const {n} Int)" for n in all_ids)

        def _add_condition(cond: str) -> None:
            if cond.lstrip().startswith("("):
                for c in z3.parse_smt2_string(f"{decls}\n(assert {cond})"):
                    solver.add(c)
            else:
                solver.add(_expr_to_z3(cond, env))

        def _add_negated(cond: str) -> None:
            if cond.lstrip().startswith("("):
                for c in z3.parse_smt2_string(f"{decls}\n(assert (not {cond}))"):
                    solver.add(c)
            else:
                solver.add(z3.Not(_expr_to_z3(cond, env)))

        _add_condition(pre)
        for inv in invariants:
            _add_condition(inv)
        _add_negated(post)

        result_str = str(solver.check())
        elapsed = int((time.monotonic() - t0) * 1_000)

        if result_str == "unsat":
            return HoareResult(verified=True, verdict="VERIFIED", elapsed_ms=elapsed)
        if result_str == "sat":
            model = solver.model()
            ce = "; ".join(f"{d.name()} = {model[d]}" for d in model.decls())
            return HoareResult(
                verified=False,
                verdict="COUNTEREXAMPLE",
                counterexample=ce,
                elapsed_ms=elapsed,
            )
        # unknown / timeout
        return HoareResult(
            verified=False,
            verdict="TIMEOUT",
            error_detail="Z3 solver returned 'unknown' (timeout or incompleteness)",
            elapsed_ms=elapsed,
        )

    except Exception as exc:  # noqa: BLE001
        elapsed = int((time.monotonic() - t0) * 1_000)
        return HoareResult(
            verified=False,
            verdict="ERROR",
            error_detail=str(exc),
            elapsed_ms=elapsed,
        )
