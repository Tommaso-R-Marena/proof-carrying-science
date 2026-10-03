import Mathlib
import PCS.V2.CanonicalArchive

/-!
# Real-valued meaning of a verified PK/PD `PASS`

The PCS kernel (`PCS.V2.PKPDCheck`, no Mathlib) decides `pkpd_reference_match` with an
exact-rational certified enclosure `expEncl` of the exponential.  This file (which uses
Mathlib's real numbers and `Real.exp`) proves:

* `expEncl_sound` — `expEncl x = some (lo, hi)` implies `lo ≤ Real.exp x ≤ hi`;
* `closeEncl_real` — the endpoint test `CloseEncl` implies Python's `isclose` relation for
  **every** real value of the enclosure;
* `pkpdMatchHolds_real` — a passing `pkpd_reference_match` item means that in every row
  of the committed prediction table the reported concentration is within the declared
  tolerance of the *real* analytic value
  `C(t) = (Dose/V) · exp(-(CL/V) · t)` (SI-scaled, reported in the declared units), and,
  if a direct-Emax block is declared, the reported effect is within tolerance of
  `E(C(t)) = E0 + Emax · C / (EC50 + C)`;
* `pcs_pkpd_reference_match_real` / `pcs_canonical_archive_pkpd_real` — the same for every
  passing evidence item of a package accepted by the Lean authority (no assumption), and
  for raw canonical archive bytes.
-/

set_option autoImplicit false

namespace PCSReal.PKPD

open PCS PCS.V2 PCS.V2.PKPDCheck PCS.V2.Replay PCS.V2.Checkers PCS.V2.HighAssurance
open PCS.V2.Authority PCS.V2.EndToEnd PCS.V2.CertificateModel
open Finset

/-! ## Rational helpers -/

theorem qabs_cast (q : ℚ) : ((qabs q : ℚ) : ℝ) = |(q : ℝ)| := by
  unfold qabs
  split
  · rename_i h
    have : (q : ℝ) < 0 := by exact_mod_cast h
    rw [abs_of_neg this]; push_cast; ring
  · rename_i h
    have : (0 : ℝ) ≤ q := by exact_mod_cast (not_lt.1 h)
    rw [abs_of_nonneg this]

theorem roundDown_le (p : ℕ) (q : ℚ) : roundDown p q ≤ q := by
  unfold roundDown
  have hpos : (0 : ℚ) < ((2 ^ p : ℕ) : ℚ) := by positivity
  rw [div_le_iff₀ hpos]
  exact Rat.floor_le _

theorem le_roundUp (p : ℕ) (q : ℚ) : q ≤ roundUp p q := by
  have := roundDown_le p (-q)
  unfold roundUp; linarith

theorem fact_eq (n : ℕ) : fact n = n.factorial := by
  induction n with
  | zero => rfl
  | succ n ih => simp [fact, ih, Nat.factorial_succ]

theorem taylorSum_cast (y : ℚ) (n : ℕ) :
    ((taylorSum y n : ℚ) : ℝ) = ∑ i ∈ range n, (y : ℝ) ^ i / (i.factorial : ℝ) := by
  induction n with
  | zero => simp [taylorSum]
  | succ n ih => rw [taylorSum, sum_range_succ, ← ih, fact_eq]; push_cast; ring

theorem taylorRem_cast (y : ℚ) (n : ℕ) :
    ((taylorRem y n : ℚ) : ℝ) = |(y : ℝ)| ^ n * ((n.succ : ℝ) / ((n.factorial : ℝ) * n)) := by
  unfold taylorRem
  rw [fact_eq]; push_cast; rw [qabs_cast]

/-! ## The exponential enclosure -/

theorem squareN_sound : ∀ (k : ℕ) (lo hi : ℚ) (z : ℝ), 0 ≤ lo → (lo : ℝ) ≤ Real.exp z →
    Real.exp z ≤ hi →
    0 ≤ (squareN k (lo, hi)).1 ∧ ((squareN k (lo, hi)).1 : ℝ) ≤ Real.exp (2 ^ k * z) ∧
      Real.exp (2 ^ k * z) ≤ (squareN k (lo, hi)).2 := by
  intro k
  induction k with
  | zero => intro lo hi z h0 hlo hhi; simp only [squareN, pow_zero, one_mul]; exact ⟨h0, hlo, hhi⟩
  | succ k ih =>
    intro lo hi z h0 hlo hhi
    have he : Real.exp (2 * z) = Real.exp z * Real.exp z := by rw [two_mul, Real.exp_add]
    have hez := Real.exp_pos z
    have hlo0 : (0 : ℝ) ≤ lo := by exact_mod_cast h0
    have h1 : ((max 0 (roundDown roundBits (lo * lo)) : ℚ) : ℝ) ≤ Real.exp (2 * z) := by
      rw [he]
      have hr := roundDown_le roundBits (lo * lo)
      have hr' : ((roundDown roundBits (lo * lo) : ℚ) : ℝ) ≤ (lo : ℝ) * lo := by exact_mod_cast hr
      rw [Rat.cast_max, Rat.cast_zero]
      exact max_le (by positivity) (hr'.trans (mul_le_mul hlo hlo hlo0 hez.le))
    have h2 : Real.exp (2 * z) ≤ ((roundUp roundBits (hi * hi) : ℚ) : ℝ) := by
      rw [he]
      have hr := le_roundUp roundBits (hi * hi)
      have hr' : (hi : ℝ) * hi ≤ ((roundUp roundBits (hi * hi) : ℚ) : ℝ) := by exact_mod_cast hr
      exact (mul_le_mul hhi hhi hez.le (hez.le.trans hhi)).trans hr'
    have := ih _ _ (2 * z) (le_max_left _ _) h1 h2
    simp only [squareN]
    rw [show (2 : ℝ) ^ (k + 1) * z = 2 ^ k * (2 * z) by ring]
    exact this

theorem expEncl_sound {x lo hi : ℚ} (h : expEncl x = some (lo, hi)) :
    0 ≤ lo ∧ (lo : ℝ) ≤ Real.exp x ∧ Real.exp x ≤ hi := by
  unfold expEncl at h
  simp only at h
  split at h
  · rename_i hy
    simp only [Option.some.injEq] at h
    have hx : (2 : ℝ) ^ halvings x * ((x / ((2 ^ halvings x : ℕ) : ℚ) : ℚ) : ℝ) = x := by
      push_cast; field_simp
    generalize x / ((2 ^ halvings x : ℕ) : ℚ) = y at hy h hx
    have hy' : |(y : ℝ)| ≤ 1 := by rw [← qabs_cast]; exact_mod_cast hy
    have hb := Real.exp_bound hy' (n := taylorTerms) (by decide)
    rw [← taylorSum_cast, ← taylorRem_cast] at hb
    rw [abs_le] at hb
    have hlo0 : ((max 0 (roundDown roundBits
        (taylorSum y taylorTerms - taylorRem y taylorTerms)) : ℚ) : ℝ) ≤ Real.exp y := by
      rw [Rat.cast_max, Rat.cast_zero]
      apply max_le (Real.exp_pos _).le
      have hr := (Rat.cast_le (K := ℝ)).2
        (roundDown_le roundBits (taylorSum y taylorTerms - taylorRem y taylorTerms))
      rw [Rat.cast_sub] at hr
      linarith
    have hhi0 : Real.exp y ≤
        ((roundUp roundBits (taylorSum y taylorTerms + taylorRem y taylorTerms) : ℚ) : ℝ) := by
      have hr := (Rat.cast_le (K := ℝ)).2
        (le_roundUp roundBits (taylorSum y taylorTerms + taylorRem y taylorTerms))
      rw [Rat.cast_add] at hr
      linarith
    have hs := squareN_sound (halvings x) _ _ _ (le_max_left _ _) hlo0 hhi0
    rw [hx, h] at hs
    exact hs
  · cases h

/-! ## Tolerance -/

/-- Python `_decimal_isclose(a, v)` over the reals. -/
def IsCloseR (a v atol rtol : ℝ) : Prop := |a - v| ≤ max atol (rtol * max |a| |v|)

theorem closeEncl_real {a lo hi atol rtol : ℚ} (h : CloseEncl a lo hi atol rtol)
    (hr : 0 ≤ rtol) {v : ℝ} (hlo : (lo : ℝ) ≤ v) (hhi : v ≤ hi) :
    IsCloseR a v atol rtol := by
  obtain ⟨_, h1, h2⟩ := h
  have hM : ((minAbs lo hi : ℚ) : ℝ) ≤ |v| := by
    unfold minAbs
    split_ifs with h0 h3
    · have : (0 : ℝ) ≤ lo := by exact_mod_cast h0
      rw [abs_of_nonneg (by linarith)]; exact hlo
    · have : (hi : ℝ) ≤ 0 := by exact_mod_cast h3
      push_cast; rw [abs_of_nonpos (by linarith)]; linarith
    · simp
  have hT : ((max atol (rtol * max (qabs a) (minAbs lo hi)) : ℚ) : ℝ) ≤
      max (atol : ℝ) (rtol * max |(a : ℝ)| |v|) := by
    push_cast [qabs_cast]
    apply max_le_max le_rfl
    apply mul_le_mul_of_nonneg_left _ (by exact_mod_cast hr)
    exact max_le_max le_rfl hM
  have e1 := (Rat.cast_le (K := ℝ)).2 h1
  have e2 := (Rat.cast_le (K := ℝ)).2 h2
  rw [qabs_cast] at e1 e2
  push_cast at e1 e2 hT
  unfold IsCloseR
  rcases le_total (a : ℝ) v with hav | hav
  · calc |(a : ℝ) - v| = v - a := by rw [abs_sub_comm, abs_of_nonneg (by linarith)]
      _ ≤ hi - a := by linarith
      _ ≤ |(a : ℝ) - hi| := by rw [abs_sub_comm]; exact le_abs_self _
      _ ≤ _ := e2.trans hT
  · calc |(a : ℝ) - v| = a - v := abs_of_nonneg (by linarith)
      _ ≤ a - lo := by linarith
      _ ≤ |(a : ℝ) - lo| := le_abs_self _
      _ ≤ _ := e1.trans hT

/-! ## The analytic model over the reals -/

/-- `C(t)` in the declared concentration unit, for a time `t` in the declared time unit. -/
noncomputable def concModel (m : PKModel) (t : ℝ) : ℝ :=
  (m.c0 : ℝ) * Real.exp (-(m.kel : ℝ) * (t * m.timeScale)) / m.concScale

/-- `E(C(t))` in the declared effect unit. -/
noncomputable def effectModel (m : PKModel) (pd : PDModel) (t : ℝ) : ℝ :=
  let c : ℝ := (m.c0 : ℝ) * Real.exp (-(m.kel : ℝ) * (t * m.timeScale))
  ((pd.e0.si : ℝ) + pd.emax.si * c / (pd.ec50.si + c)) / pd.effectScale

/-- **Real-valued meaning of one passing prediction row.** -/
structure RowReal (m : PKModel) (atol rtol : ℚ) (iT iC : ℕ) (iE : Option ℕ)
    (row : List (List UInt8)) : Prop where
  values : ∃ t c, fieldQ row iT = some t ∧ fieldQ row iC = some c ∧ 0 ≤ t ∧
    IsCloseR c (concModel m t) atol rtol ∧
    (∀ pd, m.pd = some pd → ∃ i e, iE = some i ∧ fieldQ row i = some e ∧
      IsCloseR e (effectModel m pd t) atol rtol)

theorem qty_si_pos {v : Option Workflow.PVal} {e : Units.Dim} {q : Qty}
    (h : QtyDenotes v e true q) : (0 : ℝ) < (q.si : ℝ) := by
  have h1 : (0 : ℝ) < q.value := by exact_mod_cast h.positive rfl
  have h2 : (0 : ℝ) < q.scale := by exact_mod_cast h.scalePos
  unfold Qty.si; rw [Rat.cast_mul]; exact mul_pos h1 h2

/-- The direct-Emax effect is non-decreasing in the concentration. -/
theorem effect_mono {e0 emax ec50 es : ℝ} (hemax : 0 < emax) (hec : 0 < ec50) (hes : 0 < es)
    {c d : ℝ} (hc : 0 ≤ c) (hcd : c ≤ d) :
    (e0 + emax * c / (ec50 + c)) / es ≤ (e0 + emax * d / (ec50 + d)) / es := by
  apply div_le_div_of_nonneg_right _ hes.le
  have : emax * c / (ec50 + c) ≤ emax * d / (ec50 + d) := by
    rw [div_le_div_iff₀ (by linarith) (by linarith)]
    have := mul_le_mul_of_nonneg_left hcd (mul_pos hemax hec).le
    nlinarith
  linarith

theorem rowHolds_real {bm : List UInt8} {m : PKModel} (hm : ModelContract bm m) {atol rtol : ℚ}
    (hr : 0 ≤ rtol) {iT iC : ℕ} {iE : Option ℕ} {row : List (List UInt8)}
    (h : RowHolds m atol rtol iT iC iE row) : RowReal m atol rtol iT iC iE row := by
  obtain ⟨ms, _, _, hd, hv, _, _, hcu, hpdc⟩ := hm.json
  obtain ⟨t, c, lo, hi, ht, hc, h0, he, _, hcl, hpd⟩ := h.values
  obtain ⟨_, hel, heh⟩ := expEncl_sound he
  have hcs : (0 : ℝ) < m.concScale := by
    obtain ⟨_, _, _, _, _, hk⟩ := hcu; exact_mod_cast hk
  have hc0 : (0 : ℝ) ≤ (m.c0 : ℝ) := by
    unfold PKModel.c0; rw [Rat.cast_div]; exact (div_pos (qty_si_pos hd) (qty_si_pos hv)).le
  have hexpo : ((m.expo t : ℚ) : ℝ) = -(m.kel : ℝ) * ((t : ℝ) * m.timeScale) := by
    unfold PKModel.expo; push_cast; ring
  rw [hexpo] at hel heh
  refine ⟨t, c, ht, hc, h0, ?_, ?_⟩
  · apply closeEncl_real hcl hr
    · unfold concModel; push_cast
      exact div_le_div_of_nonneg_right (mul_le_mul_of_nonneg_left hel hc0) hcs.le
    · unfold concModel; push_cast
      exact div_le_div_of_nonneg_right (mul_le_mul_of_nonneg_left heh hc0) hcs.le
  · intro pd hp
    simp only [hp] at hpdc
    obtain ⟨pms, _, hpc⟩ := hpdc
    obtain ⟨i, e, hi, hfe, hce⟩ := hpd pd hp
    have hes : (0 : ℝ) < pd.effectScale := by
      obtain ⟨_, _, _, _, _, hk⟩ := hpc.effectUnit; exact_mod_cast hk
    have hemax := qty_si_pos hpc.emax
    have hec := qty_si_pos hpc.ec50
    have hlo0 : (0 : ℝ) ≤ (m.c0 : ℝ) * lo := by
      obtain ⟨hl, _, _⟩ := expEncl_sound he
      exact mul_nonneg hc0 (by exact_mod_cast hl)
    refine ⟨i, e, hi, hfe, closeEncl_real hce hr ?_ ?_⟩
    · unfold effectModel PDModel.effect; push_cast
      exact effect_mono hemax hec hes hlo0 (mul_le_mul_of_nonneg_left hel hc0)
    · unfold effectModel PDModel.effect; push_cast
      exact effect_mono hemax hec hes (mul_nonneg hc0 (Real.exp_pos _).le)
        (mul_le_mul_of_nonneg_left heh hc0)

/-- **Real-valued meaning of a passing `pkpd_reference_match` item.** -/
def PkpdMatchReal (req : ReplayRequest) : Prop :=
  ∃ sp ms bm bo m header rows iT iC,
    Chemistry.checkSpec req.evidence = some sp ∧
    Package.strField sp "type" = some "pkpd_reference_match" ∧
    matchSpec sp = some ms ∧
    Index.lookup req.artifacts ms.model = some bm ∧ Index.lookup req.artifacts ms.output = some bo ∧
    ModelContract bm.data.toList m ∧
    Csv.CsvTable bo.data.toList header rows ∧ rows ≠ [] ∧
    header[iT]? = some ms.timeCol.toUTF8.data.toList ∧
    header[iC]? = some ms.concCol.toUTF8.data.toList ∧
    ∀ row ∈ rows, RowReal m ms.absTol ms.relTol iT iC
      (Csv.indexOf ms.effectCol.toUTF8.data.toList header) row

theorem tolOf_nonneg {v : Option Json.JVal} {q : ℚ} (h : tolOf v = some q) : 0 ≤ q := by
  unfold tolOf at h
  split at h
  · split at h
    · split at h
      · cases h; assumption
      · cases h
    · cases h
  · split at h
    · cases h; exact_mod_cast ‹_›
    · cases h
  · cases h

theorem matchSpec_relTol_nonneg {sp : List (String × Json.JVal)} {ms : MatchSpec}
    (h : matchSpec sp = some ms) : 0 ≤ ms.relTol := by
  unfold matchSpec at h
  split at h
  · rename_i hrt _
    cases h; exact tolOf_nonneg hrt
  · cases h

theorem pkpdMatchHolds_real {req : ReplayRequest} (h : PkpdMatchHolds req) : PkpdMatchReal req := by
  obtain ⟨sp, ms, bm, bo, m, header, rows, iT, iC, hsp, hty, hms, hbm, hbo, hm, hcsv, hne, hT, hC,
    _, hrows⟩ := h
  exact ⟨sp, ms, bm, bo, m, header, rows, iT, iC, hsp, hty, hms, hbm, hbo, hm, hcsv, hne, hT, hC,
    fun row hrow => rowHolds_real hm (matchSpec_relTol_nonneg hms) (hrows row hrow)⟩

/-! ## End to end -/

/-- **Authoritative acceptance ⇒ real-valued PK/PD model agreement** (no assumption): every
    passing `pkpd_reference_match` evidence item of an accepted package means that the
    committed prediction table agrees, within the committed tolerance, with the real
    analytic PK/PD model of the committed model artifact. -/
theorem pcs_pkpd_reference_match_real {t : AuthorityTranscript} {T : TrustAnchor}
    {inp : Package.PackageInput} {r : AcceptedResult} (h : acceptPCSWithTranscript t T inp = some r) :
    ∀ p ∈ r.claims, ∀ ev ∈ p.2.evidence, ev.outcome = .pass →
      ∃ e ∈ r.model.evidence, e.id = ev.id ∧
        (isPkpdMatch (requestFor r.pkg.cert r.model r.table e).evidence = true →
          PkpdMatchReal (requestFor r.pkg.cert r.model r.table e)) := by
  intro p hp ev hev hpass
  obtain ⟨e, he, hid, hsem⟩ := (pcs_verified_builtin_acceptance_sound h).builtinEvidence p hp ev hev hpass
  exact ⟨e, he, hid, fun hc => pkpdMatchHolds_real (hsem.2.2.2.2 hc)⟩

/-- The same from raw canonical archive bytes decoded by the Lean authority. -/
theorem pcs_canonical_archive_pkpd_real {t : AuthorityTranscript} {T : TrustAnchor}
    {raw : ByteArray} {inp : Package.PackageInput} {r : AcceptedResult}
    (h : CanonicalArchive.acceptArchiveWithTranscript t T raw = some (inp, r)) :
    ∀ p ∈ r.claims, ∀ ev ∈ p.2.evidence, ev.outcome = .pass →
      ∃ e ∈ r.model.evidence, e.id = ev.id ∧
        (isPkpdMatch (requestFor r.pkg.cert r.model r.table e).evidence = true →
          PkpdMatchReal (requestFor r.pkg.cert r.model r.table e)) := by
  obtain ⟨_, _, _, ha⟩ := CanonicalArchive.acceptArchiveWithTranscript_spec h
  exact pcs_pkpd_reference_match_real ha

end PCSReal.PKPD
