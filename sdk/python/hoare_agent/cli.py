"""
hoare-agent CLI
===============

Usage
-----
Verify a Python file with inline Hoare annotations::

    hoare-agent verify mymodule.py

Verify with explicit pre/post-conditions::

    hoare-agent verify --pre "n >= 0" --post "n >= 0" mymodule.py

Verify a JSON triple file::

    hoare-agent verify triple.json

Use the Hoare-Agent backend REST API instead of the local Z3 solver::

    hoare-agent verify --backend http://localhost:8080 mymodule.py
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from hoare_agent._models import HoareTriple, VerificationResult, VerificationVerdict
from hoare_agent._parser import parse_file
from hoare_agent._verifier import run_z3


def _verify_via_http(triple: HoareTriple, backend_url: str) -> VerificationResult:
    """Send the triple to the backend /verify endpoint."""
    url = backend_url.rstrip("/") + "/verify"
    payload = json.dumps({
        "triple": {
            "precondition":    triple.precondition,
            "program":         triple.program,
            "postcondition":   triple.postcondition,
            "loop_invariants": triple.loop_invariants,
        }
    }).encode()

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read().decode())
        return VerificationResult(
            verified=False,
            verdict=VerificationVerdict.ERROR,
            error_detail=f"HTTP {exc.code}: {body}",
        )
    except OSError as exc:
        return VerificationResult(
            verified=False,
            verdict=VerificationVerdict.ERROR,
            error_detail=f"Cannot reach backend at {backend_url}: {exc}",
        )

    return VerificationResult(
        verified=body.get("verified", False),
        verdict=VerificationVerdict(body.get("verdict", "ERROR")),
        counterexample=body.get("counterexample", ""),
        error_detail=body.get("error_detail", ""),
        elapsed_ms=body.get("elapsed_ms", 0),
    )


def _cmd_verify(args: argparse.Namespace) -> int:
    """Implementation of the `verify` sub-command."""
    path = Path(args.file)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 1

    # Build the triple from flags or file annotations
    if args.pre or args.post:
        if not args.pre or not args.post:
            print(
                "error: --pre and --post must both be provided when using flags",
                file=sys.stderr,
            )
            return 1
        triple = HoareTriple(
            precondition=args.pre,
            program=path.read_text(encoding="utf-8"),
            postcondition=args.post,
            loop_invariants=[i.strip() for i in (args.inv or [])],
        )
    else:
        try:
            triple = parse_file(path)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        if triple is None:
            print(
                f"error: no Hoare annotations found in {path}.\n"
                "Add '# @pre: ...' and '# @post: ...' comments, "
                "or pass --pre / --post flags.",
                file=sys.stderr,
            )
            return 1

    # Run verification
    if args.backend:
        result = _verify_via_http(triple, args.backend)
    else:
        result = run_z3(triple, timeout_ms=args.timeout_ms)

    if args.json_output:
        print(result.model_dump_json(indent=2))
    else:
        _print_result(result, str(path))

    return 0 if result.verified else 2


def _print_result(result: VerificationResult, label: str) -> None:
    print(f"\nHoare-Agent verification: {label}")
    print("─" * 50)
    if result.verified:
        print(f"  Status : \033[32m✓ VERIFIED\033[0m")
        print(f"  Elapsed: {result.elapsed_ms} ms")
    elif result.verdict == VerificationVerdict.COUNTEREXAMPLE:
        print(f"  Status       : \033[31m✗ COUNTEREXAMPLE\033[0m")
        print(f"  Counterexample: {result.counterexample}")
        print(f"  Elapsed      : {result.elapsed_ms} ms")
    elif result.verdict == VerificationVerdict.TIMEOUT:
        print(f"  Status : \033[33m✗ TIMEOUT\033[0m")
        print(f"  Detail : {result.error_detail}")
    else:
        print(f"  Status : \033[31m✗ ERROR\033[0m")
        print(f"  Detail : {result.error_detail}")
    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hoare-agent",
        description="Hoare-Agent: formally-verified code pipeline SDK",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # ── verify sub-command ────────────────────────────────────────────────
    verify = sub.add_parser(
        "verify",
        help="Verify a Hoare triple extracted from a file",
        description=(
            "Verify a Hoare triple.  Annotations are read from '# @pre:' and "
            "'# @post:' comments in the source file, or from --pre/--post flags."
        ),
    )
    verify.add_argument("file", metavar="FILE", help="Python source file or JSON triple file")
    verify.add_argument("--pre",  metavar="EXPR", help="Pre-condition expression (overrides file annotation)")
    verify.add_argument("--post", metavar="EXPR", help="Post-condition expression (overrides file annotation)")
    verify.add_argument("--inv",  metavar="EXPR", action="append",
                        help="Loop invariant expression (repeatable, used with --pre/--post)")
    verify.add_argument(
        "--backend", metavar="URL",
        help="Use the Hoare-Agent backend REST API (e.g. http://localhost:8080) instead of the local Z3 solver",
    )
    verify.add_argument(
        "--timeout-ms", type=int, default=5_000,
        help="Z3 solver timeout in milliseconds (default: 5000)",
    )
    verify.add_argument(
        "--json", dest="json_output", action="store_true",
        help="Output result as JSON",
    )

    return parser


def main(argv: Optional[list] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "verify":
        sys.exit(_cmd_verify(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
