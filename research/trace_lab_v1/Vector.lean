import PCSReal.TransportTrace
import Transfer

/-! Lift exact two-coordinate transfers to complete finite vectors and traces.
    Rational mathematical truth only: no parser or executable refinement claim. -/
set_option autoImplicit false
namespace PCSTraceLab
open Finset PCSReal.Transport
variable {ι : Type*} [Fintype ι] [DecidableEq ι]

def shift (v x : ι → ℚ) (a b : ι) (t : ℚ) (i : ι) : ℚ :=
  if i = a then x a - t / v a else if i = b then x b + t / v b else x i

omit [Fintype ι] in
theorem at_left (v x : ι → ℚ) (a b : ι) (t : ℚ) :
    shift v x a b t a = x a - t / v a := by simp [shift]

omit [Fintype ι] in
theorem at_right (v x : ι → ℚ) (a b : ι) (t : ℚ) (hab : a ≠ b) :
    shift v x a b t b = x b + t / v b := by simp [shift, Ne.symm hab]

omit [Fintype ι] in
theorem elsewhere (v x : ι → ℚ) (a b i : ι) (t : ℚ)
    (ha : i ≠ a) (hb : i ≠ b) : shift v x a b t i = x i := by simp [shift, ha, hb]

theorem amount_shift (v x : ι → ℚ) (a b : ι) (t : ℚ)
    (hab : a ≠ b) (ha : v a ≠ 0) (hb : v b ≠ 0) :
    amount v (shift v x a b t) = amount v x := by
  have hpoint (i : ι) : v i * shift v x a b t i =
      v i * x i + (if i = a then -t else 0) + (if i = b then t else 0) := by
    by_cases hia : i = a
    · subst i
      simp [shift, hab]
      field_simp [ha]
      ring
    · by_cases hib : i = b
      · subst i
        simp [shift, Ne.symm hab]
        field_simp [hb]
      · simp [shift, hia, hib]
  simp only [amount, hpoint, sum_add_distrib]
  simp

theorem quadratic_shift (v x : ι → ℚ) (a b : ι) (t : ℚ) (hab : a ≠ b) :
    quadratic v (shift v x a b t) - quadratic v x =
      PCSFluxForge.energy (v a) (v b) (x a - t / v a) (x b + t / v b) -
        PCSFluxForge.energy (v a) (v b) (x a) (x b) := by
  have hpoint (i : ι) : v i * shift v x a b t i ^ 2 = v i * x i ^ 2 +
      (if i = a then v a * (x a - t / v a)^2 - v a * x a^2 else 0) +
      (if i = b then v b * (x b + t / v b)^2 - v b * x b^2 else 0) := by
    by_cases hia : i = a
    · subst i; simp [shift, hab]
    · by_cases hib : i = b
      · subst i; simp [shift, Ne.symm hab]
      · simp [shift, hia, hib]
  simp only [quadratic, hpoint, sum_add_distrib]
  simp
  unfold PCSFluxForge.energy
  ring

theorem energy_iff (v x : ι → ℚ) (a b : ι) (t : ℚ) (hab : a ≠ b)
    (ha : 0 < v a) (hb : 0 < v b) :
    quadratic v (shift v x a b t) ≤ quadratic v x ↔
      min 0 (PCSFluxForge.root (v a) (v b) (x a) (x b)) ≤ t ∧
      t ≤ max 0 (PCSFluxForge.root (v a) (v b) (x a) (x b)) := by
  rw [← sub_nonpos, quadratic_shift v x a b t hab, sub_nonpos]
  exact PCSFluxForge.energy_interval _ _ _ _ _ ha hb

omit [Fintype ι] in
theorem bounds_shift (v x : ι → ℚ) (a b : ι) (t lo hi : ℚ) (hab : a ≠ b)
    (hx : ∀ i, lo ≤ x i ∧ x i ≤ hi)
    (hp : (lo ≤ x a - t / v a ∧ x a - t / v a ≤ hi) ∧
      (lo ≤ x b + t / v b ∧ x b + t / v b ≤ hi)) :
    ∀ i, lo ≤ shift v x a b t i ∧ shift v x a b t i ≤ hi := by
  intro i
  by_cases hia : i = a
  · subst i; rw [at_left]; exact hp.1
  · by_cases hib : i = b
    · subst i; rw [at_right v x a b t hab]; exact hp.2
    · rw [elsewhere v x a b i t hia hib]; exact hx i

def finalShift (v : ι → ℚ) (states : Nat → ι → ℚ) (N : Nat) (a b : ι) (t : ℚ)
    (k : Nat) : ι → ℚ := if k = N then shift v (states N) a b t else states k

theorem trace_reject {n : Nat} (v : Fin n → ℚ) (p : Fin n → Fin n → ℚ)
    (initial : Fin n → ℚ) (states : Nat → Fin n → ℚ) (times : Nat → ℚ)
    (dt : ℚ) (N : Nat) (a b : Fin n) (t : ℚ) (ha : v a ≠ 0) (ht : t ≠ 0)
    (good : PCSReal.TransportTrace.check p initial states times dt N = true) :
    PCSReal.TransportTrace.check p initial (finalShift v states N a b t) times dt N = false := by
  apply Bool.eq_false_iff.mpr
  intro bad
  have hold := (PCSReal.TransportTrace.check_sound good).1 N (Nat.le_refl N) a
  have hnew := (PCSReal.TransportTrace.check_sound bad).1 N (Nat.le_refl N) a
  have heq : shift v (states N) a b t a = states N a := by
    simpa only [finalShift, if_pos rfl] using hnew.trans hold.symm
  rw [at_left] at heq
  exact PCSFluxForge.nonzero_changes _ _ _ ha ht heq

theorem feasible_shift (v x : ι → ℚ) (a b : ι) (t lo hi : ℚ) (hab : a ≠ b)
    (ha : 0 < v a) (hb : 0 < v b) (hx : ∀ i, lo ≤ x i ∧ x i ≤ hi)
    (hinterval :
      max (min 0 (PCSFluxForge.root (v a) (v b) (x a) (x b)))
        (max (v a * (x a - hi)) (v b * (lo - x b))) ≤ t ∧
      t ≤ min (max 0 (PCSFluxForge.root (v a) (v b) (x a) (x b)))
        (min (v a * (x a - lo)) (v b * (hi - x b)))) :
    amount v (shift v x a b t) = amount v x ∧
      (∀ i, lo ≤ shift v x a b t i ∧ shift v x a b t i ≤ hi) ∧
      quadratic v (shift v x a b t) ≤ quadratic v x := by
  have hp := (PCSFluxForge.feasible_interval (v a) (v b) (x a) (x b) t lo hi ha hb).mpr hinterval
  refine ⟨amount_shift v x a b t hab (ne_of_gt ha) (ne_of_gt hb),
    bounds_shift v x a b t lo hi hab hx hp.1, ?_⟩
  apply sub_nonpos.mp
  rw [quadratic_shift v x a b t hab]
  exact sub_nonpos.mpr hp.2

end PCSTraceLab
