import PCS.V2.ProofGatedBytes
import PCS.V2.ProofGatedStrongGate

/-!
# Reference interpreter for PGSI2-WIDE byte artifacts, and machine-integer runtimes

## 1. An independent reference interpreter

`interpBytes A bs x` is a second, independently written evaluator. It does **not** build a
`WideNet`: after the ASCII check and the verified field parser (`decodeInts`), it checks
the architecture bound directly on the integer vector (`intsOK`: length and magnitude) and
evaluates by a single left-to-right pass over the triples `w, b, o` with an accumulator and
an explicit `if 0 < z then z else 0` ReLU (`tripleSum`).

`interpBytes_eq_inferBytes`: for **every** architecture bound, **every** byte string and
**every** integer input, the interpreter returns exactly what the mathematical pipeline
`inferBytes = decodeBytes ; predict` returns (including `none` on every malformed input).

## 2. Fixed-width machine arithmetic

`predictK h m x` models a runtime that stores every intermediate value in a two's
complement register of `2·h` values (`h = 2^63` for `int64`), wrapping on overflow after
every multiplication and addition.

* `predictK_eq_predict`: if `B·X + B < h` and `maxWidth·B·(B·X + B) + B < h`, then for every
  valid network and every input `|x| ≤ X` the wrapped runtime equals `predict` exactly
  (no overflow can occur);
* `int64_safe`: concrete instance — width ≤ 1024, parameters ≤ 32768 and inputs ≤ 32768
  are overflow-free in `int64`;
* `int64_mismatch`: **a configuration mismatch defeats the theorem** — a modification
  accepted by the strong gate on `[0, 2^62]`, whose exact predictions are perfect there,
  is evaluated by the `int64` runtime with error `2^64` at `x = 2^62`.

## 3. Test vectors

`vectors` is a finite list of byte strings, inputs and expected outputs covering signed
parameters, zero activations, architecture-bound edges, malformed bytes, large inputs and
hidden-unit permutations; `vectors_interp` and `vectors_infer` check them in the kernel.

A proof about Lean's interpreter does **not** certify an external runtime; see the V6
report for the obligations an external implementation must discharge.
-/

namespace PCS.V2.ProofGatedInterpreter

open PCS.V2.ProofGatedSelfImprovement (relu)
open PCS.V2.ProofGatedCodec
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedNetArtifacts
open PCS.V2.ProofGatedRobust (errAt ErrBound)
open PCS.V2.ProofGatedStrongGate

/-! ## The reference interpreter -/

def reluI (z : Int) : Int := if 0 < z then z else 0

theorem reluI_eq (z : Int) : reluI z = relu z := by
  unfold reluI relu
  split
  · rw [Int.max_eq_right (by omega)]
  · rw [Int.max_eq_left (by omega)]

/-- Single pass over `w, b, o` triples with an accumulator. -/
def tripleSum (x : Int) : Int → List Int → Option Int
  | acc, [] => some acc
  | acc, w :: b :: o :: rest => tripleSum x (acc + o * reluI (w * x + b)) rest
  | _, _ => none

/-- Architecture check directly on the integer vector `outBias, w₁, b₁, o₁, …`. -/
def intsOK (A : Arch) (zs : List Int) : Bool :=
  decide (zs.length ≤ 3 * A.maxWidth + 1) && zs.all (inRange A.bound)

/-- **The reference interpreter.** -/
def interpBytes (A : Arch) (bs : Bytes) (x : Int) : Option Int :=
  if bs.all isAsciiByte then
    match decodeInts tag (bs.map byteToChar) with
    | some (ob :: rest) => if intsOK A (ob :: rest) then tripleSum x ob rest else none
    | _ => none
  else none

theorem tripleSum_spec (x : Int) (rest : List Int) (acc : Int) :
    tripleSum x acc rest = (unitsOfInts rest).map (fun hs => acc + hiddenSum hs x) := by
  induction rest using unitsOfInts.induct generalizing acc with
  | case1 => simp [tripleSum, unitsOfInts, hiddenSum]
  | case2 w b o rest ih =>
    simp only [tripleSum, unitsOfInts, ih, Option.map_map]
    cases unitsOfInts rest with
    | none => rfl
    | some hs =>
      simp only [Option.map_some, Function.comp, hiddenSum, unitOut, reluI_eq,
        Option.some.injEq]
      omega
  | case3 zs h1 h2 =>
    cases zs with
    | nil => exact absurd rfl h1
    | cons a t =>
      cases t with
      | nil => simp [tripleSum, unitsOfInts]
      | cons b t =>
        cases t with
        | nil => simp [tripleSum, unitsOfInts]
        | cons c t => exact absurd rfl (h2 a b c t)

theorem all_flatMap_units (B : Nat) (hs : List HiddenUnit) :
    (hs.flatMap fun u => [u.w, u.b, u.out]).all (inRange B) = unitsOK B hs := by
  induction hs with
  | nil => rfl
  | cons u us ih => simp [unitsOK, unitOK, ih, Bool.and_assoc]

theorem length_flatMap_units (hs : List HiddenUnit) :
    (hs.flatMap fun u => [u.w, u.b, u.out]).length = 3 * hs.length := by
  induction hs with
  | nil => rfl
  | cons u us ih =>
    rw [List.flatMap_cons, List.length_append, ih]
    simp only [List.length_cons, List.length_nil]
    omega

theorem length_toInts (m : WideNet) : (toInts m).length = 3 * width m + 1 := by
  unfold toInts width
  rw [List.length_cons, length_flatMap_units]

theorem intsOK_toInts (A : Arch) (m : WideNet) : intsOK A (toInts m) = valid A m := by
  unfold intsOK valid
  rw [length_toInts]
  have : (toInts m).all (inRange A.bound) = (inRange A.bound m.outBias && unitsOK A.bound m.hidden) := by
    simp only [toInts, List.all_cons, all_flatMap_units]
  rw [this]
  have hd : decide (3 * width m + 1 ≤ 3 * A.maxWidth + 1) = decide (width m ≤ A.maxWidth) := by
    apply decide_eq_decide.mpr; omega
  rw [hd, Bool.and_assoc]

/-- **Interpreter equivalence**: for every architecture bound, every byte string and every
integer input, the reference interpreter agrees with `inferBytes` (decode, then `predict`). -/
theorem interpBytes_eq_inferBytes (A : Arch) (bs : Bytes) (x : Int) :
    interpBytes A bs x = inferBytes A bs x := by
  unfold interpBytes inferBytes decodeBytes
  by_cases ha : bs.all isAsciiByte = true
  · simp only [ha, if_true]
    unfold decode parseModel
    rw [String.toList_ofList]
    cases hd : decodeInts tag (bs.map byteToChar) with
    | none => simp
    | some zs =>
      cases zs with
      | nil => simp [ofInts]
      | cons ob rest =>
        simp only [Option.bind_some]
        cases hu : unitsOfInts rest with
        | none =>
          have : tripleSum x ob rest = none := by rw [tripleSum_spec, hu]; rfl
          simp [ofInts, hu, this]
        | some hs =>
          have hof : ofInts (ob :: rest) = some ⟨hs, ob⟩ := by simp [ofInts, hu]
          have hti : toInts ⟨hs, ob⟩ = ob :: rest := toInts_of_ofInts hof
          have hv : intsOK A (ob :: rest) = valid A ⟨hs, ob⟩ := by rw [← hti, intsOK_toInts]
          rw [hof, hv]
          by_cases hval : valid A ⟨hs, ob⟩ = true
          · simp only [hval, if_true, Option.map_some, tripleSum_spec, hu, predict]
            congr 1; omega
          · simp [hval]
  · simp [ha]

theorem interp_encode (A : Arch) (m : WideNet) (h : valid A m = true) (x : Int) :
    interpBytes A (encodeBytes m) x = some (predict m x) := by
  rw [interpBytes_eq_inferBytes, inferBytes_encodeBytes A m h]

/-! ## Fixed-width machine arithmetic -/

/-- Two's complement wrap into `[-h, h)`. -/
def wrap (h : Nat) (z : Int) : Int := (z + h) % (2 * (h : Int)) - h

theorem wrap_id (h : Nat) (z : Int) (hz : z.natAbs < h) : wrap h z = z := by
  unfold wrap
  have h1 : 0 ≤ z + h := by omega
  have h2 : z + h < 2 * (h : Int) := by omega
  rw [Int.emod_eq_of_lt h1 h2]; omega

def unitK (h : Nat) (x : Int) (u : HiddenUnit) : Int :=
  wrap h (u.out * reluI (wrap h (wrap h (u.w * x) + u.b)))

def sumK (h : Nat) (x : Int) : Int → List HiddenUnit → Int
  | acc, [] => acc
  | acc, u :: us => sumK h x (wrap h (acc + unitK h x u)) us

/-- A runtime with fixed-width registers, wrapping after every operation. -/
def predictK (h : Nat) (m : WideNet) (x : Int) : Int := sumK h x (wrap h m.outBias) m.hidden

theorem natAbs_reluI_le (z : Int) : (reluI z).natAbs ≤ z.natAbs := by
  unfold reluI; split <;> omega

theorem unitOut_bound (B X : Nat) (u : HiddenUnit) (hu : unitOK B u = true) (x : Int)
    (hx : x.natAbs ≤ X) :
    (u.w * x).natAbs ≤ B * X ∧ (u.w * x + u.b).natAbs ≤ B * X + B ∧
      (u.out * reluI (u.w * x + u.b)).natAbs ≤ B * (B * X + B) := by
  simp only [unitOK, inRange, Bool.and_eq_true, decide_eq_true_eq] at hu
  have hw : u.w.natAbs ≤ B := by omega
  have hb : u.b.natAbs ≤ B := by omega
  have ho : u.out.natAbs ≤ B := by omega
  have h1 : (u.w * x).natAbs ≤ B * X := by rw [Int.natAbs_mul]; exact Nat.mul_le_mul hw hx
  have h2 : (u.w * x + u.b).natAbs ≤ B * X + B :=
    Nat.le_trans (Int.natAbs_add_le _ _) (Nat.add_le_add h1 hb)
  refine ⟨h1, h2, ?_⟩
  rw [Int.natAbs_mul]
  exact Nat.mul_le_mul ho (Nat.le_trans (natAbs_reluI_le _) h2)

theorem unitK_eq (h B X : Nat) (u : HiddenUnit) (hu : unitOK B u = true) (x : Int)
    (hx : x.natAbs ≤ X) (h1 : B * X + B < h) (h2 : B * (B * X + B) < h) :
    unitK h x u = unitOut u x := by
  obtain ⟨b1, b2, b3⟩ := unitOut_bound B X u hu x hx
  unfold unitK unitOut
  rw [wrap_id h (u.w * x) (by omega), wrap_id h (u.w * x + u.b) (by omega),
    wrap_id h (u.out * reluI (u.w * x + u.b)) (by omega), reluI_eq]

theorem sumK_eq (h B X : Nat) (x : Int) (hx : x.natAbs ≤ X) (h1 : B * X + B < h) :
    ∀ (us : List HiddenUnit) (acc : Int), unitsOK B us = true →
      acc.natAbs + us.length * (B * (B * X + B)) < h →
      sumK h x acc us = acc + hiddenSum us x := by
  intro us
  induction us with
  | nil => intro acc _ _; simp [sumK, hiddenSum]
  | cons u us ih =>
    intro acc hus hlt
    simp only [unitsOK, Bool.and_eq_true] at hus
    simp only [List.length_cons, Nat.succ_mul] at hlt
    have hC : B * (B * X + B) < h := by omega
    obtain ⟨-, -, b3⟩ := unitOut_bound B X u hus.1 x hx
    have hv : (unitOut u x).natAbs ≤ B * (B * X + B) := by
      rw [unitOut, ← reluI_eq]; exact b3
    have hsum : (acc + unitOut u x).natAbs ≤ acc.natAbs + B * (B * X + B) :=
      Nat.le_trans (Int.natAbs_add_le _ _) (Nat.add_le_add_left hv _)
    simp only [sumK, unitK_eq h B X u hus.1 x hx h1 hC]
    rw [wrap_id h _ (by omega), ih _ hus.2 (by omega), hiddenSum]
    omega

/-- The sufficient no-overflow condition for an architecture and an input bound. -/
def NoOverflow (A : Arch) (X h : Nat) : Prop :=
  A.bound * X + A.bound < h ∧ A.maxWidth * (A.bound * (A.bound * X + A.bound)) + A.bound < h

/-- **Fixed-width correctness**: under `NoOverflow`, the wrapped runtime computes
`predict` exactly, for every valid network and every input `|x| ≤ X`. -/
theorem predictK_eq_predict (A : Arch) (X h : Nat) (hno : NoOverflow A X h) (m : WideNet)
    (hv : valid A m = true) (x : Int) (hx : x.natAbs ≤ X) : predictK h m x = predict m x := by
  obtain ⟨h1, h2⟩ := hno
  simp only [valid, Bool.and_eq_true, decide_eq_true_eq, inRange] at hv
  obtain ⟨⟨hw, hob⟩, hus⟩ := hv
  have hob' : m.outBias.natAbs ≤ A.bound := by omega
  have hlen : m.hidden.length * (A.bound * (A.bound * X + A.bound)) ≤
      A.maxWidth * (A.bound * (A.bound * X + A.bound)) := Nat.mul_le_mul_right _ hw
  unfold predictK predict
  rw [wrap_id h _ (by omega), sumK_eq h A.bound X x hx h1 m.hidden m.outBias hus (by omega)]
  omega

/-- `int64` registers: `h = 2^63`. -/
def int64Half : Nat := 2 ^ 63

/-- **Concrete `int64` safety**: width ≤ 1024, parameters ≤ 32768, inputs ≤ 32768. -/
theorem int64_safe (A : Arch) (hW : A.maxWidth ≤ 1024) (hB : A.bound ≤ 32768) (m : WideNet)
    (hv : valid A m = true) (x : Int) (hx : x.natAbs ≤ 32768) :
    predictK int64Half m x = predict m x := by
  apply predictK_eq_predict A 32768 int64Half _ m hv x hx
  have e1 : A.bound * 32768 ≤ 32768 * 32768 := Nat.mul_le_mul_right _ hB
  have e2 : A.bound * (A.bound * 32768 + A.bound) ≤ 32768 * (32768 * 32768 + 32768) :=
    Nat.mul_le_mul hB (by omega)
  have e3 : A.maxWidth * (A.bound * (A.bound * 32768 + A.bound)) ≤
      1024 * (32768 * (32768 * 32768 + 32768)) := Nat.mul_le_mul hW e2
  unfold int64Half
  constructor <;> omega

/-! ## A verification/inference configuration mismatch -/

def bigNet : WideNet := ⟨[⟨4, 0, 1⟩], 0⟩

/-- Verification configuration: target `bigNet`, corpus `[1]`, interval `[0, 2^62]`. -/
def bigSpec : StrongSpec := ⟨⟨1, 4⟩, bigNet, [1], 0, 2 ^ 62⟩

/-- **Mismatch counterexample.** The strong gate accepts `⟨[],0⟩ ↦ bigNet`; the accepted
network is exactly the target on all integers (error bound `0` on the interval), yet the
`int64` runtime returns `0` instead of `2^64` at `x = 2^62`, an input of the certified
interval. The exact-arithmetic theorems are not about that runtime. -/
theorem int64_mismatch :
    acceptStrong bigSpec ⟨[], 0⟩ bigNet = true ∧
    ErrBound bigNet bigSpec.target bigSpec.lo bigSpec.hi 0 ∧
    predict bigNet (2 ^ 62) = 2 ^ 64 ∧
    predictK int64Half bigNet (2 ^ 62) = 0 ∧
    bigSpec.lo ≤ 2 ^ 62 ∧ (2 ^ 62 : Int) ≤ bigSpec.hi := by
  refine ⟨by decide, fun x _ _ => by simp [errAt, bigSpec], by decide, by decide, by decide,
    by decide⟩

/-! ## Test vectors -/

structure TestVector where
  name : String
  bytes : Bytes
  x : Int
  expected : Option Int
  deriving Repr

def tv (name s : String) (x : Int) (e : Option Int) : TestVector := ⟨name, ascii s, x, e⟩

def gen3Text : String := "PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2"
def gen3Perm : String := "PGSI2-WIDE|0|1|-2|-2|2|1|1|-1|1|1"
def nineUnits : String := "PGSI2-WIDE|0" ++ String.join (List.replicate 9 "|1|0|1")

/-- The test vectors (architecture `arch3`: width ≤ 8, parameters in `[-32, 32]`). -/
def vectors : List TestVector :=
  [ tv "empty_net_const" "PGSI2-WIDE|5" 7 (some 5)
  , tv "negative_bias" "PGSI2-WIDE|-32" 0 (some (-32))
  , tv "bound_edges_pos_x" "PGSI2-WIDE|32|-32|32|-32" 1 (some 32)
  , tv "bound_edges_neg_x" "PGSI2-WIDE|32|-32|32|-32" (-1) (some (-2016))
  , tv "zero_activation" "PGSI2-WIDE|0|1|-3|5" 3 (some 0)
  , tv "just_active" "PGSI2-WIDE|0|1|-3|5" 4 (some 5)
  , tv "negative_weight_inactive" "PGSI2-WIDE|0|-1|0|7" 5 (some 0)
  , tv "negative_weight_active" "PGSI2-WIDE|0|-1|0|7" (-5) (some 35)
  , tv "gen3_x0" gen3Text 0 (some 2)
  , tv "gen3_xneg4" gen3Text (-4) (some 5)
  , tv "gen3_x4" gen3Text 4 (some 5)
  , tv "gen3_large_pos" gen3Text 1000000000000 (some 5)
  , tv "gen3_large_neg" gen3Text (-1000000000000) (some 1000000000001)
  , tv "perm_x0" gen3Perm 0 (some 2)
  , tv "perm_xneg4" gen3Perm (-4) (some 5)
  , tv "perm_large_pos" gen3Perm 1000000000000 (some 5)
  , tv "max_width_8" ("PGSI2-WIDE|0" ++ String.join (List.replicate 8 "|1|0|1")) 2 (some 16)
  , tv "over_width_9" nineUnits 2 none
  , tv "out_of_range_bias" "PGSI2-WIDE|33" 0 none
  , tv "out_of_range_out" "PGSI2-WIDE|0|1|0|-33" 0 none
  , tv "truncated_triple" "PGSI2-WIDE|0|1|2" 0 none
  , tv "leading_zero" "PGSI2-WIDE|007" 0 none
  , tv "negative_zero" "PGSI2-WIDE|-0" 0 none
  , tv "plus_sign" "PGSI2-WIDE|+1" 0 none
  , tv "trailing_pipe" "PGSI2-WIDE|0|" 0 none
  , tv "empty_field" "PGSI2-WIDE||0" 0 none
  , tv "space" "PGSI2-WIDE| 1" 0 none
  , tv "trailing_newline" "PGSI2-WIDE|0\n" 0 none
  , tv "wrong_tag" "PGSI1-WIDE|0" 0 none
  , tv "lower_case_tag" "pgsi2-wide|0" 0 none
  , tv "tag_only" "PGSI2-WIDE" 0 none
  , tv "empty" "" 0 none
  , ⟨"utf8_bom", [0xEF, 0xBB, 0xBF] ++ ascii "PGSI2-WIDE|0", 0, none⟩
  , ⟨"high_byte_digit", ascii "PGSI2-WIDE|" ++ [0xB9], 0, none⟩
  , ⟨"nul_byte", ascii "PGSI2-WIDE|0" ++ [0x00], 0, none⟩ ]

theorem vectors_count : vectors.length = 35 := by decide

/-- **All vectors pass on the reference interpreter** (kernel-checked). -/
theorem vectors_interp :
    vectors.all (fun v => interpBytes arch3 v.bytes v.x == v.expected) = true := by
  decide +kernel

/-- Hence all vectors pass on the mathematical pipeline `decodeBytes ; predict`. -/
theorem vectors_infer :
    vectors.all (fun v => inferBytes arch3 v.bytes v.x == v.expected) = true := by
  have := vectors_interp
  simpa only [interpBytes_eq_inferBytes] using this

/-- The permuted artifact agrees with `gen3` on **every** integer, by the permutation
theorem, not only on the vectors. -/
theorem perm_agrees (x : Int) :
    inferBytes arch3 (ascii gen3Perm) x = inferBytes arch3 (ascii gen3Text) x := by
  have h1 : ascii gen3Text = encodeBytes gen3 := gen3_bytes.symm
  have h2 : ascii gen3Perm = encodeBytes ⟨[uC, uA, uB], 0⟩ := by decide +kernel
  rw [h1, h2, inferBytes_encodeBytes _ _ (by decide), inferBytes_encodeBytes _ _ (by decide)]
  congr 1
  exact predict_perm (m := ⟨[uC, uA, uB], 0⟩) (m' := gen3)
    (List.perm_middle (a := uC) (l₁ := [uA, uB]) (l₂ := [])).symm rfl x

end PCS.V2.ProofGatedInterpreter
