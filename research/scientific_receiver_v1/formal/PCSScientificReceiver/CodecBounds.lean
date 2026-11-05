import PCSScientificReceiver.Codec

/-!
Arithmetic resource refinement: the protocol's operand and step limits imply
all field/byte-length requirements. No decoder-success premise is used.
-/
namespace PCSScientificReceiver

open PCS.V2.ProofGatedCodec
open PCS.V2.ProofGatedBytes (charToByte)

theorem renderNat_length_le_decimal (digits n : Nat) (positive : 0 < digits)
    (small : n < 10 ^ digits) : (renderNat n).length ≤ digits := by
  induction digits generalizing n with
  | zero => omega
  | succ digits ih =>
    rw [renderNat_step]
    by_cases hz : n / 10 = 0
    · simp [hz]
    · have hd : 0 < digits := by
        by_contra hn
        have he : digits = 0 := by omega
        subst digits
        norm_num at small
        omega
      have hdiv : n / 10 < 10 ^ digits := by
        rw [pow_succ] at small
        omega
      have hi := ih (n / 10) hd hdiv
      simp only [hz, ↓reduceIte, List.length_append, List.length_singleton]
      omega

theorem renderNat_length_bounded (n : Nat) (small : n ≤ maxOperand) :
    (renderNat n).length ≤ 19 := by
  apply renderNat_length_le_decimal 19 n (by decide)
  norm_num [maxOperand] at small ⊢
  omega

theorem renderInt_length_bounded (z : Int) (small : z.natAbs ≤ maxOperand) :
    (renderInt z).length ≤ maxFieldChars := by
  cases z with
  | ofNat n =>
    have h := renderNat_length_bounded n small
    simpa [renderInt, maxFieldChars] using Nat.le_trans h (by decide : 19 ≤ 20)
  | negSucc n =>
    have h := renderNat_length_bounded (n + 1) small
    simp only [renderInt, List.length_cons]
    unfold maxFieldChars
    omega

theorem rationalsInts_length (qs : List ℚ) :
    (rationalsInts qs).length = 2 * qs.length := by
  induction qs with
  | nil => rfl
  | cons q qs ih =>
    change (rationalInts q ++ rationalsInts qs).length = 2 * (q :: qs).length
    simp only [List.length_append, rationalInts, List.length_cons, List.length_nil] at *
    omega

theorem toInts_length (c : Contract) : (toInts c).length = 31 + 2 * c.firings.length := by
  simp [toInts, List.length_append, rationalsInts_length]
  omega

theorem joinFields_length_le (fs : List (List Char)) (limit : Nat)
    (boundedFields : ∀ f ∈ fs, f.length ≤ limit) :
    (joinFields fs).length ≤ (limit + 1) * fs.length := by
  induction fs with
  | nil => simp [joinFields]
  | cons f fs ih =>
    have hf := boundedFields f (by simp)
    cases fs with
    | nil => simp only [joinFields, List.length_cons, List.length_nil]; omega
    | cons g gs =>
      have hrest := ih (fun h hm => boundedFields h (List.mem_cons_of_mem _ hm))
      simp only [joinFields, List.length_append, List.length_cons] at *
      simp only [Nat.mul_add, Nat.mul_one] at *
      omega

/-- Rational field bounds come directly from the typed operand checks. -/
theorem rationalsInts_operands (qs : List ℚ)
    (hq : ∀ q ∈ qs, q.num.natAbs ≤ maxOperand ∧ q.den ≤ maxOperand)
    (z : Int) (hz : z ∈ rationalsInts qs) : z.natAbs ≤ maxOperand := by
  obtain ⟨q, hmem, hfield⟩ := List.mem_flatMap.mp hz
  simp only [rationalInts, List.mem_cons, List.not_mem_nil, or_false] at hfield
  rcases hfield with rfl | rfl
  · exact (hq q hmem).1
  · simpa using (hq q hmem).2

/-- Every integer field is bounded, including the fixed protocol constants,
boolean declarations, final reference and finite schedule length. -/
theorem toInts_operands (c : Contract) (hc : bounded c = true)
    (z : Int) (hz : z ∈ toInts c) : z.natAbs ≤ maxOperand := by
  have bounds := hc
  simp only [bounded, Bool.and_eq_true, decide_eq_true_eq] at bounds
  have hq : ∀ q ∈ rationals c, q.num.natAbs ≤ maxOperand ∧ q.den ≤ maxOperand := by
    simpa only [List.all_eq_true, rationalBounded, decide_eq_true_eq] using bounds.2
  have href : c.referenceStep ≤ maxOperand := by
    have hr := bounds.1.1
    norm_num [maxSteps, maxOperand] at hr ⊢
    omega
  simp only [toInts, List.mem_append] at hz
  rcases hz with ((hheader | hcore) | hcount) | hfirings
  · simp only [List.mem_cons, List.not_mem_nil, or_false] at hheader
    rcases hheader with rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl |
      rfl | rfl | rfl | rfl | rfl
    all_goals solve
      | exact href
      | norm_num [maxOperand]
      | cases c.unitCode <;> norm_num [boolInt, maxOperand]
      | cases c.physical <;> norm_num [boolInt, maxOperand]
  · apply rationalsInts_operands _ _ z hcore
    intro q hmem
    apply hq q
    exact List.mem_append_left _ hmem
  · simp only [List.mem_singleton] at hcount
    subst z
    have hn := bounds.1.2
    norm_num [maxOperand, maxSteps] at hn ⊢
    omega
  · apply rationalsInts_operands _ _ z hfirings
    intro q hmem
    apply hq q
    exact List.mem_append_right _ hmem

theorem bounded_field_lengths (c : Contract) (hc : bounded c = true) :
    ∀ f ∈ protocolTag :: (toInts c).map renderInt, f.length ≤ maxFieldChars := by
  intro f hf
  simp only [List.mem_cons, List.mem_map] at hf
  rcases hf with rfl | ⟨z, hz, rfl⟩
  · decide
  · exact renderInt_length_bounded z (toInts_operands c hc z hz)

/-- A bounded contract has at most 160 fields of at most 20 ASCII bytes each.
The bound includes an extra separator allowance, so 3360 is conservative. -/
theorem bounded_encodeBytes_length (c : Contract) (hc : bounded c = true) :
    (encodeBytes c).length ≤ 3360 := by
  have hn : c.firings.length ≤ maxSteps := by
    simp only [bounded, Bool.and_eq_true, decide_eq_true_eq] at hc
    exact hc.1.2
  have hfields := bounded_field_lengths c hc
  have hjoined := joinFields_length_le (protocolTag :: (toInts c).map renderInt)
    maxFieldChars hfields
  have hcount : (protocolTag :: (toInts c).map renderInt).length ≤ 160 := by
    simp only [List.length_cons, List.length_map, toInts_length]
    unfold maxSteps at hn
    omega
  simp only [encodeBytes, List.length_map, encodeChars, encodeInts]
  unfold maxFieldChars at hjoined
  omega

/-- Every typed contract within the declared operand/step bounds satisfies all
operational byte/field restrictions; the previous explicit premises are derived. -/
theorem bounded_operationallySupported (c : Contract) (hc : bounded c = true) :
    OperationallySupported c := by
  refine ⟨hc, ?_, bounded_field_lengths c hc⟩
  exact le_trans (bounded_encodeBytes_length c hc) (by decide : 3360 ≤ maxBytes)

/-- Full bounded-domain roundtrip, with no encoding-length or decoder premise. -/
theorem decode_encodeBytes_bounded (c : Contract) (hc : bounded c = true) :
    decode (encodeBytes c) = some c :=
  decode_encodeBytes c (bounded_operationallySupported c hc)

/-- Exact byte acceptance over the complete declared bounded typed domain. -/
theorem decode_iff_bounded (raw : List UInt8) (c : Contract) :
    decode raw = some c ↔ bounded c = true ∧ encodeBytes c = raw := by
  constructor
  · intro h
    exact ⟨decode_bounded h, decode_canonical h⟩
  · rintro ⟨hc, rfl⟩
    exact decode_encodeBytes_bounded c hc

#print axioms renderNat_length_le_decimal
#print axioms renderInt_length_bounded
#print axioms toInts_operands
#print axioms bounded_field_lengths
#print axioms bounded_encodeBytes_length
#print axioms bounded_operationallySupported
#print axioms decode_encodeBytes_bounded
#print axioms decode_iff_bounded

end PCSScientificReceiver
