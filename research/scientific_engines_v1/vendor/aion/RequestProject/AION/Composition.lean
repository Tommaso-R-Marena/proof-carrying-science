module

public import RequestProject.AION.Barrier

/-!
# Gluing, maximum principle, relative-error transfer, composition, robustness

* `gen_le_of_le_of_eq` : **min-gluing**.  If `g ≤ φ` everywhere and `g x = φ x`,
  then `L g x ≤ L φ x`.  This is what lets a finite-core table and an infinite-tail
  formula be glued (`g = min(core, tail)`) with only local checks.
* `hitProb_harmonic` : first-step equation for the hitting probability.
* `max_principle` : a bounded-above subsolution on an (escape-certified) region that
  is `≤ 0` outside the region is `≤ 0` everywhere.
* `relative_error_transfer` : **interface theorem**.  If `v` is harmonic on a region
  `D` and is within a factor `(1+η)` of the true hitting probability *outside* `D`
  (on the interface/tail), then it is within the same factor *inside* `D`.
  The factor does not depend on how small the probability is.
* `union_barrier` / `local_gen_bound` / `compositional_union_bound` :
  assume–guarantee composition of module-local barriers for a union of bad events,
  where cross-module coupling enters only through rate intervals that are valid on
  the good region.
* `robust_supersolution` : one barrier for a whole box of affinely-parametrised
  rate laws, checked with one inequality per state (no vertex enumeration).
-/

@[expose] public section

open scoped BigOperators
open Classical

namespace AION
namespace JumpModel

variable {S : Type*} {ι : Type*} [Fintype ι] {M : JumpModel S ι}

/-! ## Min-gluing -/

/-- If `g ≤ φ` pointwise and `g x = φ x` then `L g x ≤ L φ x`. -/
theorem gen_le_of_le_of_eq {g φ : S → ℝ} {x : S} (hle : ∀ y, g y ≤ φ y) (heq : g x = φ x) :
    M.gen g x ≤ M.gen φ x := by
  unfold gen
  refine Finset.sum_le_sum (fun r _ => mul_le_mul_of_nonneg_left ?_ (M.rate_nonneg r x))
  rw [heq]; linarith [hle (M.next r x)]

/-- Refined gluing: domination is only needed at states reachable in one jump. -/
theorem gen_le_of_le_on_jumps {g φ : S → ℝ} {x : S}
    (hle : ∀ r, M.rate r x ≠ 0 → g (M.next r x) ≤ φ (M.next r x)) (heq : g x = φ x) :
    M.gen g x ≤ M.gen φ x := by
  unfold gen
  refine Finset.sum_le_sum (fun r _ => ?_)
  by_cases h : M.rate r x = 0
  · simp [h]
  · refine mul_le_mul_of_nonneg_left ?_ (M.rate_nonneg r x)
    rw [heq]; linarith [hle r h]

/-- The pointwise minimum of two supersolutions is a supersolution. -/
theorem gen_min_nonpos {g₁ g₂ : S → ℝ} {x : S} (h₁ : M.gen g₁ x ≤ 0) (h₂ : M.gen g₂ x ≤ 0) :
    M.gen (fun y => min (g₁ y) (g₂ y)) x ≤ 0 := by
  rcases le_total (g₁ x) (g₂ x) with h | h
  · exact le_trans (gen_le_of_le_of_eq (fun y => min_le_left _ _) (min_eq_left h)) h₁
  · exact le_trans (gen_le_of_le_of_eq (fun y => min_le_right _ _) (min_eq_right h)) h₂

/-! ## Harmonicity of the hitting probability -/

lemma hitN_zero_of_empty (A : Set S) : ∀ n x, M.hitN A ∅ n x = 0
  | 0, x => by simp [hitN]
  | n + 1, x => by
      simp only [hitN, Set.mem_empty_iff_false, if_false]
      split_ifs
      · rfl
      · rfl
      · have : M.flux (M.hitN A ∅ n) x = 0 := by
          simp [flux, hitN_zero_of_empty A n]
        rw [this, zero_div]

lemma hitProb_empty (A : Set S) (x : S) : M.hitProb A ∅ x = 0 := by
  simp [hitProb, hitN_zero_of_empty]

/-- **First-step equation.** Off `A ∪ B`, with positive total rate,
`a(x) · h(x) = ∑ r, rate r x · h(next r x)`, i.e. `L h x = 0`. -/
theorem hitProb_harmonic (A B : Set S) {x : S} (hA : x ∉ A) (hB : x ∉ B)
    (hpos : 0 < M.totalRate x) : M.gen (M.hitProb A B) x = 0 := by
  have h1 : Filter.Tendsto (fun n => M.hitN A B (n + 1) x) Filter.atTop
      (nhds (M.hitProb A B x)) :=
    (tendsto_hitN A B x).comp (Filter.tendsto_add_atTop_nat 1)
  have h2 : Filter.Tendsto (fun n => M.hitN A B (n + 1) x) Filter.atTop
      (nhds (M.flux (M.hitProb A B) x / M.totalRate x)) := by
    have hf : Filter.Tendsto (fun n => M.flux (M.hitN A B n) x) Filter.atTop
        (nhds (M.flux (M.hitProb A B) x)) := by
      unfold flux
      exact tendsto_finset_sum _ (fun r _ =>
        (tendsto_hitN A B (M.next r x)).const_mul _)
    have := hf.div_const (M.totalRate x)
    refine this.congr' (Filter.Eventually.of_forall (fun n => ?_))
    simp [hitN, hA, hB, hpos.ne']
  have heq := tendsto_nhds_unique h1 h2
  rw [gen_eq_flux_sub, heq, mul_div_cancel₀ _ hpos.ne', sub_self]

/-! ## Maximum principle and relative-error transfer -/

/-- **Maximum principle** on an escape-certified region. -/
theorem max_principle {D : Set S} {w V : S → ℝ} {C : ℝ}
    (hD : ∀ x ∈ D, 0 < M.totalRate x) (hwC : ∀ x, w x ≤ C)
    (hwout : ∀ x, x ∉ D → w x ≤ 0) (hgen : ∀ x ∈ D, 0 ≤ M.gen w x)
    (hV0 : ∀ x, 0 ≤ V x) (hV : ∀ x ∈ D, M.gen V x ≤ -M.totalRate x) (x : S) : w x ≤ 0 := by
  have := le_hitProb_of_subsolution (M := M) (A := ∅) (B := ∅) (D := D) (f := w) (V := V)
    (C := C) (fun _ _ => Set.notMem_empty _) (fun _ _ => Set.notMem_empty _) hD hwC
    (fun _ h => absurd h (Set.notMem_empty _)) (fun x hx _ => hwout x hx) hgen hV0 hV x
  rwa [hitProb_empty] at this

lemma gen_sub (f g : S → ℝ) (x : S) : M.gen (fun y => f y - g y) x = M.gen f x - M.gen g x := by
  simp only [gen, ← Finset.sum_sub_distrib]
  exact Finset.sum_congr rfl (fun _ _ => by ring)

lemma gen_smul (c : ℝ) (f : S → ℝ) (x : S) : M.gen (fun y => c * f y) x = c * M.gen f x := by
  simp only [gen, Finset.mul_sum]
  exact Finset.sum_congr rfl (fun _ _ => by ring)

/-- **Relative-error transfer (upper side).**  Let `D` be a region disjoint from
`A ∪ B` from which the chain escapes (certificate `V`).  If `v` is bounded above,
harmonic on `D`, and `v ≤ (1+η)·h` outside `D` (where `h` is the true hitting
probability), then `v ≤ (1+η)·h` everywhere.  Thus the relative error of a glued
certificate is controlled by the relative error of its tail/interface data alone,
independently of how small `h` is. -/
theorem relative_error_transfer_upper {A B D : Set S} {v V : S → ℝ} {C η : ℝ}
    (hDA : ∀ x ∈ D, x ∉ A) (hDB : ∀ x ∈ D, x ∉ B) (hD : ∀ x ∈ D, 0 < M.totalRate x)
    (hη : -1 ≤ η) (hvC : ∀ x, v x ≤ C)
    (hharm : ∀ x ∈ D, M.gen v x = 0)
    (hout : ∀ x, x ∉ D → v x ≤ (1 + η) * M.hitProb A B x)
    (hV0 : ∀ x, 0 ≤ V x) (hV : ∀ x ∈ D, M.gen V x ≤ -M.totalRate x) (x : S) :
    v x ≤ (1 + η) * M.hitProb A B x := by
  have key := max_principle (M := M) (D := D) (w := fun y => v y - (1 + η) * M.hitProb A B y)
    (V := V) (C := C) hD
    (fun y => by
      have : 0 ≤ (1 + η) * M.hitProb A B y := mul_nonneg (by linarith) (hitProb_nonneg A B y)
      linarith [hvC y])
    (fun y hy => by linarith [hout y hy])
    (fun y hy => by
      rw [gen_sub, gen_smul, hitProb_harmonic A B (hDA y hy) (hDB y hy) (hD y hy), hharm y hy]
      simp)
    hV0 hV x
  simp only at key; linarith

/-- **Relative-error transfer (lower side).** -/
theorem relative_error_transfer_lower {A B D : Set S} {v V : S → ℝ} {C η : ℝ}
    (hDA : ∀ x ∈ D, x ∉ A) (hDB : ∀ x ∈ D, x ∉ B) (hD : ∀ x ∈ D, 0 < M.totalRate x)
    (hη : η ≤ 1) (hvC : ∀ x, C ≤ v x)
    (hharm : ∀ x ∈ D, M.gen v x = 0)
    (hout : ∀ x, x ∉ D → (1 - η) * M.hitProb A B x ≤ v x)
    (hV0 : ∀ x, 0 ≤ V x) (hV : ∀ x ∈ D, M.gen V x ≤ -M.totalRate x) (x : S) :
    (1 - η) * M.hitProb A B x ≤ v x := by
  have key := max_principle (M := M) (D := D) (w := fun y => (1 - η) * M.hitProb A B y - v y)
    (V := V) (C := (1 - η) - C) hD
    (fun y => by
      have : (1 - η) * M.hitProb A B y ≤ 1 - η := by
        have h1 := hitProb_le_one (M := M) A B y
        have h0 := hitProb_nonneg (M := M) A B y
        nlinarith
      linarith [hvC y])
    (fun y hy => by linarith [hout y hy])
    (fun y hy => by
      rw [gen_sub, gen_smul, hitProb_harmonic A B (hDA y hy) (hDB y hy) (hD y hy), hharm y hy]
      simp)
    hV0 hV x
  simp only at key; linarith

/-! ## Compositional (assume–guarantee) union barriers -/

/-- Union bound by additive barriers: if each `g i` is a supersolution off
`A ∪ ⋃ B j` and `g i ≥ 1` on `B i`, the sum bounds `P(reach ⋃ B i before A)`. -/
theorem union_barrier {κ : Type*} [Fintype κ] {A : Set S} {B : κ → Set S} {g : κ → S → ℝ}
    (hg0 : ∀ i x, 0 ≤ g i x) (hgB : ∀ i, ∀ x ∈ B i, 1 ≤ g i x)
    (hgen : ∀ i x, x ∉ A → x ∉ ⋃ j, B j → M.gen (g i) x ≤ 0) (x : S) :
    M.hitProb A (⋃ j, B j) x ≤ ∑ i, g i x := by
  apply hitProb_le_of_supersolution
  · intro y; exact Finset.sum_nonneg (fun i _ => hg0 i y)
  · intro y hy
    obtain ⟨i, hi⟩ := Set.mem_iUnion.mp hy
    calc (1:ℝ) ≤ g i y := hgB i y hi
      _ ≤ ∑ j, g j y := Finset.single_le_sum (fun j _ => hg0 j y) (Finset.mem_univ i)
  · intro y hA hB
    have : M.gen (fun z => ∑ i, g i z) y = ∑ i, M.gen (g i) y := by
      simp only [gen, Finset.mul_sum, ← Finset.sum_sub_distrib]
      rw [Finset.sum_comm]
    rw [this]
    exact Finset.sum_nonpos (fun i _ => hgen i y hA hB)

/-- A real number in `[lo, hi]` times `e` is at most `max (lo*e) (hi*e)`. -/
lemma mul_le_max_of_mem_Icc {θ lo hi e : ℝ} (h1 : lo ≤ θ) (h2 : θ ≤ hi) :
    θ * e ≤ max (lo * e) (hi * e) := by
  rcases le_total 0 e with he | he
  · exact le_trans (mul_le_mul_of_nonneg_right h2 he) (le_max_right _ _)
  · exact le_trans (mul_le_mul_of_nonpos_right h1 he) (le_max_left _ _)

/-- **Local generator bound.**  If `g = φ ∘ π` depends only on a module's local
coordinates, transitions act locally (`π (next r x) = nxt r (π x)`), and each rate is
known only up to an interval `[lo r (π x), hi r (π x)]` depending on local data, then
`L g x ≤ ∑ r, max (lo·Δ) (hi·Δ)`, a quantity depending on `π x` alone. -/
theorem local_gen_bound {T : Type*} (π : S → T) (nxt : ι → T → T) (φ : T → ℝ)
    (lo hi : ι → T → ℝ) {x : S} (hcomm : ∀ r, π (M.next r x) = nxt r (π x))
    (hrate : ∀ r, lo r (π x) ≤ M.rate r x ∧ M.rate r x ≤ hi r (π x)) :
    M.gen (fun y => φ (π y)) x ≤
      ∑ r, max (lo r (π x) * (φ (nxt r (π x)) - φ (π x)))
               (hi r (π x) * (φ (nxt r (π x)) - φ (π x))) := by
  unfold gen
  refine Finset.sum_le_sum (fun r _ => ?_)
  simp only
  rw [hcomm r]
  exact mul_le_max_of_mem_Icc (hrate r).1 (hrate r).2

/-- **Compositional union bound (assume–guarantee).**
Modules `i : κ` have local state spaces `T i`, projections `π i`, local bad sets
`Bl i`, and local barriers `φ i`.  Coupling with the rest of the network is modelled
by rate intervals `lo i r, hi i r` that must hold whenever the *global* state is
outside `A` and outside every module's bad set (the circular assumption is
discharged by the union target).  If each module passes its **local** check, the sum
of local barriers bounds the probability that *some* module goes bad before `A`. -/
theorem compositional_union_bound {κ : Type*} [Fintype κ] {T : κ → Type*}
    (π : ∀ i, S → T i) (nxt : ∀ i, ι → T i → T i) (φ : ∀ i, T i → ℝ)
    (lo hi : ∀ i, ι → T i → ℝ) (A : Set S) (Bl : ∀ i, Set (T i))
    (hcomm : ∀ i r x, π i (M.next r x) = nxt i r (π i x))
    (hrate : ∀ i r x, x ∉ A → (∀ j, π j x ∉ Bl j) →
        lo i r (π i x) ≤ M.rate r x ∧ M.rate r x ≤ hi i r (π i x))
    (hφ0 : ∀ i z, 0 ≤ φ i z) (hφB : ∀ i, ∀ z ∈ Bl i, 1 ≤ φ i z)
    (hlocal : ∀ i z, z ∉ Bl i →
        ∑ r, max (lo i r z * (φ i (nxt i r z) - φ i z)) (hi i r z * (φ i (nxt i r z) - φ i z))
          ≤ 0)
    (x : S) :
    M.hitProb A (⋃ i, π i ⁻¹' Bl i) x ≤ ∑ i, φ i (π i x) := by
  apply union_barrier (g := fun i y => φ i (π i y)) (B := fun i => π i ⁻¹' Bl i)
  · intro i y; exact hφ0 i _
  · intro i y hy; exact hφB i _ hy
  · intro i y hA hB
    have hgood : ∀ j, π j y ∉ Bl j := fun j hj => hB (Set.mem_iUnion.mpr ⟨j, hj⟩)
    exact le_trans (local_gen_bound (π i) (nxt i) (φ i) (lo i) (hi i) (hcomm i · y)
      (fun r => hrate i r y hA hgood)) (hlocal i _ (hgood i))

end JumpModel

/-! ## Parameter-robust barriers -/

/-- An affinely parametrised family of jump models: for parameter vector `θ : κ → ℝ`,
`rate θ r x = base r x + ∑ k, θ k * coef k r x` (all models share `next`). -/
structure AffineFamily (S : Type*) (ι : Type*) (κ : Type*) [Fintype ι] [Fintype κ] where
  base : ι → S → ℝ
  coef : κ → ι → S → ℝ
  next : ι → S → S
  /-- the parameter box -/
  lo : κ → ℝ
  hi : κ → ℝ
  /-- rates are nonnegative throughout the box -/
  rate_nonneg : ∀ θ : κ → ℝ, (∀ k, lo k ≤ θ k ∧ θ k ≤ hi k) →
    ∀ r x, 0 ≤ base r x + ∑ k, θ k * coef k r x

namespace AffineFamily

variable {S : Type*} {ι : Type*} {κ : Type*} [Fintype ι] [Fintype κ] (F : AffineFamily S ι κ)

/-- The member model at an admissible parameter. -/
noncomputable def model (θ : κ → ℝ) (hθ : ∀ k, F.lo k ≤ θ k ∧ θ k ≤ F.hi k) : JumpModel S ι where
  rate r x := F.base r x + ∑ k, θ k * F.coef k r x
  rate_nonneg := F.rate_nonneg θ hθ
  next := F.next

/-- The robust drift bound: one number per state, linear in the number of parameters. -/
noncomputable def robustDrift (g : S → ℝ) (x : S) : ℝ :=
  (∑ r, F.base r x * (g (F.next r x) - g x)) +
    ∑ k, max (F.lo k * ∑ r, F.coef k r x * (g (F.next r x) - g x))
             (F.hi k * ∑ r, F.coef k r x * (g (F.next r x) - g x))

lemma gen_le_robustDrift (g : S → ℝ) (θ : κ → ℝ) (hθ : ∀ k, F.lo k ≤ θ k ∧ θ k ≤ F.hi k)
    (x : S) : (F.model θ hθ).gen g x ≤ F.robustDrift g x := by
  have : (F.model θ hθ).gen g x = (∑ r, F.base r x * (g (F.next r x) - g x)) +
      ∑ k, θ k * ∑ r, F.coef k r x * (g (F.next r x) - g x) := by
    simp only [JumpModel.gen, model, add_mul, Finset.sum_add_distrib, Finset.sum_mul,
      Finset.mul_sum]
    congr 1
    rw [Finset.sum_comm]
    exact Finset.sum_congr rfl (fun _ _ => Finset.sum_congr rfl (fun _ _ => by ring))
  rw [this, robustDrift]
  gcongr with k
  exact JumpModel.mul_le_max_of_mem_Icc (hθ k).1 (hθ k).2

/-- **Robust barrier theorem.** One function `g` whose robust drift is nonpositive
off `A ∪ B` bounds the hitting probability for *every* parameter in the box. -/
theorem robust_supersolution {A B : Set S} {g : S → ℝ} (hg0 : ∀ x, 0 ≤ g x)
    (hgB : ∀ x ∈ B, 1 ≤ g x) (hdrift : ∀ x, x ∉ A → x ∉ B → F.robustDrift g x ≤ 0)
    (θ : κ → ℝ) (hθ : ∀ k, F.lo k ≤ θ k ∧ θ k ≤ F.hi k) (x : S) :
    (F.model θ hθ).hitProb A B x ≤ g x :=
  JumpModel.hitProb_le_of_supersolution hg0 hgB
    (fun y hA hB => le_trans (F.gen_le_robustDrift g θ hθ y) (hdrift y hA hB)) x

end AffineFamily
end AION
