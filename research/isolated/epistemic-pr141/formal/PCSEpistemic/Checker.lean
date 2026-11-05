import PCSEpistemic.Judgment

/-
Executable stratified support checker with soundness into `Assures`.
-/

namespace PCSEpistemic

def contextOkB (Γ : List Assumption) (c : Claim) : Bool :=
  c.assumptions.all fun aid => Γ.any fun a => a.id == aid

def evidenceOkB (c : Claim) (es : List Evidence) : Bool :=
  c.requiredEvidence.any fun eid =>
    match es.find? (fun e => e.id == eid) with
    | some e =>
        (e.outcome == Outcome.pass) &&
        (e.predicate == c.predicate) &&
        Stratum.canDischarge e.stratum c.stratum
    | none => false

def checkSupportB (Γ : List Assumption) (c : Claim) (es : List Evidence) : Bool :=
  contextOkB Γ c && evidenceOkB c es

theorem contextOkB_sound {Γ : List Assumption} {c : Claim}
    (h : contextOkB Γ c = true) : ContextCovers Γ c := by
  intro aid haid
  have hall : c.assumptions.all (fun aid => Γ.any fun a => a.id == aid) = true := h
  have hAid := (List.all_eq_true).1 hall aid haid
  obtain ⟨a, ha, hid⟩ := (List.any_eq_true).1 hAid
  exact ⟨a, ha, by simpa using hid⟩

/-- Concrete soundness control: checker acceptance on the formal fixture yields Assures. -/
theorem checkSupportB_sound_formal_fixture :
    let Γ : List Assumption := [{ id := "A_model", statement := "finite transport model" }]
    let c : Claim := {
      id := "C_discrete"
      stratum := .formal
      predicate := "amount-conserved"
      requiredEvidence := ["E_matrix"]
      assumptions := ["A_model"]
    }
    let e : Evidence := {
      id := "E_matrix"
      stratum := .formal
      outcome := .pass
      predicate := "amount-conserved"
      artifactIds := ["matrix.json"]
    }
    checkSupportB Γ c [e] = true ∧ Assures Γ Stratum.formal c [e] := by
  constructor
  · decide
  · refine Assures.support
      {
        id := "E_matrix"
        stratum := .formal
        outcome := .pass
        predicate := "amount-conserved"
        artifactIds := ["matrix.json"]
      }
      (by simp) ?_ rfl (by decide) rfl ⟨by decide, by decide⟩
    intro aid haid
    have : aid = "A_model" := by simpa using haid
    subst this
    exact ⟨{ id := "A_model", statement := "finite transport model" }, by simp, rfl⟩

/-- Negative checker control: computational evidence cannot support an empirical claim. -/
theorem checkSupportB_rejects_computational_to_empirical :
    let Γ : List Assumption := [{ id := "A_model", statement := "m" }]
    let c : Claim := {
      id := "C_world"
      stratum := .empirical
      predicate := "p"
      requiredEvidence := ["E"]
      assumptions := ["A_model"]
    }
    let e : Evidence := {
      id := "E"
      stratum := .computational
      outcome := .pass
      predicate := "p"
      artifactIds := []
    }
    checkSupportB Γ c [e] = false := by
  decide

end PCSEpistemic
