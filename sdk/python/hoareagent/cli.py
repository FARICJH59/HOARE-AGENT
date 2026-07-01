"""
CLI entry-point: ``hoare-agent``

Usage examples::

    # Verify all annotated functions in a file
    hoare-agent verify mymodule.py

    # Verify with explicit conditions (applied to every function in the file)
    hoare-agent verify mymodule.py --pre "x >= 0" --post "result >= 0"

    # Verify a single expression triple directly
    hoare-agent verify --pre "n > 5" --post "n > 0"

    # Show help
    hoare-agent --help
"""

from __future__ import annotations

import ast
import sys
import textwrap
from pathlib import Path
from typing import List, NamedTuple, Optional


# ---------------------------------------------------------------------------
# Small data helpers
# ---------------------------------------------------------------------------

class _FunctionSpec(NamedTuple):
    name: str
    pre: str
    post: str
    lineno: int


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

_PRE_PATTERNS  = ("# pre:",  ":pre:")
_POST_PATTERNS = ("# post:", ":post:")


def _strip_condition(text: str, marker: str) -> str:
    idx = text.lower().find(marker.lower())
    if idx == -1:
        return ""
    return text[idx + len(marker):].split("\n")[0].strip()


def _extract_specs_from_source(source: str) -> List[_FunctionSpec]:
    """
    Walk the AST and return one :class:`_FunctionSpec` per function that has
    ``:pre:`` / ``:post:`` docstring fields or ``# pre:`` / ``# post:``
    comment blocks immediately above its ``def``.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"[error] Syntax error parsing file: {exc}", file=sys.stderr)
        return []

    specs: List[_FunctionSpec] = []
    lines = source.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        pre  = "True"
        post = "True"

        # 1. Try docstring
        docstring = ast.get_docstring(node) or ""
        for marker in _PRE_PATTERNS:
            val = _strip_condition(docstring, marker)
            if val:
                pre = val
                break
        for marker in _POST_PATTERNS:
            val = _strip_condition(docstring, marker)
            if val:
                post = val
                break

        # 2. Fall back to comments immediately above the def
        if pre == "True" and post == "True":
            start = max(0, node.lineno - 5)
            comment_block = "\n".join(lines[start : node.lineno - 1])
            for marker in _PRE_PATTERNS:
                val = _strip_condition(comment_block, marker)
                if val:
                    pre = val
                    break
            for marker in _POST_PATTERNS:
                val = _strip_condition(comment_block, marker)
                if val:
                    post = val
                    break

        # Only include if at least one condition was explicitly annotated
        if pre != "True" or post != "True":
            specs.append(_FunctionSpec(
                name=node.name,
                pre=pre,
                post=post,
                lineno=node.lineno,
            ))

    return specs


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _print_result(label: str, result) -> None:  # type: ignore[type-arg]
    icon = "\u2705" if result.verified else "\u274c"
    print(f"  {icon}  {label}  [{result.verdict}]  ({result.elapsed_ms} ms)")
    if result.counterexample:
        print(f"       counterexample: {result.counterexample}")
    if result.error_detail:
        print(f"       detail: {result.error_detail}")


# ---------------------------------------------------------------------------
# Sub-command: verify
# ---------------------------------------------------------------------------

def _cmd_verify(args) -> int:  # type: ignore[type-arg]
    from hoareagent._core import verify, HoareResult

    explicit_pre  = getattr(args, "pre",  None)
    explicit_post = getattr(args, "post", None)
    timeout_ms    = getattr(args, "timeout", 5_000)
    file_path: Optional[Path] = getattr(args, "file", None)

    # ── Mode 1: no file — verify explicit conditions directly ─────────────
    if file_path is None:
        if explicit_pre is None and explicit_post is None:
            print("[error] Provide a file path or --pre / --post conditions.", file=sys.stderr)
            return 2
        result = verify(
            "",
            pre=explicit_pre or "True",
            post=explicit_post or "True",
            timeout_ms=timeout_ms,
        )
        _print_result("(inline)", result)
        return 0 if result.verified else 1

    # ── Mode 2: verify a file ─────────────────────────────────────────────
    try:
        source = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"[error] Cannot read {file_path}: {exc}", file=sys.stderr)
        return 2

    print(f"\nhoare-agent \u2014 verifying {file_path}\n")

    # If explicit conditions given, apply them to the whole file source
    if explicit_pre is not None or explicit_post is not None:
        result = verify(
            source,
            pre=explicit_pre,
            post=explicit_post,
            timeout_ms=timeout_ms,
        )
        _print_result(str(file_path), result)
        print()
        return 0 if result.verified else 1

    # Otherwise parse the file for annotated functions
    specs = _extract_specs_from_source(source)
    if not specs:
        print(
            "  \u26a0\ufe0f  No annotated functions found.\n"
            "  Add :pre: / :post: fields to docstrings, e.g.:\n\n"
            '      def add(x, y):\n'
            '          """\n'
            '          :pre:  x >= 0 and y >= 0\n'
            '          :post: result >= 0\n'
            '          """\n'
            '          return x + y\n',
            file=sys.stderr,
        )
        return 0

    results = []
    for spec in specs:
        result = verify(
            "",  # conditions only — code body not needed for Z3
            pre=spec.pre,
            post=spec.post,
            timeout_ms=timeout_ms,
        )
        label = f"{spec.name}  (line {spec.lineno})"
        _print_result(label, result)
        results.append(result)

    print()
    total  = len(results)
    passed = sum(1 for r in results if r.verified)
    failed = total - passed
    all_passed = failed == 0
    if all_passed:
        print(f"\u2705  All {total} triple(s) verified.")
    else:
        print(f"\u274c  {failed} of {total} triple(s) failed.")

    return 0 if all_passed else 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="hoare-agent",
        description="Formally verify Python functions with Hoare logic.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
        examples:
          hoare-agent verify mymodule.py
          hoare-agent verify mymodule.py --pre "x >= 0" --post "result >= 0"
          hoare-agent verify --pre "n > 5" --post "n > 0"
        """),
    )
    parser.add_argument("--version", action="version", version="hoare-agent 0.1.0")

    sub = parser.add_subparsers(dest="command")

    verify_p = sub.add_parser("verify", help="Verify a Python file or inline triple")
    verify_p.add_argument(
        "file",
        nargs="?",
        type=Path,
        metavar="FILE",
        help="Python source file to verify (optional)",
    )
    verify_p.add_argument("--pre",  default=None, metavar="EXPR",
                          help="Pre-condition expression")
    verify_p.add_argument("--post", default=None, metavar="EXPR",
                          help="Post-condition expression")
    verify_p.add_argument("--timeout", type=int, default=5_000, metavar="MS",
                          help="Z3 solver timeout in milliseconds (default: 5000)")

    args = parser.parse_args(argv)

    if args.command == "verify":
        sys.exit(_cmd_verify(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
