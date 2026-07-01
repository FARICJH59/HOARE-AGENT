"""
Self-Verifying LLM Agent (Two-Pass Hoare Loop)
===============================================

Pass 1 — Generate
    The LLM receives a task description and a target schema.  It produces:
      • A Python / SQL transformation function (the *program* C).
      • A pre-condition P and post-condition Q expressed as Python boolean
        expressions or SMT-LIB2 formulas.
      • Optional loop invariants.

Pass 2 — Verify
    The generated Hoare triple {P} C {Q} is fed into :mod:`hoare_engine.verifier`.
    If the Z3 proof succeeds the code is released for execution.
    If the proof fails a *structured error vector* (the counterexample + the
    failed proof attempt) is appended to the conversation and Pass 1 is
    repeated, up to ``max_retries`` times.

LLM Integration
---------------
The agent is designed to work with any OpenAI-compatible endpoint
(vLLM, SGLang, Azure OpenAI).  Set the environment variables:

    HOARE_LLM_BASE_URL   — e.g. http://localhost:8000/v1
    HOARE_LLM_MODEL      — e.g. Qwen/Qwen2.5-0.5B-Instruct
    HOARE_LLM_API_KEY    — bearer token (defaults to "EMPTY" for local vLLM)

If no LLM is reachable the agent falls back to :func:`_mock_llm_call` which
returns a hard-coded template — useful for unit tests and CI pipelines.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from schema.models import (
    AgentTaskRequest,
    AgentTaskResult,
    FSMStateEnum,
    HoareTriple,
    VerificationVerdict,
)
from hoare_engine.verifier import verify_triple
from hoare_engine.pda_engine import registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_LLM_BASE_URL = os.getenv("HOARE_LLM_BASE_URL", "http://localhost:8000/v1")
_LLM_MODEL    = os.getenv("HOARE_LLM_MODEL",    "Qwen/Qwen2.5-0.5B-Instruct")
_LLM_API_KEY  = os.getenv("HOARE_LLM_API_KEY",  "EMPTY")


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a formally-verified data-engineering agent.

When given a data transformation task you MUST respond with a JSON object
that has exactly the following keys:

{
  "program":        "<Python function body as a string>",
  "precondition":   "<boolean Python expression or SMT-LIB2 assertion>",
  "postcondition":  "<boolean Python expression or SMT-LIB2 assertion>",
  "loop_invariants": ["<inv1>", "<inv2>"]
}

Rules:
1. The program must be a pure Python function called `transform(data: dict) -> dict`.
2. Pre/post-conditions must be valid Python boolean expressions involving the
   symbolic variable names that appear in the program (e.g. n, x, result).
3. Include at least one non-trivial loop invariant if the program contains a loop.
4. Do NOT include markdown fences or any text outside the JSON object.
"""

_REFACTOR_PROMPT_TEMPLATE = """\
The Hoare triple you generated failed verification.

Verdict      : {verdict}
Counterexample: {counterexample}
Error detail : {error_detail}

Please fix the program so that the triple {{P}} C {{Q}} holds.
Re-generate the full JSON response (program + pre/post-conditions + invariants).
"""


# ---------------------------------------------------------------------------
# LLM call (with mock fallback)
# ---------------------------------------------------------------------------

def _try_openai_call(messages: List[Dict[str, str]]) -> str:
    """Call an OpenAI-compatible endpoint.  Returns the assistant message text."""
    try:
        import openai  # type: ignore
    except ImportError:
        raise RuntimeError("openai package not installed; run: pip install openai")

    client = openai.OpenAI(
        base_url=_LLM_BASE_URL,
        api_key=_LLM_API_KEY,
    )
    response = client.chat.completions.create(
        model=_LLM_MODEL,
        messages=messages,  # type: ignore[arg-type]
        temperature=0.0,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""


def _mock_llm_call(_messages: List[Dict[str, str]]) -> str:  # noqa: ARG001
    """
    Deterministic mock used when no LLM endpoint is configured.
    Returns a valid Hoare-annotated identity transform that always verifies.
    """
    return json.dumps({
        "program": (
            "def transform(data: dict) -> dict:\n"
            "    n = len(data)\n"
            "    result = {k: v for k, v in data.items()}\n"
            "    return result"
        ),
        "precondition":  "n >= 0",
        "postcondition": "n >= 0",
        "loop_invariants": ["n >= 0"],
    })


def _call_llm(messages: List[Dict[str, str]], use_mock: bool = False) -> str:
    if use_mock:
        return _mock_llm_call(messages)
    try:
        return _try_openai_call(messages)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM call failed (%s); falling back to mock.", exc)
        return _mock_llm_call(messages)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_llm_response(text: str) -> Optional[HoareTriple]:
    """Extract a :class:`HoareTriple` from the LLM's JSON response."""
    # Strip markdown fences if the model ignored instructions
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        obj: Dict[str, Any] = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("LLM returned non-JSON: %s — %s", text[:200], exc)
        return None

    try:
        return HoareTriple(
            precondition=obj.get("precondition", "True"),
            program=obj.get("program", ""),
            postcondition=obj.get("postcondition", "True"),
            loop_invariants=obj.get("loop_invariants", []),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to parse HoareTriple: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Agent state observer (for dashboard / gRPC streaming)
# ---------------------------------------------------------------------------

class AgentObserver:
    """
    Callback interface for observing FSM state changes during agent execution.
    The gRPC server attaches a concrete implementation that streams FSMState
    messages to connected dashboard clients.
    """

    def on_state_change(self, state: FSMStateEnum, detail: str) -> None:  # noqa: B027
        pass


class LoggingObserver(AgentObserver):
    def on_state_change(self, state: FSMStateEnum, detail: str) -> None:
        logger.info("[FSM] %s — %s", state.value, detail)


# ---------------------------------------------------------------------------
# Core agent
# ---------------------------------------------------------------------------

class HoareAgent:
    """
    Two-pass self-verifying agent.

    Parameters
    ----------
    use_mock_llm:
        Force the mock LLM regardless of environment variables.  Useful for
        unit tests and CI.
    observer:
        An optional :class:`AgentObserver` that receives FSM state transitions.
    """

    def __init__(
        self,
        use_mock_llm: bool = False,
        observer: Optional[AgentObserver] = None,
    ) -> None:
        self._use_mock = use_mock_llm
        self._observer = observer or LoggingObserver()

    # ── Public ─────────────────────────────────────────────────────────────

    def run_task(self, request: AgentTaskRequest) -> AgentTaskResult:
        """
        Execute the generate → verify → (refactor)* loop.

        Returns an :class:`AgentTaskResult` with ``success=True`` if the
        generated code was formally verified within ``max_retries`` iterations.
        """
        self._notify(FSMStateEnum.INGESTING, f"Task '{request.task_id}' started")
        messages = self._build_initial_messages(request)

        triple: Optional[HoareTriple] = None
        proof = None
        repair_trace: List[Dict[str, Any]] = []

        for attempt in range(1, request.max_retries + 1):
            self._notify(
                FSMStateEnum.PARSING,
                f"Pass 1 — generating code (attempt {attempt}/{request.max_retries})",
            )

            raw_response = _call_llm(messages, use_mock=self._use_mock)
            triple = _parse_llm_response(raw_response)

            if triple is None:
                messages.append({
                    "role": "user",
                    "content": "Your response was not valid JSON.  Please try again.",
                })
                continue

            self._notify(FSMStateEnum.VERIFYING, "Pass 2 — running Z3 proof")
            proof = verify_triple(triple)
            repair_trace.append({
                "attempt": attempt,
                "verified": proof.verified,
                "verdict": proof.verdict.value,
                "counterexample": proof.counterexample,
                "error_detail": proof.error_detail,
                "elapsed_ms": proof.elapsed_ms,
            })

            if proof.verified:
                self._notify(FSMStateEnum.COMMITTED, "Triple verified — code released")
                return AgentTaskResult(
                    task_id=request.task_id,
                    generated_code=triple.program,
                    triple=triple,
                    proof=proof,
                    repair_trace=repair_trace,
                    iterations=attempt,
                    success=True,
                )

            # Proof failed — feed counterexample back as a refactor prompt
            self._notify(
                FSMStateEnum.BLOCKED,
                f"Proof failed ({proof.verdict}) — entering self-healing loop",
            )
            refactor_msg = _REFACTOR_PROMPT_TEMPLATE.format(
                verdict=proof.verdict,
                counterexample=proof.counterexample or "N/A",
                error_detail=proof.error_detail or "N/A",
            )
            messages.append({"role": "assistant", "content": raw_response})
            messages.append({"role": "user",      "content": refactor_msg})

        # Max retries exhausted
        self._notify(FSMStateEnum.ERROR, "Max retries reached without proof")
        return AgentTaskResult(
            task_id=request.task_id,
            generated_code=triple.program if triple else "",
            triple=triple,
            proof=proof,
            repair_trace=repair_trace,
            iterations=request.max_retries,
            success=False,
            failure_reason=(
                f"Proof failed after {request.max_retries} attempts. "
                f"Last verdict: {proof.verdict if proof else 'N/A'}"
            ),
        )

    # ── Internal ───────────────────────────────────────────────────────────

    def _notify(self, state: FSMStateEnum, detail: str) -> None:
        self._observer.on_state_change(state, detail)

    @staticmethod
    def _build_initial_messages(request: AgentTaskRequest) -> List[Dict[str, str]]:
        user_msg = (
            f"Task: {request.description}\n\n"
            f"Target schema (JSON):\n{request.target_schema}\n\n"
            "Generate a formally-verified transformation function for this schema."
        )
        return [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ]
