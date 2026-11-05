# Aristotle proof queue

Target toolchain: `leanprover/lean4:v4.28.0` (matching the most recent directly observed Aristotle backend default as of July 2026).

The formal library is intentionally split so Aristotle can solve small obligations in sequence.

## 0. First compile pass

Run from `formal/`:

```bash
lake build
```

Fix only genuine Lean/elaboration errors. Do not weaken theorem statements merely to make the build green without checking the intended semantics.

Important files:

- `PCS/Core.lean` — logical judgment `Assures Γ L C E`;
- `PCS/Decision.lean` — executable status decision;
- `PCS/Refinement.lean` — witness-to-logical-judgment proofs;
- `PCS/DecisionVectors.lean` — closed conformance examples;
- `PCS/PKPD.lean` — restricted PK/PD dimensional contract.

## 1. Preserve this semantic alignment

A computational claim may be supported by either:

```lean
EvidenceKind.computationalTest
```

or the stronger:

```lean
EvidenceKind.formalProof
```

This matches `pcs.decision.assess_claim` and the frozen vector
`computational_can_use_formal_evidence`.

Do not revert `Assures.computational` to computational-test-only unless the Python semantics are changed at the same time.

## 2. Prove decision extraction lemmas

Add these to a new file such as `PCS/DecisionExtraction.lean`.

### Computational

```lean
theorem decideClaim_computational_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.computational) :
    c.kind = ClaimKind.computational ∧
    RequiredEvidencePasses c es ∧
    (∃ e, e ∈ requiredEvidenceFor c es ∧
      (e.kind = EvidenceKind.computationalTest ∨
       e.kind = EvidenceKind.formalProof))
```

### Formal

```lean
theorem decideClaim_formal_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.formal) :
    c.kind = ClaimKind.formal ∧
    RequiredEvidencePasses c es ∧
    (∃ e, e ∈ requiredEvidenceFor c es ∧
      e.kind = EvidenceKind.formalProof)
```

### Empirical

```lean
theorem decideClaim_empirical_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.empirical) :
    c.kind = ClaimKind.empirical ∧
    RequiredEvidencePasses c es ∧
    (∃ e, e ∈ requiredEvidenceFor c es ∧
      (e.kind = EvidenceKind.empiricalValidation ∨
       e.kind = EvidenceKind.statisticalValidation))
```

### Mixed

```lean
theorem decideClaim_mixed_extract
    {c : Claim} {es : List Evidence}
    (h : decideClaim c es = DecisionStatus.mixed) :
    c.kind = ClaimKind.mixed ∧
    RequiredEvidencePasses c es ∧
    (∃ correctness,
      correctness ∈ requiredEvidenceFor c es ∧
      correctness.kind = EvidenceKind.formalProof) ∧
    (∃ empiricalEvidence,
      empiricalEvidence ∈ requiredEvidenceFor c es ∧
      (empiricalEvidence.kind = EvidenceKind.empiricalValidation ∨
       empiricalEvidence.kind = EvidenceKind.statisticalValidation))
```

Useful strategy: split on the Booleans in `decideClaim` in their exact evaluation order:

1. `missingRequiredEvidence`;
2. `hasOutcome Outcome.fail`;
3. `hasOutcome Outcome.unverified`;
4. `req.isEmpty`;
5. claim kind;
6. the relevant `hasKind` / `allKind` branch.

The impossible branches reduce to `open_` or `failed`, contradicting the accepted status.

## 3. Compose extraction with existing refinement proofs

After the extraction lemmas compile, prove the direct bridge theorems.

### Computational direct soundness

```lean
theorem decideClaim_computational_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.computational) :
    Assures Γ AssuranceLevel.computational c es := by
  rcases decideClaim_computational_extract h with
    ⟨claimKind, passes, witness⟩
  exact computational_claim_sound
    context claimKind passes binding witness
```

### Formal direct soundness

```lean
theorem decideClaim_formal_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.formal) :
    Assures Γ AssuranceLevel.formal c es := by
  rcases decideClaim_formal_extract h with
    ⟨claimKind, passes, witness⟩
  exact formal_claim_sound
    context claimKind passes binding witness
```

### Empirical direct soundness

```lean
theorem decideClaim_empirical_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.empirical) :
    Assures Γ AssuranceLevel.empirical c es := by
  rcases decideClaim_empirical_extract h with
    ⟨claimKind, passes, witness⟩
  exact empirical_claim_sound
    context claimKind passes binding witness
```

### Mixed direct soundness

```lean
theorem decideClaim_mixed_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence}
    (context : ContextCovers Γ c)
    (binding : RequiredEvidenceBound c es)
    (h : decideClaim c es = DecisionStatus.mixed) :
    Assures Γ AssuranceLevel.mixed c es := by
  rcases decideClaim_mixed_extract h with
    ⟨claimKind, passes, correctnessWitness, empiricalWitness⟩
  exact mixed_claim_sound
    context claimKind passes binding
    correctnessWitness empiricalWitness
```

These are the main theorem targets for issue #6.

## 4. Important boundary

The direct soundness theorems above still assume:

```lean
RequiredEvidenceBound c es
```

That assumption is deliberate. `decideClaim` only classifies already-replayed evidence; it does not itself prove that serialized evidence is semantically bound to the claim predicate.

The next project after issue #6 is therefore issue #7:

```text
serialized certificate
      ↓
verified/replayed normalized evidence
      ↓
RequiredEvidenceBound + ContextCovers
      ↓
decideClaim
      ↓
Assures Γ L C E
```

Do not collapse the serialization/domain-checker trust boundary into the decision theorem.

## 5. Final audit

After Aristotle closes the proofs:

```bash
lake build
! grep -R --line-number --fixed-strings 'sorry' PCS.lean PCS
```

Freeze any compile corrections and theorem changes in a normal Git commit. The resulting build is the first point at which PCS should describe this layer as machine-checked.
