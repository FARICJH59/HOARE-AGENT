"""
hoare-agent — Python SDK
========================

Quick start::

    from hoare_agent import verify

    result = verify(
        precondition="n >= 0",
        postcondition="n >= 0",
        program="def transform(data): return data",
    )
    if result:
        print("Verified!")
    else:
        print(f"Failed: {result}")

The :func:`verify` function uses the bundled Z3 solver by default.
Pass ``backend_url`` to delegate verification to a running Hoare-Agent
backend instead::

    result = verify(
        precondition="n >= 0",
        postcondition="n >= 0",
        backend_url="http://localhost:8080",
    )
"""

from __future__ import annotations

from typing import List, Optional

from hoare_agent._models import HoareTriple, VerificationResult, VerificationVerdict
from hoare_agent._verifier import run_z3

__all__ = [
    "verify",
    "HoareTriple",
    "VerificationResult",
    "VerificationVerdict",
]

__version__ = "0.1.0"


def verify(
    precondition: str,
    postcondition: str,
    program: str = "",
    loop_invariants: Optional[List[str]] = None,
    timeout_ms: int = 5_000,
    backend_url: Optional[str] = None,
) -> VerificationResult:
    """
    Verify the Hoare triple ``{precondition} program {postcondition}``.

    Parameters
    ----------
    precondition:
        Pre-condition P as a Python boolean expression or SMT-LIB2 assertion.
    postcondition:
        Post-condition Q as a Python boolean expression or SMT-LIB2 assertion.
    program:
        Optional program text C (informational; not symbolically executed).
    loop_invariants:
        Optional list of loop invariant expressions.
    timeout_ms:
        Z3 solver timeout in milliseconds (default 5 000).  Ignored when
        ``backend_url`` is set.
    backend_url:
        When given, verification is delegated to the Hoare-Agent backend REST
        API at ``{backend_url}/verify`` instead of the local Z3 solver.

    Returns
    -------
    VerificationResult
        ``result.verified`` is ``True`` iff the triple was formally proved.
        The result object is truthy iff verified.
    """
    triple = HoareTriple(
        precondition=precondition,
        postcondition=postcondition,
        program=program,
        loop_invariants=loop_invariants or [],
    )

    if backend_url is not None:
        from hoare_agent.cli import _verify_via_http
        return _verify_via_http(triple, backend_url)

    return run_z3(triple, timeout_ms=timeout_ms)
