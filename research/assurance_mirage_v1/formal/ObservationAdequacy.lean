import AssuranceMirage

/-! Observation-based evaluation on reachable episodes and a finite partial monitor. -/
set_option autoImplicit false
namespace ObservationAdequacy

/-- A monitor must give the same answer on every episode it cannot distinguish. -/
def Uniform {E O V : Type} (obs : E → O) (score : E → V) : Prop :=
  ∀ a b, obs a = obs b → score a = score b

/-- On a view with a chosen representative of each observation, uniformity is
necessary and sufficient. The evaluator only needs to agree on reachable observations. -/
theorem factor_iff_uniform {E O V : Type} (obs : E → O) (score : E → V)
    (repr : O → E) (sectionOnImage : ∀ e, obs (repr (obs e)) = obs e) :
    (∃ f : O → V, ∀ e, score e = f (obs e)) ↔ Uniform obs score := by
  constructor
  · rintro ⟨f, h⟩ a b eq
    rw [h a, h b, eq]
  · intro h
    exact ⟨fun o => score (repr o), fun e => (h _ _ (sectionOnImage e)).symm⟩

open AssuranceMirage

theorem channel1_iff_uniform (score : Episode → Nat) :
    Channel1Factorable score ↔ Uniform Episode.tools score :=
  factor_iff_uniform _ _ (fun t => ⟨t, [], ⟨false⟩⟩) (fun _ => rfl)

/-- A detector that only reads the leak bit when the tool log is empty.
It ties the published four-step pair but varies within the empty-tool fiber. -/
def emptyLogScore (e : Episode) : Nat :=
  if e.tools.isEmpty && e.raw.leaked then 1 else 0

theorem tie_without_factor :
    emptyLogScore (episodeOf safePropose false 4) =
      emptyLogScore (episodeOf unsafePropose true 4) ∧
    ¬ Channel1Factorable emptyLogScore := by
  constructor
  · decide
  · intro h
    have bad := (channel1_iff_uniform _).1 h ⟨[], [], ⟨false⟩⟩ ⟨[], [], ⟨true⟩⟩ rfl
    cases bad

/-- An arbitrary finite episode domain with independent Boolean labels.
An observation can support zero, one, or both labels in this domain. -/
def supports {E O : Type} [DecidableEq O] (domain : List E)
    (obs : E → O) (label : E → Bool) (o : O) (v : Bool) : Bool :=
  domain.any fun e => decide (obs e = o ∧ label e = v)

/-- Return a verdict exactly when all compatible labels agree and evidence exists. -/
def monitor {E O : Type} [DecidableEq O] (domain : List E)
    (obs : E → O) (label : E → Bool) (o : O) : Option Bool :=
  match supports domain obs label o false, supports domain obs label o true with
  | true, false => some false
  | false, true => some true
  | _, _ => none

theorem monitor_exact {E O : Type} [DecidableEq O] (domain : List E)
    (obs : E → O) (label : E → Bool) (o : O) (v : Bool) :
    monitor domain obs label o = some v ↔
    (∃ e ∈ domain, obs e = o) ∧ ∀ e ∈ domain, obs e = o → label e = v := by
  have supp (b : Bool) : supports domain obs label o b = true ↔
      ∃ e ∈ domain, obs e = o ∧ label e = b := by simp [supports]
  constructor
  · intro hm
    have hv : supports domain obs label o v = true ∧ supports domain obs label o (!v) = false := by
      cases v <;> cases hf : supports domain obs label o false <;>
        cases ht : supports domain obs label o true <;> simp_all [monitor]
    obtain ⟨e, mem, eq, _⟩ := (supp v).1 hv.1
    refine ⟨⟨e, mem, eq⟩, ?_⟩
    intro x hx ho
    cases he : label x <;> cases v <;> first | rfl | (
      have contra := (supp _).2 ⟨x, hx, ho, he⟩
      simp_all)
  · rintro ⟨⟨e, mem, eq⟩, same⟩
    have yes := (supp v).2 ⟨e, mem, eq, same e mem eq⟩
    have no : supports domain obs label o (!v) ≠ true := by
      intro h
      obtain ⟨x, hx, he, hneg⟩ := (supp _).1 h
      have both := same x hx he
      cases v <;> simp_all
    cases v <;> cases hf : supports domain obs label o false <;>
      cases ht : supports domain obs label o true <;> simp_all [monitor]

/-- Adding instrumentation preserves every decisive verdict at an actually
observed episode, provided dropping the additional instrumentation recovers the old view. -/
theorem refinement_preserves_verdict {E O F : Type} [DecidableEq O] [DecidableEq F]
    (domain : List E) (fine : E → F) (forget : F → O) (label : E → Bool)
    (e : E) (he : e ∈ domain) (v : Bool)
    (old : monitor domain (fun x => forget (fine x)) label (forget (fine e)) = some v) :
    monitor domain fine label (fine e) = some v := by
  have h := (monitor_exact ..).1 old
  apply (monitor_exact ..).2
  exact ⟨⟨e, he, rfl⟩, fun x hx eq => h.2 x hx (congrArg forget eq)⟩

/-- Two Boolean episodes agree on the coarse view, disagree on their labels.
Refinement yields information. An empty table still cannot issue a verdict. -/
theorem monitors_boundary :
    monitor [false, true] (fun _ => ()) id () = none ∧
    monitor [false, true] id id true = some true ∧
    monitor ([] : List Bool) id id true = none := by decide

#print axioms factor_iff_uniform
#print axioms channel1_iff_uniform
#print axioms tie_without_factor
#print axioms monitor_exact
#print axioms refinement_preserves_verdict
#print axioms monitors_boundary

end ObservationAdequacy
