# AesirGrid Case Study CI Validation Plan

Provenance: 2026-09-14

The AesirGrid case study is merged into `main`. The focused workflow should run on both pull requests and pushes to `main` so that the case study is continuously validated after merge.

Focused suite:

```text
backend/tests/test_case_study_aesirgrid.py
backend/tests/test_aesirgrid_simulation.py
backend/tests/test_aesirgrid_authority.py
backend/tests/test_aesirgrid_control_boundary.py
backend/tests/test_aesirgrid_case_study_end_to_end.py
backend/tests/test_governed_execution.py
```

The suite must prove:

1. product lifecycle reaches STAGED;
2. synthetic telemetry produces deterministic assessments;
3. shadow analysis is allowed without physical control;
4. missing authority escalates;
5. invalid/expired/revoked authority is denied;
6. STAGED products cannot execute;
7. STAGED → AUTHORIZED requires explicit admission;
8. the existing executor is invoked only after successful AEGIS admission and product authorization.
