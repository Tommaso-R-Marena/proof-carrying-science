import PCSScientificReceiver.Types
import PCS.V2.ProofGatedCodec
import PCS.V2.ProofGatedBytes

/-!
Canonical byte codec for PCS-SCI-BOUND-V1. The reusable parser is the baseline's
proved transparent decimal/tagged-field codec. No JSON, native string rendering,
producer proofs, executable expressions or alternate versions participate.
-/
namespace PCSScientificReceiver

open PCS.V2.ProofGatedCodec
open PCS.V2.ProofGatedBytes (byteToChar charToByte isAsciiByte AsciiChars)

def protocolTag : List Char := "PCS-SCI-BOUND-V1".toList

def boolInt (b : Bool) : Int := if b then 1 else 0

def parseBool : Int → Option Bool
  | 0 => some false
  | 1 => some true
  | _ => none

def parseNatural (z : Int) : Option Nat :=
  if 0 ≤ z then some z.toNat else none

/-- Positive denominator and exact reduced representation are mandatory. -/
def parseRational (num den : Int) : Option ℚ :=
  let q : ℚ := (num : ℚ) / (den : ℚ)
  if 0 < den ∧ q.num = num ∧ (q.den : Int) = den then some q else none

def rationalInts (q : ℚ) : List Int := [q.num, (q.den : Int)]

def rationalsInts (qs : List ℚ) : List Int := qs.flatMap rationalInts

def parseRationals : List Int → Option (List ℚ)
  | [] => some []
  | num :: den :: rest => do
      let q ← parseRational num den
      let qs ← parseRationals rest
      pure (q :: qs)
  | _ => none

/-- Fixed matrix, species, weights, expression, assumptions and limitations. -/
def toInts (c : Contract) : List Int :=
  [1, 1, 0, 1, -1, 1, 1, 1, 0, (c.referenceStep : Int),
    boolInt c.unitCode, boolInt c.physical, 1, 1] ++
  rationalsInts [c.initialA, c.initialB, c.envValue, c.boxLo, c.boxHi,
    c.lower, c.upper, c.declaredTotal] ++
  [(c.firings.length : Int)] ++ rationalsInts c.firings

/-- Structural interpretation of the exact fixed field order. -/
def ofInts : List Int → Option Contract
  | 1 :: 1 :: 0 :: 1 :: (-1) :: 1 :: 1 :: 1 :: 0 :: ref :: unit :: phys ::
      1 :: 1 :: aN :: aD :: bN :: bD :: eN :: eD :: loN :: loD :: hiN :: hiD ::
      lN :: lD :: uN :: uD :: tN :: tD :: count :: fs => do
    let referenceStep ← parseNatural ref
    let unitCode ← parseBool unit
    let physical ← parseBool phys
    let initialA ← parseRational aN aD
    let initialB ← parseRational bN bD
    let envValue ← parseRational eN eD
    let boxLo ← parseRational loN loD
    let boxHi ← parseRational hiN hiD
    let lower ← parseRational lN lD
    let upper ← parseRational uN uD
    let declaredTotal ← parseRational tN tD
    let firings ← parseRationals fs
    if count = (firings.length : Int) then
      some (Contract.mk referenceStep unitCode physical initialA initialB envValue
        boxLo boxHi lower upper declaredTotal firings)
    else none
  | _ => none

def encodeChars (c : Contract) : List Char := encodeInts protocolTag (toInts c)

def encodeBytes (c : Contract) : List UInt8 := (encodeChars c).map charToByte

/-- Check resource restrictions before decimal/rational parsing. -/
def wireWithinLimits (raw : List UInt8) : Bool :=
  decide (raw.length ≤ maxBytes) && raw.all isAsciiByte &&
    (splitFields (raw.map byteToChar)).all (fun f => decide (f.length ≤ maxFieldChars))

/-- Require exact re-encoding after structural parsing. This checked guard
contains no scientific hypothesis. -/
def decode (raw : List UInt8) : Option Contract :=
  if wireWithinLimits raw then
    match decodeInts protocolTag (raw.map byteToChar) >>= ofInts with
    | none => none
    | some c => if bounded c && decide (encodeBytes c = raw) then some c else none
  else none

/-- Independent operational premises: typed operand/step bounds and encoder
byte/field lengths. No premise mentions decoder success or scientific claims.
Removing explicit length premises by decimal arithmetic is a future refinement;
these premises do not change the decoder's enforced byte acceptance policy. -/
structure OperationallySupported (c : Contract) : Prop where
  bounded : bounded c = true
  byteLength : (encodeBytes c).length ≤ maxBytes
  fieldLengths : ∀ f ∈ protocolTag :: (toInts c).map renderInt,
    f.length ≤ maxFieldChars

theorem parseBool_boolInt (b : Bool) : parseBool (boolInt b) = some b := by
  cases b <;> rfl

theorem parseNatural_nat (n : Nat) : parseNatural (n : Int) = some n := by
  simp [parseNatural]

theorem parseRational_num_den (q : ℚ) :
    parseRational q.num (q.den : Int) = some q := by
  simp [parseRational, Rat.num_div_den]

theorem parseRationals_rationalsInts (qs : List ℚ) :
    parseRationals (rationalsInts qs) = some qs := by
  induction qs with
  | nil => rfl
  | cons q qs ih =>
    change parseRationals (q.num :: (q.den : Int) :: rationalsInts qs) = some (q :: qs)
    simp [parseRationals, parseRational_num_den, ih]

/-- Structural roundtrip for every typed contract, without scientific or
operational resource assumptions. -/
theorem ofInts_toInts (c : Contract) : ofInts (toInts c) = some c := by
  cases c with
  | mk ref unit phys a b e lo hi lower upper total fs =>
    have hfs := parseRationals_rationalsInts fs
    change parseRationals (List.flatMap rationalInts fs) = some fs at hfs
    simp [toInts, rationalsInts, rationalInts, ofInts, parseNatural_nat,
      parseBool_boolInt, parseRational_num_den, hfs]

theorem protocolTag_pipe_free : '|' ∉ protocolTag := by decide

theorem protocolTag_ascii : AsciiChars protocolTag := by
  intro ch h; revert ch; decide

theorem encodeChars_ascii (c : Contract) : AsciiChars (encodeChars c) :=
  PCS.V2.ProofGatedBytes.asciiChars_encodeInts protocolTag protocolTag_ascii _

theorem encodeBytes_ascii (c : Contract) : (encodeBytes c).all isAsciiByte = true :=
  PCS.V2.ProofGatedBytes.all_ascii_map_charToByte _ (encodeChars_ascii c)

theorem encodeBytes_chars (c : Contract) :
    (encodeBytes c).map byteToChar = encodeChars c :=
  PCS.V2.ProofGatedBytes.map_byteToChar_charToByte _ (encodeChars_ascii c)

theorem wireWithinLimits_encode (c : Contract) (h : OperationallySupported c) :
    wireWithinLimits (encodeBytes c) = true := by
  simp only [wireWithinLimits, h.byteLength, decide_true, encodeBytes_ascii,
    Bool.and_self, Bool.true_and, encodeBytes_chars, encodeChars, encodeInts]
  rw [splitFields_joinFields _ (by simp)]
  · simp only [List.all_eq_true, decide_eq_true_eq]
    exact h.fieldLengths
  · intro f hf
    simp only [List.mem_cons, List.mem_map] at hf
    rcases hf with rfl | ⟨z, _, rfl⟩
    · exact protocolTag_pipe_free
    · exact pipe_not_mem_renderInt z

/-- Byte roundtrip for the entire supported typed domain. -/
theorem decode_encodeBytes (c : Contract) (h : OperationallySupported c) :
    decode (encodeBytes c) = some c := by
  simp [decode, wireWithinLimits_encode c h, encodeBytes_chars, encodeChars,
    decodeInts_encodeInts protocolTag protocolTag_pipe_free,
    ofInts_toInts, h.bounded]

/-- Successful decoding binds the object to the exact submitted bytes. -/
theorem decode_canonical {raw : List UInt8} {c : Contract}
    (h : decode raw = some c) : encodeBytes c = raw := by
  unfold decode at h
  split at h
  · split at h
    · contradiction
    · split at h
      · rename_i parsed _ hguard
        have hc : parsed = c := Option.some.inj h
        subst parsed
        simp only [Bool.and_eq_true, decide_eq_true_eq] at hguard
        exact hguard.2
      · contradiction
  · contradiction

theorem decode_bounded {raw : List UInt8} {c : Contract}
    (h : decode raw = some c) : bounded c = true := by
  unfold decode at h
  split at h
  · split at h
    · contradiction
    · split at h
      · rename_i parsed _ hguard
        have hc : parsed = c := Option.some.inj h
        subst parsed
        simp only [Bool.and_eq_true] at hguard
        exact hguard.1
      · contradiction
  · contradiction

/-- Accepted encodings for a given typed object are unique. -/
theorem decode_unique {raw raw' : List UInt8} {c : Contract}
    (h : decode raw = some c) (h' : decode raw' = some c) : raw = raw' := by
  rw [← decode_canonical h, ← decode_canonical h']

/-- The delimiter split has exactly the tag and declared integer fields. -/
theorem splitFields_encodeChars (c : Contract) :
    splitFields (encodeChars c) = protocolTag :: (toInts c).map renderInt := by
  unfold encodeChars encodeInts
  apply splitFields_joinFields _ (by simp)
  intro f hf
  simp only [List.mem_cons, List.mem_map] at hf
  rcases hf with rfl | ⟨z, _, rfl⟩
  · exact protocolTag_pipe_free
  · exact pipe_not_mem_renderInt z

theorem decode_wireWithinLimits {raw : List UInt8} {c : Contract}
    (h : decode raw = some c) : wireWithinLimits raw = true := by
  unfold decode at h
  split at h
  · assumption
  · contradiction

/-- Successful decoding preserves every structural/operational requirement. -/
theorem decode_supported {raw : List UInt8} {c : Contract}
    (h : decode raw = some c) : OperationallySupported c := by
  have hw := decode_wireWithinLimits h
  rw [← decode_canonical h] at hw
  simp only [wireWithinLimits, Bool.and_eq_true, decide_eq_true_eq,
    encodeBytes_chars, splitFields_encodeChars, List.all_eq_true] at hw
  exact ⟨decode_bounded h, hw.1.1, hw.2⟩

/-- Exact acceptance set, with no parser-success premise in the supported domain. -/
theorem decode_iff (raw : List UInt8) (c : Contract) :
    decode raw = some c ↔ OperationallySupported c ∧ encodeBytes c = raw := by
  constructor
  · intro h
    exact ⟨decode_supported h, decode_canonical h⟩
  · rintro ⟨hs, rfl⟩
    exact decode_encodeBytes c hs

/-- Distinct typed scientific contracts have distinct canonical byte encodings,
including outside the operationally supported domain. -/
theorem encodeBytes_injective {c c' : Contract}
    (h : encodeBytes c = encodeBytes c') : c = c' := by
  have hc := congrArg (List.map byteToChar) h
  rw [encodeBytes_chars, encodeBytes_chars] at hc
  have hz : toInts c = toInts c' :=
    encodeInts_injective protocolTag protocolTag_pipe_free hc
  have ho := congrArg ofInts hz
  simpa only [ofInts_toInts, Option.some.injEq] using ho

/-- Every noncanonical or unsupported byte sequence fails closed. -/
theorem decode_rejects (raw : List UInt8)
    (h : ∀ c, OperationallySupported c → encodeBytes c ≠ raw) :
    decode raw = none := by
  cases hd : decode raw with
  | none => rfl
  | some c => exact (h c (decode_supported hd) (decode_canonical hd)).elim

/-- A nontrivial one-step fixture used only to witness operational nonvacuity. -/
def codecSample : Contract where
  referenceStep := 1
  unitCode := true
  physical := true
  initialA := 1
  initialB := 0
  envValue := 2 / 3
  boxLo := 3 / 5
  boxHi := 7 / 10
  lower := 1 / 2
  upper := 3 / 4
  declaredTotal := 1
  firings := [1 / 3]

theorem codecSample_supported : OperationallySupported codecSample := by
  constructor <;> decide +kernel

theorem codecSample_roundtrip : decode (encodeBytes codecSample) = some codecSample :=
  decode_encodeBytes codecSample codecSample_supported

/-- Exact decimal fixture, without opaque runtime string rendering. -/
theorem codecSample_bytes : encodeBytes codecSample =
    PCS.V2.ProofGatedBytes.ascii
      "PCS-SCI-BOUND-V1|1|1|0|1|-1|1|1|1|0|1|1|1|1|1|1|1|0|1|2|3|3|5|7|10|1|2|3|4|1|1|1|1|3" := by
  decide +kernel

theorem codecSample_literal_decodes :
    decode (PCS.V2.ProofGatedBytes.ascii
      "PCS-SCI-BOUND-V1|1|1|0|1|-1|1|1|1|0|1|1|1|1|1|1|1|0|1|2|3|3|5|7|10|1|2|3|4|1|1|1|1|3") =
      some codecSample := by
  rw [← codecSample_bytes]
  exact codecSample_roundtrip

/-- Normalization failures reject before scientific checking. -/
theorem rational_rejection_controls :
    parseRational 2 4 = none ∧ parseRational 0 2 = none ∧
    parseRational 1 0 = none ∧ parseRational (-1) (-2) = none := by
  decide +kernel

/-- Representative failures: empty input, noncanonical decimals, wrong protocol
version and trailing separator. The general characterization covers all cases. -/
theorem malformed_examples :
    decode [] = none ∧
    decode (PCS.V2.ProofGatedBytes.ascii "PCS-SCI-BOUND-V1|00") = none ∧
    decode (PCS.V2.ProofGatedBytes.ascii "PCS-SCI-BOUND-V1|-0") = none ∧
    decode (PCS.V2.ProofGatedBytes.ascii "PCS-SCI-BOUND-V1|+1") = none ∧
    decode (PCS.V2.ProofGatedBytes.ascii "PCS-SCI-BOUND-V2|1") = none ∧
    decode (PCS.V2.ProofGatedBytes.ascii "PCS-SCI-BOUND-V1|1|") = none := by
  decide +kernel

#print axioms ofInts_toInts
#print axioms decode_encodeBytes
#print axioms decode_canonical
#print axioms decode_bounded
#print axioms decode_unique
#print axioms decode_supported
#print axioms decode_iff
#print axioms encodeBytes_injective
#print axioms decode_rejects
#print axioms codecSample_supported
#print axioms codecSample_roundtrip
#print axioms codecSample_bytes
#print axioms malformed_examples
#print axioms codecSample_literal_decodes
#print axioms rational_rejection_controls

end PCSScientificReceiver
