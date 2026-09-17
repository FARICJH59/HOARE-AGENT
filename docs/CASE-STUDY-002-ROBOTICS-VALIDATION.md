# HOARE Case Study #2 — Validation Record

**Provenance:** 2026-09-16  
**Case study:** `HOARE-CS-002`

## Validation target

Demonstrate that HOARE can represent and govern an industrial robotics inspection product using the same universal product-factory contract already used for AesirGrid.

## Assertions

- Domain changes from `energy` to `robotics` without a new HOARE core.
- Product lifecycle uses the existing ordered lifecycle contract.
- Robot telemetry is supplied through a provider boundary.
- Degraded observations produce a maintenance signal.
- Invalid observations fail closed.
- Shadow analysis is permitted without physical control.
- Controlled mode requires explicit authority.
- Product definitions remain non-executable.
- Vertical and customer IP references remain separate.

## Safety boundary

The case study is synthetic and does not issue robot motion commands or alter machine-safety controls.

## Interpretation

Case Study #1 demonstrates the architecture in an energy/grid context. Case Study #2 deliberately changes the physical domain while retaining the platform contract. Together, they provide a direct test of the claim that HOARE is a reusable control-plane/factory rather than an AesirGrid-specific application framework.
