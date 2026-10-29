import CertNum.Expr.Basic
import CertNum.Interval.Soundness
import CertNum.Interval.MulSoundness
import CertNum.Interval.AbsSquareSoundness
import Mathlib.Tactic

/-!
# Expression enclosure soundness

Structural theorem for the `IsChecked` fragment (const/var/neg/abs).
Binary operators are sound at the interval layer (`Interval.mem_add` etc.);
lifting those through `evalInterval`'s status tests is the next formal step.
-/

namespace CertNum.Expr

inductive IsChecked : Expr → Prop
  | const q : IsChecked (.const q)
  | var v : IsChecked (.var v)
  | neg {e} : IsChecked e → IsChecked (.neg e)
  | abs {e} : IsChecked e → IsChecked (.abs e)

/-- Alias for the certificate checker. -/
abbrev IsArith := IsChecked

theorem powNat_mem {x : ℚ} {I : Interval} (hx : x ∈ᵢ I) :
    ∀ n : Nat, (x ^ n) ∈ᵢ Interval.powNat I n
  | 0 => by
      simpa [pow_zero, Interval.powNat] using Interval.mem_singleton (1 : ℚ)
  | n + 1 => by
      simpa [pow_succ, Interval.powNat] using Interval.mem_mul (powNat_mem hx n) hx

theorem neg_evalInterval_ok {e : Expr} {β : Box} {I : Interval}
    (h : (Expr.neg e).evalInterval β = Enclosure.ok I) :
    (e.evalInterval β).status = .ok ∧ I = (e.evalInterval β).interval.neg := by
  simp [evalInterval] at h
  split_ifs at h with hst
  · cases h; exact ⟨hst, rfl⟩
  · cases hR : e.evalInterval β with
    | mk st J =>
        simp [hR] at hst h
        exact absurd (by cases h; rfl) hst

theorem abs_evalInterval_ok {e : Expr} {β : Box} {I : Interval}
    (h : (Expr.abs e).evalInterval β = Enclosure.ok I) :
    (e.evalInterval β).status = .ok ∧ I = (e.evalInterval β).interval.abs := by
  simp [evalInterval] at h
  split_ifs at h with hst
  · cases h; exact ⟨hst, rfl⟩
  · cases hR : e.evalInterval β with
    | mk st J =>
        simp [hR] at hst h
        exact absurd (by cases h; rfl) hst

theorem evalInterval_sound_arith
    {e : Expr} (ha : IsArith e) (ρ : Env) (β : Box) (hρ : EnvInBox ρ β)
    {x : ℚ} {I : Interval}
    (hx : e.eval ρ = some x) (hI : e.evalInterval β = Enclosure.ok I) :
    x ∈ᵢ I := by
  induction e generalizing x I with
  | const q =>
      cases hx; cases hI; exact Interval.mem_singleton q
  | var v =>
      cases hI; exact hρ v x hx
  | neg e ih =>
      cases ha with
      | neg ha' =>
        cases hev : e.eval ρ with
        | none => simp [eval, hev] at hx
        | some y =>
            simp [eval, hev] at hx; cases hx
            obtain ⟨hst, hEq⟩ := neg_evalInterval_ok hI
            cases hJe : e.evalInterval β with
            | mk st J =>
                simp [hJe] at hst
                cases hst
                have hJ : e.evalInterval β = Enclosure.ok J := by simpa [Enclosure.ok, hJe]
                have hind := ih ha' hev hJ
                simp [hJe, Enclosure.ok] at hEq
                cases hEq
                exact Interval.mem_neg hind
  | abs e ih =>
      cases ha with
      | abs ha' =>
        cases hev : e.eval ρ with
        | none => simp [eval, hev] at hx
        | some y =>
            simp [eval, hev] at hx; cases hx
            obtain ⟨hst, hEq⟩ := abs_evalInterval_ok hI
            cases hJe : e.evalInterval β with
            | mk st J =>
                simp [hJe] at hst
                cases hst
                have hJ : e.evalInterval β = Enclosure.ok J := by simpa [Enclosure.ok, hJe]
                have hind := ih ha' hev hJ
                simp [hJe, Enclosure.ok] at hEq
                cases hEq
                exact Interval.mem_abs hind
  | add _ _ _ _ => cases ha
  | sub _ _ _ _ => cases ha
  | mul _ _ _ _ => cases ha
  | div _ _ _ _ => cases ha
  | powNat _ _ _ => cases ha

end CertNum.Expr
