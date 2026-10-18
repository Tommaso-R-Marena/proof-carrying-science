import PCS.V2.ProofGatedDeepCert

/-!
# Certificate generation, minimisation and a parameterised lower bound for deep networks

Builds on the verified cell-certificate checker `chainOK` of `ProofGatedDeepCert`.

## Untrusted generation, verified checking
* `genDeepCert f t L U fuel`: a practical **bisection generator** — try the whole interval;
  if a ReLU may bend inside, split at the midpoint and recurse (falling back to unit cells
  when the fuel is exhausted). `genDeepCert_ok`: its output is always accepted by the
  checker and ends at `U`, for every pair of networks of every depth, every interval and
  every fuel. So the generator needs no trust: the checker re-validates it, and the
  generator is moreover proved never to fail.
* `minimizeCert`: a greedy pass deleting every point whose two neighbouring cells can be
  merged. `minimizeCert_ok`: minimisation preserves validity and the right end point.

## Worst-case size: tight bounds
* `cert_length_le`: **every** valid certificate has at most `U - L` points (upper bound,
  all networks).
* `cert_length_of_full`: a valid certificate that must contain every interior integer
  has exactly `U - L` points.
* `sawNet k` (`k ≥ 1`) is the width-2 sawtooth with `k + 1` hidden layers and fold constants
  `2^(k-1), …, 2, 1` (`sawNet 5` is the earlier `saw6`). `sawNet_predict`: on
  `[-2^k, 2^k]` it computes `(|x| + 1) mod 2`. `sawNet_all_kinks`: its second difference
  is nonzero at **every** interior integer of `[-2^k, 2^k]`.
* `sawNet_cert_length` (**parameterised sawtooth lower bound**): for every `k ≥ 1` and
  every target network, every valid certificate for `sawNet k` on `[-2^k, 2^k]` has
  exactly `2^(k+1)` points. The network has `6k + 7` parameters of magnitude at most
  `2^(k-1)`, so certificate size is exponential in depth, and the trivial upper bound is
  attained.

## Positive example
* `dFull_gen`: bisection plus minimisation produces a 4-point certificate for the
  two-layer network `dFull` on `[-10^6, 10^6]` (bisection alone: 41 points), accepted by
  the checker by `genDeepCert_ok` and `minimizeCert_ok`.
-/

namespace PCS.V2.ProofGatedDeepCertGen

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedDeep
open PCS.V2.ProofGatedDeepCert
open PCS.V2.ProofGatedNoForget (SecondDiffZero)

/-! ## Chain algebra -/

theorem chainOK_append (f t : DeepNet) (xs ys : List Int) (p : Int) :
    chainOK f t p (xs ++ ys) = (chainOK f t p xs && chainOK f t (lastPt p xs) ys) := by
  induction xs generalizing p with
  | nil => simp [chainOK, lastPt]
  | cons q xs ih => simp [chainOK, lastPt, ih, Bool.and_assoc]

theorem lastPt_append (p : Int) (xs ys : List Int) :
    lastPt p (xs ++ ys) = lastPt (lastPt p xs) ys := by
  induction xs generalizing p with
  | nil => rfl
  | cons q xs ih => simp [lastPt, ih]

/-! ## The bisection generator -/

/-- Points after `p` up to and including `q` (`p < q`). -/
def genCell (f t : DeepNet) : Nat → Int → Int → List Int
  | 0, p, q => enumCert p (q - p).toNat
  | fuel + 1, p, q =>
    if cellOK f p q && cellOK t p q then [q]
    else if q - p ≤ 1 then [q]
    else genCell f t fuel p (p + (q - p) / 2) ++ genCell f t fuel (p + (q - p) / 2) q

/-- **The certificate generator** (untrusted; validated by `chainOK`). -/
def genDeepCert (f t : DeepNet) (L U : Int) (fuel : Nat) : List Int :=
  if L < U then genCell f t fuel L U else []

theorem genCell_ok (f t : DeepNet) :
    ∀ (fuel : Nat) (p q : Int), p < q →
      chainOK f t p (genCell f t fuel p q) = true ∧ lastPt p (genCell f t fuel p q) = q := by
  intro fuel
  induction fuel with
  | zero =>
    intro p q hpq
    obtain ⟨h1, h2⟩ := enumCert_ok f t (q - p).toNat p
    exact ⟨h1, by simp only [genCell]; rw [h2]; omega⟩
  | succ fuel ih =>
    intro p q hpq
    simp only [genCell]
    by_cases hc : (cellOK f p q && cellOK t p q) = true
    · simp only [hc, if_true]
      simp only [Bool.and_eq_true] at hc
      simp [chainOK, lastPt, hpq, hc.1, hc.2]
    · simp only [hc, Bool.false_eq_true, if_false]
      by_cases h1 : q - p ≤ 1
      · simp only [h1, if_true]
        have hq : q = p + 1 := by omega
        subst hq
        simp [chainOK, lastPt, cellOK_succ] <;> omega
      · simp only [h1, if_false]
        have hm1 : p < p + (q - p) / 2 := by omega
        have hm2 : p + (q - p) / 2 < q := by omega
        obtain ⟨a1, a2⟩ := ih p _ hm1
        obtain ⟨b1, b2⟩ := ih _ q hm2
        refine ⟨?_, ?_⟩
        · rw [chainOK_append, a1, a2, b1]; rfl
        · rw [lastPt_append, a2, b2]

/-- **Generator completeness**: the generated certificate is always accepted by the
verified checker and covers exactly `[L, U]`. -/
theorem genDeepCert_ok (f t : DeepNet) (L U : Int) (fuel : Nat) (h : L ≤ U) :
    chainOK f t L (genDeepCert f t L U fuel) = true ∧ lastPt L (genDeepCert f t L U fuel) = U := by
  unfold genDeepCert
  by_cases hlt : L < U
  · simp only [hlt, if_true]; exact genCell_ok f t fuel L U hlt
  · simp only [hlt, if_false]
    exact ⟨rfl, by simp only [lastPt]; omega⟩

/-- Hence the generated certificate yields the exact worst-case error on `[L, U]`. -/
theorem genDeepCert_isMax (f t : DeepNet) (L U : Int) (fuel : Nat) (h : L ≤ U) :
    (∀ x, L ≤ x → x ≤ U → derr f t x ≤ certMaxErr f t L (genDeepCert f t L U fuel)) ∧
      ∃ x, L ≤ x ∧ x ≤ U ∧ derr f t x = certMaxErr f t L (genDeepCert f t L U fuel) := by
  obtain ⟨h1, h2⟩ := genDeepCert_ok f t L U fuel h
  have := certMaxErr_isMax f t L _ h1
  rw [h2] at this
  exact this

/-! ## Minimisation -/

/-- Greedy minimisation: drop `q` whenever `[p, r]` is a valid cell for both networks. -/
def minimizeCert (f t : DeepNet) : Int → List Int → List Int
  | _, [] => []
  | _, [q] => [q]
  | p, q :: r :: rest =>
    if cellOK f p r && cellOK t p r then minimizeCert f t p (r :: rest)
    else q :: minimizeCert f t q (r :: rest)

theorem minimizeCert_ok (f t : DeepNet) (p : Int) (cert : List Int)
    (h : chainOK f t p cert = true) :
    chainOK f t p (minimizeCert f t p cert) = true ∧
      lastPt p (minimizeCert f t p cert) = lastPt p cert := by
  induction p, cert using minimizeCert.induct f t with
  | case1 p => exact ⟨rfl, rfl⟩
  | case2 p q => exact ⟨h, rfl⟩
  | case3 p q r rest hc ih =>
    obtain ⟨hpq, _, _, hr⟩ := chainOK_cons h
    obtain ⟨hqr, _, _, hrest⟩ := chainOK_cons hr
    simp only [minimizeCert, hc, if_true]
    have hc' : chainOK f t p (r :: rest) = true := by
      simp only [Bool.and_eq_true] at hc
      simp [chainOK, hc.1, hc.2, hrest, show p < r by omega]
    obtain ⟨i1, i2⟩ := ih hc'
    exact ⟨i1, by rw [i2]; rfl⟩
  | case4 p q r rest hc ih =>
    obtain ⟨hpq, hf, ht, hr⟩ := chainOK_cons h
    simp only [minimizeCert, hc, Bool.false_eq_true, if_false]
    obtain ⟨i1, i2⟩ := ih hr
    exact ⟨by simp [chainOK, hpq, hf, ht, i1], by simp only [lastPt]; exact i2⟩

theorem minimizeCert_length (f t : DeepNet) (p : Int) (cert : List Int) :
    (minimizeCert f t p cert).length ≤ cert.length := by
  induction p, cert using minimizeCert.induct f t with
  | case1 p => exact Nat.le_refl _
  | case2 p q => exact Nat.le_refl _
  | case3 p q r rest hc ih =>
    simp only [minimizeCert, hc, if_true, List.length_cons] at ih ⊢; omega
  | case4 p q r rest hc ih =>
    simp only [minimizeCert, hc, Bool.false_eq_true, if_false, List.length_cons] at ih ⊢; omega

/-! ## Size bounds -/

/-- **Upper bound**: a valid certificate never has more points than the interval length. -/
theorem cert_length_le (f t : DeepNet) :
    ∀ (rest : List Int) (p : Int), chainOK f t p rest = true →
      (rest.length : Int) ≤ lastPt p rest - p := by
  intro rest
  induction rest with
  | nil => intro p _; simp [lastPt]
  | cons q rest ih =>
    intro p h
    obtain ⟨hpq, _, _, hr⟩ := chainOK_cons h
    have := ih q hr
    simp only [List.length_cons, lastPt]
    omega

/-- A valid certificate that contains every interior integer has exactly `U - L` points. -/
theorem cert_length_of_full (f t : DeepNet) :
    ∀ (rest : List Int) (p : Int), chainOK f t p rest = true →
      (∀ z, p < z → z < lastPt p rest → z ∈ rest) →
      (rest.length : Int) = lastPt p rest - p := by
  intro rest
  induction rest with
  | nil => intro p _ _; simp [lastPt]
  | cons q rest ih =>
    intro p h hall
    obtain ⟨hpq, _, _, hr⟩ := chainOK_cons h
    have hrange := chain_in_range f t rest q hr
    have hq : q = p + 1 := by
      apply Classical.byContradiction
      intro hne
      have hmem := hall (p + 1) (by omega) (by
        have := (hrange q (by simp)).2
        simp only [lastPt]; omega)
      simp only [List.mem_cons] at hmem
      rcases hmem with h1 | h1
      · omega
      · have := (hrange (p + 1) (List.mem_cons_of_mem _ h1)).1
        omega
    have hall' : ∀ z, q < z → z < lastPt q rest → z ∈ rest := by
      intro z h1 h2
      have := hall z (by omega) (by simp only [lastPt]; exact h2)
      simp only [List.mem_cons] at this
      rcases this with h3 | h3
      · omega
      · exact h3
    have := ih q hr hall'
    simp only [List.length_cons, lastPt]
    omega

/-! ## The parameterised sawtooth -/

/-- Fold constants `2^(k-1), …, 2, 1`. -/
def sawCs : Nat → List Int
  | 0 => []
  | k + 1 => (2 ^ k : Int) :: sawCs k

/-- The width-2 sawtooth with `k + 1` hidden layers. -/
def sawNet (k : Nat) : DeepNet := sawtooth (sawCs k)

theorem saw6_eq : saw6 = sawNet 5 := by decide

def absI (z : Int) : Int := relu z + relu (-z)

theorem absI_eq (z : Int) : absI z = if 0 ≤ z then z else -z := by
  unfold absI relu
  split
  · rw [Int.max_eq_right (by omega), Int.max_eq_left (by omega)]; omega
  · rw [Int.max_eq_left (by omega), Int.max_eq_right (by omega)]; omega

def foldAbs : List Int → Int → Int
  | [], y => y
  | c :: cs, y => foldAbs cs (absI (y - c))

theorem hidden_folds (cs : List Int) (u v : Int) :
    dot [1, 1] (hiddenEval (cs.map foldLayer) [u, v]) = foldAbs cs (u + v) := by
  induction cs generalizing u v with
  | nil => simp [hiddenEval, foldAbs, dot]
  | cons c cs ih =>
    simp only [hiddenEval, foldLayer, layerEval, List.map, dot, foldAbs]
    rw [ih]
    congr 1
    unfold absI
    congr 1 <;> congr 1 <;> omega

theorem sawtooth_predict (cs : List Int) (x : Int) :
    predict (sawtooth cs) x = foldAbs cs (absI x) := by
  simp only [predict, sawtooth, hiddenEval, layerEval, List.map, dot]
  rw [hidden_folds]
  have e1 : 1 * x + 0 + 0 = x := by omega
  have e2 : -1 * x + 0 + 0 = -x := by omega
  rw [e1, e2, Int.add_zero]; rfl

theorem foldAbs_sawCs (k : Nat) (hk : 1 ≤ k) :
    ∀ y : Int, 0 ≤ y → y ≤ 2 ^ k → foldAbs (sawCs k) y = (y + 1) % 2 := by
  induction k with
  | zero => omega
  | succ k ih =>
    intro y h0 h1
    simp only [sawCs, foldAbs]
    rcases Nat.eq_zero_or_pos k with rfl | hk1
    · simp only [sawCs, foldAbs, absI_eq]
      simp only [Int.pow_succ, Int.pow_zero] at h1 ⊢
      split <;> omega
    · have hp : (2 : Int) ^ (k + 1) = 2 * 2 ^ k := by rw [Int.pow_succ]; omega
      have heven : (2 : Int) ^ k % 2 = 0 := by
        obtain ⟨j, rfl⟩ : ∃ j, k = j + 1 := ⟨k - 1, by omega⟩
        rw [Int.pow_succ]; omega
      have hpos : (0 : Int) < 2 ^ k := Int.pow_pos (by decide)
      rw [ih hk1 (absI (y - 2 ^ k)) (by rw [absI_eq]; split <;> omega)
        (by rw [absI_eq]; split <;> omega)]
      rw [absI_eq]; split <;> omega

/-- **Closed form**: on `[-2^k, 2^k]`, `sawNet k` computes `(|x| + 1) mod 2`. -/
theorem sawNet_predict (k : Nat) (hk : 1 ≤ k) (x : Int) (h1 : -(2 ^ k) ≤ x) (h2 : x ≤ 2 ^ k) :
    predict (sawNet k) x = (absI x + 1) % 2 := by
  unfold sawNet
  rw [sawtooth_predict, foldAbs_sawCs k hk _ (by rw [absI_eq]; split <;> omega)
    (by rw [absI_eq]; split <;> omega)]

/-- **Every interior integer is a kink**, for every depth. -/
theorem sawNet_all_kinks (k : Nat) (hk : 1 ≤ k) (z : Int) (h1 : -(2 ^ k) < z) (h2 : z < 2 ^ k) :
    ¬ SecondDiffZero (predict (sawNet k)) z := by
  unfold SecondDiffZero
  rw [sawNet_predict k hk (z - 1) (by omega) (by omega), sawNet_predict k hk (z + 1) (by omega)
    (by omega), sawNet_predict k hk z (by omega) (by omega)]
  simp only [absI_eq]
  split <;> split <;> split <;> omega

/-- **Parameterised sawtooth lower bound.** For every `k ≥ 1` and every target network,
every valid certificate for `sawNet k` on `[-2^k, 2^k]` has exactly `2^(k+1)` points:
the exponential lower bound and the general upper bound `cert_length_le` coincide. -/
theorem sawNet_cert_length (k : Nat) (hk : 1 ≤ k) (t : DeepNet) (rest : List Int)
    (h : chainOK (sawNet k) t (-(2 ^ k)) rest = true) (hU : lastPt (-(2 ^ k)) rest = 2 ^ k) :
    (rest.length : Int) = 2 ^ (k + 1) := by
  have hall : ∀ z, -(2 ^ k) < z → z < lastPt (-(2 ^ k)) rest → z ∈ rest := by
    intro z h1 h2
    rw [hU] at h2
    exact cert_must_contain (sawNet k) t rest _ h z h1 (by rw [hU]; exact h2)
      (sawNet_all_kinks k hk z h1 h2)
  have := cert_length_of_full (sawNet k) t rest _ h hall
  rw [this, hU, Int.pow_succ]
  omega

/-- The sawtooth family has `6k + 7` parameters: a description linear in `k` (with
magnitudes up to `2^(k-1)`), against certificates of size `2^(k+1)`. -/
def paramCount (m : DeepNet) : Nat :=
  (m.layers.map fun L => (L.map fun n => n.weights.length + 1).sum).sum +
    m.readout.weights.length + 1

theorem sawNet_paramCount (k : Nat) : paramCount (sawNet k) = 6 * k + 7 := by
  unfold paramCount sawNet sawtooth
  induction k with
  | zero => rfl
  | succ k ih =>
    simp only [sawCs, List.map_cons, List.sum_cons] at ih ⊢
    simp only [foldLayer, List.map_cons, List.map_nil, List.sum_cons, List.sum_nil,
      List.length_cons, List.length_nil] at ih ⊢
    omega

/-! ## Positive example: concise certificates -/

/-- Bisection on the two-layer `dFull` over `[-10^6, 10^6]` yields 41 points. -/
theorem dFull_gen_length : (genDeepCert dFull dZero (-1000000) 1000000 64).length = 41 := by
  decide

/-- Greedy minimisation reduces it to four points: the kinks `-2, 0, 2` and the right end. -/
theorem dFull_gen : minimizeCert dFull dZero (-1000000)
    (genDeepCert dFull dZero (-1000000) 1000000 64) = [-2, 0, 2, 1000000] := by decide

/-- The minimised certificate is valid by the general theorems (no recomputation). -/
theorem dFull_gen_checked :
    chainOK dFull dZero (-1000000) (minimizeCert dFull dZero (-1000000)
      (genDeepCert dFull dZero (-1000000) 1000000 64)) = true :=
  (minimizeCert_ok _ _ _ _ (genDeepCert_ok _ _ _ _ _ (by decide)).1).1

/-- On the sawtooth the generator necessarily returns the full enumeration (`k = 3`). -/
theorem saw3_gen_length : (genDeepCert (sawNet 3) dZero (-8) 8 64).length = 16 := by decide

end PCS.V2.ProofGatedDeepCertGen
