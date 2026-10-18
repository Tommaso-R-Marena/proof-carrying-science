# PCS Epistemic Calculus v1 — Implementation Report

## Thesis

Critical computation increasingly arrives as **ensembles of rival models**, not
single certificates. Assurance infrastructure must therefore:

1. keep evidence classes un-conflated,
2. compose certificates without illicit promotion,
3. reopen claims when declared dependencies change,
4. refuse world non-impact without dependency completeness, and
5. expose agreement cores and dispute frontiers instead of collapsing disagreement.

This incubation implements that calculus with matching Lean proofs and an
independent Python checker.

## Exact Lean contracts

| Theorem | Meaning |
| --- | --- |
| `no_computational_to_formal` | Computational evidence cannot discharge formal obligations |
| `computational_cannot_assure_formal` | Assures rejects that promotion |
| `formal_evidence_assures_formal` | Accepted formal evidence supports formal claims |
| `compose_assures` | Pipeline composition under evidence-id disjointness |
| `claimsRequiring_covers` | Required affected evidence forces claim reopen |
| `hidden_dependency_blocks_world_nonimpact` | Completeness is mandatory for world non-impact |
| `distinguishing_not_unanimous` | Distinguishing observations are non-unanimous |
| `dispute_preserved_if_still_split` | Merges preserve remaining disputes |
| Controls `control_*` | Finite positive/negative kernel checks via `decide` |

Axiom audit (`PcsEpistemic.Audit`): only `propext` and/or `Quot.sound` (several
theorems are axiom-free).

## Architecture

```
certificate (JSON)
    │
    ▼
pcs_epistemic.checker  ──►  receipt (accepted?, no production authority)
    │
    ├── assures / compose   (lattice + Assures)
    ├── invalidate/nonimpact (declared graph + completeness gate)
    └── dialectic           (agreement / dispute / distinguishing)
```

Lean remains the mathematical authority for the reference calculus. Python is an
independent executable mirror for experiments and adversarial controls.

## Experiment: PK dialectic

Synthetic one- vs two-compartment ensemble:

- Agreement: `mass_conserved`, `cmax_bound`
- Dispute / distinguishing: `terminal_slope_matches_ke`
- Invalidation: changing `raw_plasma` reopens mass and Cmax claims
- Negative: hidden claim cannot receive world non-impact endorsement
- Negative: computational→formal promotion rejected

## Added rigor (continuation)

- Lattice laws: reflexivity, transitivity, antisymmetry, incomparability
- Assures: rejected evidence blocks; empirical↛formal; formal covers computational
- Dialectic: agreement/dispute disjointness; empty-ensemble; candidate subset
- Invalidation: `incomplete_never_endorses`; impact/nonimpact complementarity
- Lean↔Python differential vectors for all Controls fixtures
- Commons seed-corpus bridge (read-only) for INV-001..003 alignment
- Adversarial checker tests + single-byte mutation sweep
- `scripts/axiom_audit.sh` gates approved axiom closure

## Limits

Finite ensembles and declared graphs only. No continuous-time PK theorem, no
empirical study, no production signing, no Claim-IR coupling. Lean↔Python
agreement is finite differential evidence, not a refinement theorem.
