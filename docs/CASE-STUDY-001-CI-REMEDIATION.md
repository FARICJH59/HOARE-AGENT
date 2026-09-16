# AesirGrid Case Study CI Remediation

Provenance: 2026-09-16

The focused AesirGrid workflow reached 34 tests on Python 3.12: 32 passed and 2 failed. Both failures were stale test fixtures constructing `AuthorityLease` without the now-required action binding. The implementation correctly enforces exact action binding; the remediation is to update those fixtures with `action="apply_maintenance_setpoint"` and rerun the focused workflow.
