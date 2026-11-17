# Formal specification — Scientific Argument Calculus v0

## Design choice (prior-art informed)

We use a **small natural-deduction fragment** over propositional atoms with:

- **explicit authority labels** on premises (justification / provenance flavored);
- **support sets** (assumption-based TMS / provenance-semiring flavor);
- **no ex falso** (paraconsistent containment for this fragment);
- **retraction** as invalidation of certificates whose support intersects withdrawn premises.

This is **not** claiming a new foundational logic. Novelty, if any, is the PCS-oriented composition of authority non-escalation + contradiction containment + independently replayable scientific certificates. See `research/PRIOR_ART.md`.

## Syntax

Atoms: `PropId` (Nat).  
Formulas: `atom p` | `not φ` | `and φ ψ`.  
Authority: `mathVerified` | `empiricalAsserted` | `assumption` | `hypothesis` | `derived` | `disputed`.  
Context `Γ`: list of `(PropId × Formula × Authority)` with unique PropIds for declared premises.  
Judgment: `Γ ⊢⟨S,a⟩ φ` — formula φ derived with support set `S ⊆ PropId` and result authority `a`.

## Well-formedness

- Context PropIds unique.  
- Support ids ⊆ context PropIds.  
- Negation polarity is syntactic (`not`); classical double-negation elimination is **not** a rule.

## Inference rules

1. **Hyp:** if `(i,φ,a) ∈ Γ` then `Γ ⊢⟨{i},a⟩ φ`.  
2. **AndI:** from `Γ ⊢⟨S,a⟩ φ` and `Γ ⊢⟨T,b⟩ ψ` infer `Γ ⊢⟨S∪T, meet(a,b)⟩ φ∧ψ`.  
3. **AndE₁ / AndE₂:** from `Γ ⊢⟨S,a⟩ φ∧ψ` infer the conjunct with same `S,a`.  
4. **NotI is not included in v0** (keeps fragment tiny).  
5. **No ExFalso:** there is no rule `φ, ¬φ ⇒ ψ` for arbitrary `ψ`.

## Authority lattice (meet)

Order (higher = stronger mathematical standing):  
`disputed < hypothesis < empiricalAsserted ≈ assumption < derived < mathVerified`  
with `meet` = greatest lower bound. Derivation **never increases** authority above the meet of used premises. In particular, `empiricalAsserted` premises cannot yield `mathVerified` conclusions.

## Contradiction

`Γ` is *locally contradictory on S* if some φ and ¬φ are both derived with supports ⊆ S.  
Local contradiction **does not** authorize unrelated ψ (non-explosion).

## Certificate validity

A certificate is valid iff every step is an instance of the rules above, support sets are correctly accumulated, authorities obey meet, and the conclusion formula matches the final judgment.

## Retraction

Withdrawing premise id `i` invalidates any certificate whose support contains `i`. Recompute from remaining premises; no incremental DAG cache (ICR #217 territory).

## What certificates prove / do not prove

**Prove:** under the encoded premises and rules, the conclusion is derivable with recorded support and authority.  
**Do not prove:** empirical truth of observations, applicability of models, scientific truth of hypotheses, or world-correctness of disputed claims.
