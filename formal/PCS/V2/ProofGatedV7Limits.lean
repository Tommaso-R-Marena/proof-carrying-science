import PCS.V2.ProofGatedV7EndToEnd

/-!
# V7 Priority 6: limits of short no-forgetting certificates

**Probe certificates are exponentially long in the parameter bit length.** A *probe
checker* decides an update from the values of the incumbent, the candidate and the target
on a fixed finite probe set `Q` (it may be any function of those values). For the bounded
architecture `⟨3, B⟩` (width 3, parameters in `[-B, B]`), `probe_checker_needs_all_points`
proves: if a probe checker is sound and complete for universal no-forgetting on that class,
then `Q` contains **every** integer `p` with `|p| + 1 ≤ B`; hence `|Q| ≥ 2B - 1`
(`probe_checker_length`). The witness is the width-3 "bump" network that is `1` at `p` and
`0` at every other integer (`predict_bump`). Without a parameter bound no finite `Q`
suffices at all (`no_finite_probe_checker`).

By contrast the parameter-reading sweep certificate of `ProofGatedSweepCert` has one entry
per hidden unit (`genNF_length`, `sweep_steps`), independent of `B`: the reduction from
probing to reading parameters is exponential in the bit length of `B`.

Depth: `ProofGatedDeepCert.saw6_cert_contains_all` and
`ProofGatedDeepCertGen.sawNet_cert_length` (V5/V6) already show that breakpoint
certificates for deep networks can be exponentially long in the depth.

**Objective relativity** (`objective_relative`): the authority's accepted step `gen0 ↦ r1`
under the pinned policy is a strict regression for a different objective (the zero
function, which `gen0` matches everywhere). Proof-gated improvement is improvement with
respect to the *fixed pinned objective* only; nothing here measures scientific truth,
general reasoning or open-ended intelligence.
-/

namespace PCS.V2.ProofGatedV7Limits

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedPolicy

/-- The bump network at `p`: `relu(x-p+1) - 2·relu(x-p) + relu(x-p-1)`. -/
def bump (p : Int) : WideNet := ⟨[⟨1, 1 - p, 1⟩, ⟨1, -p, -2⟩, ⟨1, -p - 1, 1⟩], 0⟩

/-- The zero network. -/
def zeroNet : WideNet := ⟨[], 0⟩

theorem predict_zeroNet (x : Int) : predict zeroNet x = 0 := rfl

theorem relu_eq_self_of_nonneg {z : Int} (h : 0 ≤ z) : relu z = z := by
  simp [relu, Int.max_def]; omega

theorem relu_eq_zero_of_nonpos {z : Int} (h : z ≤ 0) : relu z = 0 := by
  simp [relu, Int.max_def]; omega

/-- The bump is `1` at `p` and `0` at every other integer. -/
theorem predict_bump (p x : Int) : predict (bump p) x = if x = p then 1 else 0 := by
  simp only [predict, bump, hiddenSum, unitOut]
  by_cases h1 : x ≤ p - 1
  · rw [relu_eq_zero_of_nonpos (by omega), relu_eq_zero_of_nonpos (by omega), relu_eq_zero_of_nonpos (by omega),
      if_neg (by omega)]; omega
  · by_cases h2 : x = p
    · subst h2
      rw [relu_eq_self_of_nonneg (by omega), relu_eq_zero_of_nonpos (by omega), relu_eq_zero_of_nonpos (by omega),
        if_pos rfl]; omega
    · rw [relu_eq_self_of_nonneg (by omega), relu_eq_self_of_nonneg (by omega), relu_eq_self_of_nonneg (by omega),
        if_neg h2]; omega

theorem bump_valid (B : Nat) (p : Int) (hB : 2 ≤ B) (hp : p.natAbs + 1 ≤ B) :
    valid ⟨3, B⟩ (bump p) = true := by
  simp only [valid, bump, width, unitsOK, unitOK, inRange, Bool.and_eq_true, decide_eq_true_eq,
    List.length_cons, List.length_nil, and_true]
  omega

theorem zeroNet_valid (A : Arch) : valid A zeroNet = true := by
  simp [valid, zeroNet, width, unitsOK, inRange]

/-- Universal no-forgetting, as a proposition. -/
def NoForget (o n t : WideNet) : Prop := ∀ x, predict o x = predict t x → predict n x = predict t x

/-- A probe checker on the probe set `Q`. -/
abbrev ProbeChecker := List Int → List Int → List Int → Bool

def vals (Q : List Int) (m : WideNet) : List Int := Q.map (predict m)

/-- Soundness of a probe checker for universal no-forgetting on the architecture `A`. -/
def ProbeSound (A : Arch) (Q : List Int) (D : ProbeChecker) : Prop :=
  ∀ o n t, valid A o = true → valid A n = true → valid A t = true →
    D (vals Q o) (vals Q n) (vals Q t) = true → NoForget o n t

/-- Completeness of a probe checker. -/
def ProbeComplete (A : Arch) (Q : List Int) (D : ProbeChecker) : Prop :=
  ∀ o n t, valid A o = true → valid A n = true → valid A t = true →
    NoForget o n t → D (vals Q o) (vals Q n) (vals Q t) = true

theorem vals_bump (Q : List Int) (p : Int) (hp : p ∉ Q) : vals Q (bump p) = vals Q zeroNet := by
  simp only [vals]
  apply List.map_congr_left
  intro q hq
  have hne : q ≠ p := by intro h; subst h; exact hp hq
  rw [predict_bump, if_neg hne]
  rfl

/-- The bump is a forgetting update of the perfect zero model towards the zero target. -/
theorem bump_forgets (p : Int) : ¬ NoForget zeroNet (bump p) zeroNet := by
  intro h
  have := h p rfl
  rw [predict_bump, if_pos rfl] at this
  cases this

/-- **Probe lower bound.** A probe checker that is sound and complete for universal
no-forgetting on width-3 networks with parameters in `[-B, B]` must probe every integer
`p` with `|p| + 1 ≤ B`. -/
theorem probe_checker_needs_all_points (B : Nat) (hB : 2 ≤ B) (Q : List Int) (D : ProbeChecker)
    (hs : ProbeSound ⟨3, B⟩ Q D) (hc : ProbeComplete ⟨3, B⟩ Q D) :
    ∀ p : Int, p.natAbs + 1 ≤ B → p ∈ Q := by
  intro p hp
  apply Classical.byContradiction
  intro hpQ
  have hz := zeroNet_valid ⟨3, B⟩
  have h0 := hc zeroNet zeroNet zeroNet hz hz hz (fun _ h => h)
  have h1 : D (vals Q zeroNet) (vals Q (bump p)) (vals Q zeroNet) = true := by
    rw [vals_bump Q p hpQ]; exact h0
  exact bump_forgets p (hs zeroNet (bump p) zeroNet hz (bump_valid B p hB hp) hz h1)

/-- Counting: a duplicate-free list contained in `l₂` is no longer than `l₂`. -/
theorem length_le_of_nodup_subset : ∀ (l₁ l₂ : List Int), l₁.Nodup → (∀ x ∈ l₁, x ∈ l₂) →
    l₁.length ≤ l₂.length
  | [], _, _, _ => Nat.zero_le _
  | a :: t, l₂, hn, hs => by
    have ha : a ∈ l₂ := hs a (List.mem_cons_self ..)
    have hn' := List.nodup_cons.mp hn
    have ht : ∀ x ∈ t, x ∈ l₂.erase a := by
      intro x hx
      have hne : x ≠ a := fun h => hn'.1 (h ▸ hx)
      exact (List.mem_erase_of_ne hne).mpr (hs x (List.mem_cons_of_mem _ hx))
    have := length_le_of_nodup_subset t (l₂.erase a) hn'.2 ht
    rw [List.length_erase_of_mem ha] at this
    have hpos : 0 < l₂.length := List.length_pos_of_mem ha
    simp only [List.length_cons]
    omega

/-- The integers `-(B-1), …, B-1`. -/
def window (B : Nat) : List Int := (List.range (2 * B - 1)).map fun i : Nat => (i : Int) - ((B : Int) - 1)

theorem window_nodup (B : Nat) : (window B).Nodup := by
  apply List.Pairwise.map _ _ List.nodup_range
  intro a b h1 h2
  apply h1
  omega

theorem window_length (B : Nat) : (window B).length = 2 * B - 1 := by
  simp [window]

theorem mem_window {B : Nat} {p : Int} (h : p ∈ window B) : p.natAbs + 1 ≤ B := by
  simp only [window, List.mem_map, List.mem_range] at h
  obtain ⟨i, hi, rfl⟩ := h
  omega

/-- **Probe certificates have size `≥ 2B - 1`**, exponential in the bit length of `B`. -/
theorem probe_checker_length (B : Nat) (hB : 2 ≤ B) (Q : List Int) (D : ProbeChecker)
    (hs : ProbeSound ⟨3, B⟩ Q D) (hc : ProbeComplete ⟨3, B⟩ Q D) : 2 * B - 1 ≤ Q.length := by
  rw [← window_length B]
  exact length_le_of_nodup_subset _ _ (window_nodup B)
    fun p hp => probe_checker_needs_all_points B hB Q D hs hc p (mem_window hp)

/-- **No finite probe set suffices without a parameter bound**: for every probe set `Q`
and every probe checker that accepts the identity update of the zero model, some
forgetting update is accepted. -/
theorem no_finite_probe_checker (Q : List Int) (D : ProbeChecker)
    (h0 : D (vals Q zeroNet) (vals Q zeroNet) (vals Q zeroNet) = true) :
    ∃ n, D (vals Q zeroNet) (vals Q n) (vals Q zeroNet) = true ∧ ¬ NoForget zeroNet n zeroNet := by
  let p : Int := (Q.map Int.natAbs).sum + 1
  have hp : p ∉ Q := by
    intro hq
    have : ∀ (l : List Int) (q : Int), q ∈ l → q.natAbs ≤ (l.map Int.natAbs).sum := by
      intro l
      induction l with
      | nil => intro q h; cases h
      | cons a l ih =>
        intro q h
        simp only [List.map_cons, List.sum_cons]
        rcases List.mem_cons.mp h with rfl | h
        · omega
        · have := ih q h; omega
    have := this Q p hq
    omega
  exact ⟨bump p, by rw [vals_bump Q p hp]; exact h0, bump_forgets p⟩

/-- The sweep certificate generated for an update has exactly one entry per hidden unit of
the incumbent, candidate and target (independent of the parameter bound). -/
theorem sweep_cert_size (a m t : WideNet) :
    (PCS.V2.ProofGatedSweepCert.genNF a m t).order.length =
      (PCS.V2.ProofGatedSweepCert.sweepUnits a m t).length :=
  PCS.V2.ProofGatedSweepCert.genNF_length a m t

/-- **Objective relativity**: the step `gen0 ↦ r1` is admissible under the pinned policy,
yet `r1` is strictly worse than `gen0` for the zero objective at `x = -1`. -/
theorem objective_relative :
    StrongAdmissible pinned0.spec gen0 r1 ∧
    predict gen0 (-1) = predict zeroNet (-1) ∧ predict r1 (-1) ≠ predict zeroNet (-1) := by
  refine ⟨(acceptStrong_iff _ _ _).mp (by decide), by decide, by decide⟩

end PCS.V2.ProofGatedV7Limits
