import PcsPccr.PolicyIdentification

/-! Policy-specific adjustment on a finite population. Binary potential response
to the policy must be independent of following the policy within each stratum.
This is a restriction on hidden response types, not an observational test. -/
namespace PcsPccr.PolicyIdentification

def stratumSize (d : List (Datum s a)) (z : Fin s) :=
  d.countP (fun r => r.stratum == z)
def followers (p : Policy s a) (d : List (Datum s a)) (z : Fin s) :=
  d.countP (fun r => r.stratum == z && aligned p r)
def followerSuccess (p : Policy s a) (d : List (Datum s a)) (z : Fin s) :=
  d.countP (fun r => r.stratum == z && aligned p r && r.outcome)

def policySuccess (p : Policy s a) (m : List (UnitModel s a)) (z : Fin s) :=
  m.countP (fun u => u.stratum == z && u.response (p u.stratum))

/-- Hidden cross-product for Y(policy) independent of the indicator of following
policy, conditional on stratum z. Empty strata satisfy the equation. -/
def balancedAt (p : Policy s a) (m : List (UnitModel s a)) (z : Fin s) : Bool :=
  let joint := m.countP (fun u => u.stratum == z && u.assigned == p u.stratum &&
    u.response (p u.stratum))
  let total := m.countP (fun u => u.stratum == z)
  let followed := m.countP (fun u => u.stratum == z && u.assigned == p u.stratum)
  joint * total == policySuccess p m z * followed

def Balanced (p : Policy s a) (m : List (UnitModel s a)) : Prop :=
  ∀ z, balancedAt p m z = true

def Positive (p : Policy s a) (d : List (Datum s a)) : Prop :=
  ∀ z, 0 < stratumSize d z → 0 < followers p d z

/-- Positive cell counts on feasible equal-weight populations make the quotient
exact. Empty strata contribute zero. -/
def adjustedAt (p : Policy s a) (d : List (Datum s a)) (z : Fin s) :=
  followerSuccess p d z * stratumSize d z / followers p d z

private theorem factual_joint (p : Policy s a) (m : List (UnitModel s a)) (z : Fin s) :
    followerSuccess p (m.map observe) z =
      m.countP (fun u => u.stratum == z && u.assigned == p u.stratum &&
        u.response (p u.stratum)) := by
  simp only [followerSuccess, List.countP_map]
  apply List.countP_congr
  intro u _
  by_cases h : u.assigned = p u.stratum <;> simp [aligned, observe, h]

theorem adjustment_at (p : Policy s a) (hm : Compatible d m)
    (hb : Balanced p m) (hp : Positive p d) (z : Fin s) :
    adjustedAt p d z = policySuccess p m z := by
  have total : stratumSize d z = m.countP (fun u => u.stratum == z) :=
    (hm.countP_eq (fun (r : Datum s a) => r.stratum == z)).symm.trans (by simp [List.countP_map, observe, Function.comp_def])
  have followed : followers p d z = m.countP (fun u => u.stratum == z && u.assigned == p u.stratum) :=
    (hm.countP_eq (fun (r : Datum s a) => r.stratum == z && aligned p r)).symm.trans (by simp [List.countP_map, aligned, observe, Function.comp_def])
  have joint := (hm.countP_eq (fun (r : Datum s a) => r.stratum == z && aligned p r && r.outcome)).symm.trans
    (factual_joint p m z)
  change followerSuccess p d z = _ at joint
  unfold adjustedAt
  by_cases ht : 0 < stratumSize d z
  · apply Nat.div_eq_of_eq_mul_left (hp z ht)
    rw [total, followed, joint]
    exact eq_of_beq (hb z)
  · have zero : stratumSize d z = 0 := by omega
    have le : policySuccess p m z ≤ m.countP (fun u => u.stratum == z) :=
      List.countP_mono_left (by intro u _ h; exact (Bool.and_eq_true_iff.mp h).1)
    rw [← total, zero] at le
    simp [zero, Nat.eq_zero_of_le_zero le]

def sumOver : (n : Nat) → (Fin n → Nat) → Nat
  | 0, _ => 0
  | n + 1, f => f 0 + sumOver n (fun i => f i.succ)

private theorem sum_add (n : Nat) (f g : Fin n → Nat) :
    sumOver n (fun i => f i + g i) = sumOver n f + sumOver n g := by
  induction n with
  | zero => rfl
  | succ n ih =>
    simp only [sumOver]
    rw [ih (fun i => f i.succ) (fun i => g i.succ)]
    omega

private theorem sum_zero (n : Nat) : sumOver n (fun _ => 0) = 0 := by
  induction n <;> simp_all [sumOver]

private theorem sum_single (n : Nat) (i : Fin n) (k : Nat) :
    sumOver n (fun j => if i = j then k else 0) = k := by
  induction n with
  | zero => exact Fin.elim0 i
  | succ n ih =>
    refine Fin.cases ?_ (fun i => ?_) i
    · simp [sumOver, sum_zero, fun j => (Fin.succ_ne_zero j).symm]
    · simp [sumOver, ih, Fin.succ_ne_zero]

theorem partition_success (p : Policy s a) (m : List (UnitModel s a)) :
    sumOver s (policySuccess p m) = value p m := by
  induction m with
  | nil => exact sum_zero s
  | cons u us ih =>
    have row : policySuccess p (u :: us) = fun z => policySuccess p us z +
        if u.stratum = z then (if u.response (p u.stratum) then 1 else 0) else 0 := by
      funext z
      by_cases h : u.stratum = z <;> simp [policySuccess, List.countP_cons, h]
    rw [row, sum_add, sum_single, ih]
    simp [value, List.countP_cons]

def adjusted (p : Policy s a) (d : List (Datum s a)) := sumOver s (adjustedAt p d)

/-- The observation-only adjustment functional recovers the structural policy
count under policy-specific exchangeability, consistency and supported strata. -/
theorem policy_adjustment (p : Policy s a) (hm : Compatible d m)
    (hb : Balanced p m) (hp : Positive p d) : adjusted p d = value p m := by
  unfold adjusted
  rw [funext (adjustment_at p hm hb hp), partition_success]

/-- Require a complete compatible model witnessing feasibility. This prevents
accepting an adjustment result vacuously when no grid population is admissible. -/
def checkAdjusted (p : Policy s a) (d : List (Datum s a)) (m : List (UnitModel s a)) (k : Nat) :=
  decide (d ≠ [] ∧ (m.map observe).Perm d ∧
    (∀ z, balancedAt p m z = true) ∧
    (∀ z, 0 < stratumSize d z → 0 < followers p d z) ∧ adjusted p d = k)

theorem adjusted_sound (h : checkAdjusted p d m k = true) :
    (∃ model, Compatible d model ∧ Balanced p model) ∧
    ∀ model, Compatible d model → Balanced p model → value p model = k := by
  obtain ⟨_, hm, hb, hp, hk⟩ := of_decide_eq_true h
  exact ⟨⟨m, hm, hb⟩, fun _ hc he => (policy_adjustment p hc he hp).symm.trans hk⟩

end PcsPccr.PolicyIdentification
