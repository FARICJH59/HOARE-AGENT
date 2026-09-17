from __future__ import annotations

import pytest

from hoare_engine.execution_admission import (
    ExecutionAdmission,
    ExecutionDecision,
    ExecutionNotAdmitted,
    execute_admitted,
)


class StubAuthority:
    def __init__(self, decision: ExecutionDecision) -> None:
        self.decision = decision
        self.calls = 0

    def admit(self, _request: object) -> ExecutionAdmission:
        self.calls += 1
        return ExecutionAdmission(
            decision=self.decision,
            reason=self.decision.value.lower(),
            authority_id="test-authority",
        )


def test_allowed_admission_invokes_existing_executor_once():
    authority = StubAuthority(ExecutionDecision.ALLOW)
    calls: list[object] = []

    result = execute_admitted(
        {"action": "test"},
        authority,
        lambda request: calls.append(request) or "executed",
    )

    assert result == "executed"
    assert authority.calls == 1
    assert calls == [{"action": "test"}]


@pytest.mark.parametrize("decision", [ExecutionDecision.DENY, ExecutionDecision.ESCALATE])
def test_non_allow_admission_never_invokes_executor(decision: ExecutionDecision):
    authority = StubAuthority(decision)
    calls: list[object] = []

    with pytest.raises(ExecutionNotAdmitted):
        execute_admitted(
            {"action": "blocked"},
            authority,
            lambda request: calls.append(request),
        )

    assert authority.calls == 1
    assert calls == []
