import PCS.Core

namespace PCS.Decision

/-- Narrow Boolean helper for a single computational-test evidence object.
    Operational replay establishes the evidence outcome before this layer runs.

    This helper intentionally recognizes only `computationalTest`. The whole-claim
    `decideClaim` rule is the normative status decision and additionally permits a
    stronger `formalProof` to support a computational claim. -/
def computationalEvidenceAccepts (c : Claim) (e : Evidence) : Bool :=
  if c.kind = ClaimKind.computational then
    if e.kind = EvidenceKind.computationalTest then
      if e.outcome = Outcome.pass then
        if e.id ∈ c.requiredEvidence then
          if e.predicate = c.predicate then true else false
        else false
      else false
    else false
  else false

/-- A successful Boolean evidence decision plus explicit context/membership
    constructs the logical assurance judgment. -/
theorem computationalEvidenceAccepts_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence} {e : Evidence}
    (member : e ∈ es)
    (context : ContextCovers Γ c)
    (h : computationalEvidenceAccepts c e = true) :
    Assures Γ AssuranceLevel.computational c es := by
  simp [computationalEvidenceAccepts] at h
  rcases h with ⟨claimKind, evidenceKind, passed, required, predicate⟩
  exact Assures.computational e member context claimKind (Or.inl evidenceKind) passed ⟨required, predicate⟩

def formalEvidenceAccepts (c : Claim) (e : Evidence) : Bool :=
  if c.kind = ClaimKind.formal then
    if e.kind = EvidenceKind.formalProof then
      if e.outcome = Outcome.pass then
        if e.id ∈ c.requiredEvidence then
          if e.predicate = c.predicate then true else false
        else false
      else false
    else false
  else false

theorem formalEvidenceAccepts_sound
    {Γ : List Assumption} {c : Claim} {es : List Evidence} {e : Evidence}
    (member : e ∈ es)
    (context : ContextCovers Γ c)
    (h : formalEvidenceAccepts c e = true) :
    Assures Γ AssuranceLevel.formal c es := by
  simp [formalEvidenceAccepts] at h
  rcases h with ⟨claimKind, evidenceKind, passed, required, predicate⟩
  exact Assures.formal e member context claimKind evidenceKind passed ⟨required, predicate⟩

/-- Executable whole-claim status. This mirrors the pure Python decision kernel
    after artifact/evidence replay and semantic binding have already succeeded.
    It deliberately does not perform scientific checks itself. -/
inductive DecisionStatus
  | formal
  | computational
  | empirical
  | mixed
  | open_
  | failed
  deriving DecidableEq, Repr

def requiredEvidenceFor (c : Claim) (es : List Evidence) : List Evidence :=
  es.filter (fun e => c.requiredEvidence.contains e.id)

def missingRequiredEvidence (c : Claim) (es : List Evidence) : Bool :=
  c.requiredEvidence.any (fun eid => !(es.any (fun e => e.id == eid)))

def hasOutcome (o : Outcome) (es : List Evidence) : Bool :=
  es.any (fun e => e.outcome == o)

def hasKind (k : EvidenceKind) (es : List Evidence) : Bool :=
  es.any (fun e => e.kind == k)

def allKind (k : EvidenceKind) (es : List Evidence) : Bool :=
  es.all (fun e => e.kind == k)

/-- Pure claim decision corresponding to `pcs.decision.assess_claim`.

    Preconditions for the intended refinement theorem:
    * evidence IDs are unique;
    * all listed evidence has already been independently replayed/established;
    * claim/evidence semantic binding has already been checked;
    * the explicit assumption context is handled separately by `ContextCovers`.

    The decision is intentionally conservative: unsupported combinations remain OPEN.
-/
def decideClaim (c : Claim) (es : List Evidence) : DecisionStatus :=
  let req := requiredEvidenceFor c es
  if missingRequiredEvidence c es then
    DecisionStatus.open_
  else if hasOutcome Outcome.fail req then
    DecisionStatus.failed
  else if hasOutcome Outcome.unverified req then
    DecisionStatus.open_
  else if req.isEmpty then
    DecisionStatus.open_
  else
    match c.kind with
    | ClaimKind.formal =>
        if allKind EvidenceKind.formalProof req
        then DecisionStatus.formal
        else DecisionStatus.open_
    | ClaimKind.empirical =>
        if hasKind EvidenceKind.empiricalValidation req ||
           hasKind EvidenceKind.statisticalValidation req
        then DecisionStatus.empirical
        else DecisionStatus.open_
    | ClaimKind.mixed =>
        if hasKind EvidenceKind.formalProof req &&
           (hasKind EvidenceKind.empiricalValidation req ||
            hasKind EvidenceKind.statisticalValidation req)
        then DecisionStatus.mixed
        else DecisionStatus.open_
    | ClaimKind.computational =>
        if hasKind EvidenceKind.computationalTest req ||
           hasKind EvidenceKind.formalProof req
        then DecisionStatus.computational
        else DecisionStatus.open_

/-
Next machine-checked target once the Lean runner is available:

  decideClaim c es = DecisionStatus.<accepted class>
  ∧ NormalizedEvidence es
  ∧ ContextCovers Γ c
  --------------------------------------------------
  Assures Γ <corresponding AssuranceLevel> c es

This is intentionally a one-way soundness target, not completeness.
-/

end PCS.Decision
