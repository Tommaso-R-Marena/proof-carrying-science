import CertNum.Expr.Soundness
import Mathlib.Tactic

/-!
# Minimal Lean checker for interval-enclosure certificates
-/

namespace CertNum.Certificate

open CertNum.Expr

structure IntervalEnclosureCert where
  expr : Expr
  arith : IsArith expr
  box : List (String × Interval)
  claimed : Interval

def lookupBox : List (String × Interval) → String → Interval
  | [], _ => .empty
  | (w, I) :: rest, v => if w = v then I else lookupBox rest v

def toBox (box : List (String × Interval)) : Box := fun v => lookupBox box v

def checkIntervalEnclosure (c : IntervalEnclosureCert) : Bool :=
  match c.expr.evalInterval (toBox c.box) with
  | ⟨.ok, I⟩ =>
      match I, c.claimed with
      | .empty, _ => true
      | .nonempty lo hi _, .nonempty clo chi _ => decide (clo ≤ lo ∧ hi ≤ chi)
      | .nonempty _ _ _, .empty => false
  | _ => false

theorem subset_of_endpoints {lo hi clo chi : ℚ}
    (hlo : clo ≤ lo) (hhi : hi ≤ chi) (wf : lo ≤ hi) (cwf : clo ≤ chi) :
    Interval.Subset (.nonempty lo hi wf) (.nonempty clo chi cwf) := by
  intro x hx
  obtain ⟨hx1, hx2⟩ := hx
  exact ⟨le_trans hlo hx1, le_trans hx2 hhi⟩

theorem checkIntervalEnclosure_sound
    (c : IntervalEnclosureCert)
    (hacc : checkIntervalEnclosure c = true)
    (ρ : Env) (hρ : EnvInBox ρ (toBox c.box))
    {x : ℚ} (hx : c.expr.eval ρ = some x) :
    x ∈ᵢ c.claimed := by
  unfold checkIntervalEnclosure at hacc
  cases he : c.expr.evalInterval (toBox c.box) with
  | mk st I =>
      simp [he] at hacc
      split at hacc
      · next hst =>
          cases hst
          have hOk : c.expr.evalInterval (toBox c.box) = Enclosure.ok I := by
            simpa [Enclosure.ok] using he
          have hin := evalInterval_sound_arith c.arith ρ (toBox c.box) hρ hx hOk
          cases I with
          | empty => cases hin
          | nonempty lo hi wf =>
              cases hc : c.claimed with
              | empty => simp [hc] at hacc
              | nonempty clo chi cwf =>
                  simp [hc, decide_eq_true_eq] at hacc
                  obtain ⟨h1, h2⟩ := hacc
                  exact subset_of_endpoints h1 h2 wf cwf x hin
      · cases hacc

end CertNum.Certificate
