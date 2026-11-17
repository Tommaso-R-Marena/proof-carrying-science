# Theorem inventory

Toolchain: Lean 4.28.0. Package: `lean/`. No sorry/admit/custom axioms.

| Theorem | File | Claim | Axioms |
|---|---|---|---|
| `derives_sound` | Soundness | Derives ⇒ Entails | propext |
| `derives_support_in_context` | Soundness | support ⊆ context ids | propext, Quot.sound |
| `andI_authority_meet` / `no_escalation_by_meet` / `meet_empirical_not_math` | Soundness/Authority | meet non-escalation | none / propext |
| `derives_atoms_from_context` | Contradictions | atoms from context | propext, Quot.sound |
| `no_ex_falso_unrelated_atom` | Contradictions | atom 99 underivable in demoΓ | propext, Quot.sound |
| `demo_locally_contradictory` | Contradictions | P and ¬P co-derivable | propext |
| `retract_removes` | Retraction | retracted ids absent | propext, Quot.sound |
| `hyp_invalidated_by_self` / `andI_support_union_invalidation` | Retraction | support invalidation | propext |
| `valid_implies_sound` | Certificates | valid cert ⇒ Entails | propext |

**Gap:** Entails explodes classically on unsatisfiable Γ; non-explosion is derivability-only (documented).
