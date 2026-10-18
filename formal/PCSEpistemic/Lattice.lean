import PCSEpistemic.Stratum

/-
Finite lattice laws for epistemic strata. Research-grade; no scientific authority.
Ordinary kernel `decide` on the finite stratum type — never `native_decide`.
-/

namespace PCSEpistemic

theorem Stratum.meet_idempotent (a : Stratum) : meet a a = a := by
  cases a <;> decide

theorem Stratum.join_idempotent (a : Stratum) : join a a = a := by
  cases a <;> decide

theorem Stratum.join_comm (a b : Stratum) : join a b = join b a := by
  cases a <;> cases b <;> decide

theorem Stratum.meet_assoc (a b c : Stratum) :
    meet (meet a b) c = meet a (meet b c) := by
  cases a <;> cases b <;> cases c <;> decide

theorem Stratum.join_assoc (a b c : Stratum) :
    join (join a b) c = join a (join b c) := by
  cases a <;> cases b <;> cases c <;> decide

theorem Stratum.meet_join_absorb (a b : Stratum) : meet a (join a b) = a := by
  cases a <;> cases b <;> decide

theorem Stratum.join_meet_absorb (a b : Stratum) : join a (meet a b) = a := by
  cases a <;> cases b <;> decide

theorem Stratum.meet_glb (a b c : Stratum) :
    c ≤ a → c ≤ b → c ≤ meet a b := by
  cases a <;> cases b <;> cases c <;> decide

theorem Stratum.join_lub (a b c : Stratum) :
    a ≤ c → b ≤ c → join a b ≤ c := by
  cases a <;> cases b <;> cases c <;> decide

theorem Stratum.canDischarge_mono_evidence (e₁ e₂ c : Stratum) :
    e₁ ≤ e₂ → canDischarge e₁ c = true → canDischarge e₂ c = true := by
  cases e₁ <;> cases e₂ <;> cases c <;> decide

theorem Stratum.forbiddenPromotion_anti_evidence (e₁ e₂ c : Stratum) :
    e₁ ≤ e₂ → forbiddenPromotion e₂ c = true → forbiddenPromotion e₁ c = true := by
  cases e₁ <;> cases e₂ <;> cases c <;> decide

theorem Stratum.discharge_table_complete (e c : Stratum) :
    canDischarge e c = true ∨ forbiddenPromotion e c = true ∨ e = c := by
  cases e <;> cases c <;> decide

end PCSEpistemic
