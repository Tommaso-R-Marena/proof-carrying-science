# HANDOFF — Phase II

- **Branch:** `research/proof_carrying_scientific_reasoning_v0`
- **Phase II start head:** `518aa068`
- **Exclusive path:** `research/proof_carrying_scientific_reasoning_v0/`
- **PR:** #218 draft

## Phase II completed

1. Reproduced Findings A–G; frozen JSON under `results/security_findings_v1/` (do not edit).  
2. Schema v1 + `independent_checker/check_certificate_v1.py` (reconstructs judgments; rejects A/B/C forgeries).  
3. Lean `checkCertificate` + `checkCertificate_sound` (no sorryAx).  
4. Commutative meet; `math_established=false` on Hyp; Belnap witness; authority audit; contradiction report.  
5. Mutation suite, causal/PKPD cases, benchmarks, revised novelty (engineering, not foundational).

## Reproduce

```bash
bash scripts/check_all.sh
```

## Next (if continuing)

- Prove Derives ⇒ Entails4 for the supported fragment.  
- Exhaustive finite-model correspondence tables.  
- External attestation design for `math_established` (do not fake it).  
- More scientific stress cases.

## CI note

Sealed census may fail — do not weaken.
