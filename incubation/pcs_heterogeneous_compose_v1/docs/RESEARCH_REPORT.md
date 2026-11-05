# HECK v1 research report

**Date:** 2026-10-18  
**Branch:** `feature/heterogeneous-compose-kernel-v1-5880`  
**Scope:** `incubation/pcs_heterogeneous_compose_v1/` only

## Problem

PCS leaf kernels prove strong local contracts (transport conservation, calibration
minimax, PK/PD replay). The founding Research Agenda still asks when certificates
compose and how heterogeneous evidence coexists without conflation. Parallel
workstreams (PGSI/PGSC6, CertNum, PCS Next) do not own this composition law.

## Contribution

1. **Theory.** A Mathlib-free Lean 4.28 calculus of assurance levels with proved
   meet-lattice laws, no-empirical-promotion, empty-reject, heterogeneous-pair
   law, and predictive match/falsify/sticky theorems (49 audit targets; 14
   executable controls).
2. **Architecture.** Theory IR + composite claim IR + independent Python receiver
   that recomputes meet, rejects underleveled/unsupported/empty composites, and
   evaluates predictive closure.
3. **Experimentation.** Composition campaign: transport+prediction closure at
   Empirical (not Formal); calibration-style computational+empirical; falsified
   prediction blocks closure. Conflation attack suite: **8/8 caught**.
4. **Engineering.** CLI (`meet|compose|verify|predict|theory|attacks`), fixtures,
   pytest (16), noninterference gate, Lean build without Mathlib.

## Results

| Gate | Outcome |
| --- | --- |
| `pytest -q` | 16 passed |
| Composition campaign | all scenarios PASS |
| Attack catch rate | 1.0 (8/8) |
| Formal-only fixture | accept |
| Formal+Empirical demanded as Formal | reject |
| `lake build` | success, no sorry/admit |

## Limits

- Leaf `supported` bits are upstream inputs in v1 (HECK does not re-run transport/calibration kernels).
- Not production PCS authority; scientific closure ≠ formal truth.
- Catch rate is suite-specific.
- No new physical measurements.

## Noninterference

No edits outside `incubation/pcs_heterogeneous_compose_v1/`. Does not touch
CertNum, PCS Next, PGSI/PGSC6, website, or production `pcs/` / `formal/PCS*`.
