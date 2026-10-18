import PCSEpistemic.Judgment

/-
Artifact-driven invalidation: changed bytes reopen dependent claims.
-/

namespace PCSEpistemic

def evidenceTouches (changed : List String) (e : Evidence) : Bool :=
  e.artifactIds.any (fun a => changed.contains a)

def claimTouches (changed : List String) (es : List Evidence) (c : Claim) : Bool :=
  c.requiredEvidence.any fun eid =>
    match es.find? (fun e => e.id == eid) with
    | some e => evidenceTouches changed e
    | none => false

structure Invalidation where
  changedArtifacts : List String
  affectedEvidence : List String
  affectedClaims : List String
  deriving DecidableEq, Repr

def invalidate (changed : List String) (es : List Evidence) (cs : List Claim) :
    Invalidation where
  changedArtifacts := changed
  affectedEvidence :=
    (es.filter (fun e => evidenceTouches changed e)).map (fun e => e.id)
  affectedClaims :=
    (cs.filter (fun c => claimTouches changed es c)).map (fun c => c.id)

def markUnverified (e : Evidence) : Evidence :=
  { e with outcome := Outcome.unverified }

theorem markUnverified_outcome (e : Evidence) :
    (markUnverified e).outcome = Outcome.unverified := rfl

theorem single_touched_cannot_assure
    {Γ : List Assumption} {s : Stratum} {c : Claim} {e : Evidence} :
    ¬ Assures Γ s c [markUnverified e] := by
  intro h
  cases h with
  | support e' member _ _ _ passed _ =>
      have : e' = markUnverified e := by
        simpa using member
      subst this
      simp [markUnverified] at passed

theorem all_unverified_cannot_assure
    {Γ : List Assumption} {s : Stratum} {c : Claim} {es : List Evidence}
    (hOnly : ∀ e ∈ es, e.outcome = Outcome.unverified) :
    ¬ Assures Γ s c es := by
  intro h
  cases h with
  | support e member _ _ _ passed _ =>
      have hout := hOnly e member
      simp [hout] at passed

end PCSEpistemic
