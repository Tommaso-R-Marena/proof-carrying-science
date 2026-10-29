import PCS.V2.ProofGatedCodec
import PCS.V2.ProofGatedInference

/-!
# Priority A for the legacy `PGSI1` codec: what is provable, and why

**Status update.** `ProofGatedArtifacts.encode` / `parseComponents` now use the verified
renderer and parser from `ProofGatedCodec` (same bytes), and the target statement

  `theorem decode_encode_of_bounded (m : Neuron) (h : valid m = true) :`
  `    decode (encode m) = some m`

is proved there **unconditionally** (`ProofGatedArtifacts.decode_encode_of_bounded`).
The original core-`toString`/`toInt?` definitions are kept as `encodeLegacy`,
`parseComponentsLegacy` and `decodeLegacy`; this module records why the roundtrip could
not be proved for them, and proves byte compatibility of the two encoders
(`encode_eq_encodeLegacy_of_nonneg`, `encode_eq_encodeLegacy_of_append_spec`).

## Finding 1 — an obstruction in Lean core (not in the model)

`encodeLegacy` renders integers with core `toString`. For negative integers Lean 4.28 defines

  `toString (Int.negSucc n) = String.Internal.append "-" (toString (n+1))`

(`ProofGatedCodec.toString_negSucc_def`, proved by `rfl`), and
`String.Internal.append` is declared `opaque` (natively implemented by
`lean_string_append`). The kernel never unfolds an opaque constant and no theorem in the
library constrains it, so from the definitions alone nothing can be derived about the
characters of `toString (-1 : Int)`. In particular the target statement for any neuron
with a negative weight or bias cannot be derived from the definitions alone. As far
as the definitions go, the opaque constant could be any function of its type. This is a
limitation of the *specification artifact*, not of the network: the PGSI2 codec
(`ProofGatedCodec`, `ProofGatedNetArtifacts`) avoids it.

In addition, core `String.toInt?` is implemented with the `Std.Iter` iterator framework
over `String.Slice`; kernel reduction gets stuck on it (even `"27".toInt? = some 27` is
not closed by `decide +kernel`) and the library contains no lemma relating
`Slice.chars` to `String.toList`. A proof that it inverts `toString` is therefore an open
library-level obligation; we isolate it as an explicit hypothesis.

## What is proved here, with no hypotheses

* `splitOn_pipe`: for **every** string `s`, core `s.splitOn "|"` equals the verified
  list-level splitter `splitFields` (a general theorem about Lean core's legacy
  `String.splitOnAux`, by well-founded induction over UTF-8 byte positions);
* `encode_splitOn`: the exact field decomposition of `encodeLegacy m`;
* `parseComponentsLegacy_encodeLegacy`: field-level roundtrip given only the integer contract;
* `encode_injective_nonneg`: `encodeLegacy` is injective on neurons with nonnegative
  parameters (unconditionally);
* soundness never depended on these facts: `decodeLegacy` re-checks canonicity, so it is
  fail-closed whatever the opaque primitive does (`decode_sound_unconditional`).

## What is proved under explicit, ordinary hypotheses

* `decode_encode_of_bounded_of_core` — the target statement — assuming
  `CoreIntContract` (core `toString` / `toInt?` are inverse and `|`-free on `[-32,32]`);
* `coreIntContract_of`: `CoreIntContract` follows from (i) the runtime behaviour of the
  opaque append on the prefix `"-"` and (ii) a statement about core `toInt?` on the
  transparent canonical renderings only;
* `encode_injective_of_bounded_of_core`;
* `decode_encodeLegacy_of_append_spec`: legacy-written artifacts are accepted by the
  verified decoder, assuming only the runtime behaviour of the opaque append.
-/

namespace PCS.V2.ProofGatedV1Analysis

open PCS.V2.ProofGatedCodec

def bsz : List Char → Nat
  | [] => 0
  | c :: cs => c.utf8Size + bsz cs

theorem bsz_append (a b : List Char) : bsz (a ++ b) = bsz a + bsz b := by
  induction a with
  | nil => simp [bsz]
  | cons c cs ih => simp [bsz, ih, Nat.add_assoc]

theorem utf8ByteSize_ofList (l : List Char) : (String.ofList l).utf8ByteSize = bsz l := by
  induction l with
  | nil => rfl
  | cons c cs ih =>
      have : String.ofList (c :: cs) = String.ofList [c] ++ String.ofList cs := by
        rw [← String.ofList_append]; rfl
      rw [this, String.utf8ByteSize_append, ← String.singleton_eq_ofList,
        String.utf8ByteSize_singleton, ih]
      rfl

theorem utf8GetAux_at (A : List Char) (c : Char) (C : List Char) (k : Nat) :
    String.Pos.Raw.utf8GetAux (A ++ c :: C) ⟨k⟩ ⟨k + bsz A⟩ = c := by
  induction A generalizing k with
  | nil => simp [String.Pos.Raw.utf8GetAux, bsz]
  | cons a as ih =>
      have hpos := Char.utf8Size_pos a
      simp only [List.cons_append, String.Pos.Raw.utf8GetAux]
      have hne : (⟨k⟩ : String.Pos.Raw) ≠ ⟨k + bsz (a :: as)⟩ := by
        intro h; simp [bsz] at h; omega
      rw [if_neg hne]
      have : (⟨k⟩ : String.Pos.Raw) + a = ⟨k + a.utf8Size⟩ := rfl
      rw [this]
      have h2 : (⟨k + bsz (a :: as)⟩ : String.Pos.Raw) = ⟨k + a.utf8Size + bsz as⟩ := by
        simp [bsz, Nat.add_assoc]
      rw [h2]
      exact ih _

theorem extract_go₂ (B C : List Char) (k : Nat) :
    String.Pos.Raw.extract.go₂ (B ++ C) ⟨k⟩ ⟨k + bsz B⟩ = B := by
  induction B generalizing k with
  | nil =>
      cases C with
      | nil => rfl
      | cons c cs => simp [String.Pos.Raw.extract.go₂, bsz]
  | cons b bs ih =>
      have hpos := Char.utf8Size_pos b
      simp only [List.cons_append, String.Pos.Raw.extract.go₂]
      have hne : (⟨k⟩ : String.Pos.Raw) ≠ ⟨k + bsz (b :: bs)⟩ := by
        intro h; simp [bsz] at h; omega
      rw [if_neg hne]
      have : (⟨k⟩ : String.Pos.Raw) + b = ⟨k + b.utf8Size⟩ := rfl
      rw [this]
      have h2 : (⟨k + bsz (b :: bs)⟩ : String.Pos.Raw) = ⟨k + b.utf8Size + bsz bs⟩ := by
        simp [bsz, Nat.add_assoc]
      rw [h2, ih]

theorem extract_go₁ (A R : List Char) (k : Nat) (e : String.Pos.Raw) :
    String.Pos.Raw.extract.go₁ (A ++ R) ⟨k⟩ ⟨k + bsz A⟩ e =
      String.Pos.Raw.extract.go₂ R ⟨k + bsz A⟩ e := by
  induction A generalizing k with
  | nil =>
      cases R with
      | nil => rfl
      | cons r rs => simp [String.Pos.Raw.extract.go₁, bsz]
  | cons a as ih =>
      have hpos := Char.utf8Size_pos a
      simp only [List.cons_append, String.Pos.Raw.extract.go₁]
      have hne : (⟨k⟩ : String.Pos.Raw) ≠ ⟨k + bsz (a :: as)⟩ := by
        intro h; simp [bsz] at h; omega
      rw [if_neg hne]
      have : (⟨k⟩ : String.Pos.Raw) + a = ⟨k + a.utf8Size⟩ := rfl
      rw [this]
      have h2 : (⟨k + bsz (a :: as)⟩ : String.Pos.Raw) = ⟨k + a.utf8Size + bsz as⟩ := by
        simp [bsz, Nat.add_assoc]
      rw [h2, ih]

theorem extract_mid (A B C : List Char) :
    String.Pos.Raw.extract (String.ofList (A ++ B ++ C)) ⟨bsz A⟩ ⟨bsz A + bsz B⟩ =
      String.ofList B := by
  unfold String.Pos.Raw.extract
  by_cases hB : B = []
  · subst hB; simp [bsz]
  · have hpos : 0 < bsz B := by
      cases B with
      | nil => exact absurd rfl hB
      | cons b bs => have := Char.utf8Size_pos b; simp [bsz]; omega
    have hlt : ¬ (bsz A ≥ bsz A + bsz B) := by omega
    simp only [hlt, if_false, String.toList_ofList]
    rw [List.append_assoc]
    have := extract_go₁ A (B ++ C) 0 ⟨bsz A + bsz B⟩
    simp only [Nat.zero_add] at this
    rw [show (0 : String.Pos.Raw) = ⟨0⟩ from rfl, this, extract_go₂]


def prefixField (B : List Char) (fs : List (List Char)) : List (List Char) :=
  match fs with
  | g :: gs => (B ++ g) :: gs
  | [] => [B]

theorem splitOnAux_pipe (C A B : List Char) (hB : '|' ∉ B) (r : List String) :
    String.splitOnAux (String.ofList (A ++ B ++ C)) "|" ⟨bsz A⟩ ⟨bsz A + bsz B⟩ 0 r =
      r.reverse ++ (prefixField B (splitFields C)).map String.ofList := by
  induction C generalizing A B r with
  | nil =>
      rw [String.splitOnAux]
      have hend : String.Pos.Raw.atEnd (String.ofList (A ++ B ++ [])) ⟨bsz A + bsz B⟩ = true := by
        simp [String.Pos.Raw.atEnd, utf8ByteSize_ofList]
      rw [if_pos hend]
      have := extract_mid A B []
      rw [this]
      simp only [splitFields, prefixField, List.append_nil, List.map_cons, List.map_nil,
        List.reverse_cons]
  | cons c C ih =>
      rw [String.splitOnAux]
      have hpos := Char.utf8Size_pos c
      have hend : String.Pos.Raw.atEnd (String.ofList (A ++ B ++ c :: C)) ⟨bsz A + bsz B⟩ = false := by
        simp [String.Pos.Raw.atEnd, utf8ByteSize_ofList, bsz]
        omega
      rw [if_neg (by rw [hend]; exact Bool.false_ne_true)]
      have hget : String.Pos.Raw.get (String.ofList (A ++ B ++ c :: C)) ⟨bsz A + bsz B⟩ = c := by
        unfold String.Pos.Raw.get
        rw [String.toList_ofList, List.append_assoc]
        have := utf8GetAux_at (A ++ B) c C 0
        simp only [Nat.zero_add, bsz_append, List.append_assoc] at this
        exact this
      have hsep : String.Pos.Raw.get "|" 0 = '|' := by decide +kernel
      rw [hget, hsep]
      by_cases hc : c = '|'
      · subst hc
        simp only [beq_self_eq_true, if_true]
        have hj : String.Pos.Raw.next "|" 0 = ⟨1⟩ := by decide +kernel
        have hjend : String.Pos.Raw.atEnd "|" ⟨1⟩ = true := by decide +kernel
        rw [hj, if_pos hjend]
        have hnext : String.Pos.Raw.next (String.ofList (A ++ B ++ '|' :: C)) ⟨bsz A + bsz B⟩ =
            ⟨bsz (A ++ B ++ ['|'])⟩ := by
          unfold String.Pos.Raw.next
          rw [hget]
          simp only [bsz_append, bsz]
          rfl
        have hun : (⟨bsz (A ++ B ++ ['|'])⟩ : String.Pos.Raw).unoffsetBy ⟨1⟩ =
            ⟨bsz A + bsz B⟩ := by
          simp only [String.Pos.Raw.unoffsetBy, bsz_append, bsz]
          congr 1
        rw [hnext, hun, extract_mid A B ('|' :: C)]
        have hs : String.ofList (A ++ B ++ '|' :: C) = String.ofList ((A ++ B ++ ['|']) ++ [] ++ C) := by
          simp
        have := ih (A ++ B ++ ['|']) [] (by simp) (String.ofList B :: r)
        simp only [bsz, Nat.add_zero] at this
        rw [hs, this]
        cases h : splitFields C with
        | nil => exact absurd h (splitFields_ne_nil C)
        | cons g gs => simp [prefixField, splitFields, h]
      · have hcb : (c == '|') = false := by simp [hc]
        rw [hcb, if_neg Bool.false_ne_true]
        have hun : (⟨bsz A + bsz B⟩ : String.Pos.Raw).unoffsetBy 0 = ⟨bsz A + bsz B⟩ := by
          simp [String.Pos.Raw.unoffsetBy]
        have hnext : String.Pos.Raw.next (String.ofList (A ++ B ++ c :: C)) ⟨bsz A + bsz B⟩ =
            ⟨bsz A + bsz (B ++ [c])⟩ := by
          unfold String.Pos.Raw.next
          rw [hget]
          simp only [bsz_append, bsz, Nat.add_zero]
          show (⟨bsz A + bsz B + c.utf8Size⟩ : String.Pos.Raw) = _
          rw [Nat.add_assoc]
        rw [hun, hnext]
        have hs : String.ofList (A ++ B ++ c :: C) = String.ofList (A ++ (B ++ [c]) ++ C) := by
          simp
        have hB' : '|' ∉ B ++ [c] := by
          simp only [List.mem_append, List.mem_singleton, not_or]
          exact ⟨hB, fun h => hc h.symm⟩
        rw [hs, ih A (B ++ [c]) hB' r]
        cases h : splitFields C with
        | nil => exact absurd h (splitFields_ne_nil C)
        | cons g gs => simp [prefixField, splitFields, h, hc]


theorem prefixField_nil (fs : List (List Char)) (h : fs ≠ []) : prefixField [] fs = fs := by
  cases fs with
  | nil => exact absurd rfl h
  | cons g gs => rfl

/-- **Lean core's legacy `String.splitOn` with separator `"|"` is exactly the verified
list-level field splitter**, for every string (any Unicode content). -/
theorem splitOn_pipe_ofList (l : List Char) :
    (String.ofList l).splitOn "|" = (splitFields l).map String.ofList := by
  unfold String.splitOn
  rw [if_neg (by decide)]
  have := splitOnAux_pipe l [] [] (by simp) []
  simp only [List.nil_append, bsz, Nat.add_zero, List.reverse_nil] at this
  rw [prefixField_nil _ (splitFields_ne_nil l)] at this
  exact this

theorem splitOn_pipe (s : String) :
    s.splitOn "|" = (splitFields s.toList).map String.ofList := by
  have := splitOn_pipe_ofList s.toList
  rwa [String.ofList_toList] at this

open PCS.V2.ProofGatedSelfImprovement (Neuron predict)
open PCS.V2.ProofGatedArtifacts

def actChars (m : Neuron) : List Char := if m.useReLU then ['R'] else ['L']

theorem encode_toList (m : Neuron) :
    (encodeLegacy m).toList = joinFields ["PGSI1".toList, actChars m,
      (toString m.weight).toList, (toString m.bias).toList] := by
  have h1 : ("PGSI1|" : String).toList = "PGSI1".toList ++ ['|'] := by decide +kernel
  have h2 : ("|" : String).toList = ['|'] := by decide +kernel
  have hR : ("R" : String).toList = ['R'] := by decide +kernel
  have hL : ("L" : String).toList = ['L'] := by decide +kernel
  unfold encodeLegacy actChars
  cases m.useReLU <;>
    simp only [Bool.false_eq_true, if_false, if_true, String.toList_append, h1, h2, hR, hL,
      joinFields, List.append_assoc, List.cons_append, List.nil_append]


theorem actChars_pipe_free (m : Neuron) : '|' ∉ actChars m := by
  unfold actChars; cases m.useReLU <;> decide

theorem encode_splitOn (m : Neuron) (hw : '|' ∉ (toString m.weight).toList)
    (hb : '|' ∉ (toString m.bias).toList) :
    (encodeLegacy m).splitOn "|" =
      ["PGSI1", String.ofList (actChars m), toString m.weight, toString m.bias] := by
  rw [splitOn_pipe, encode_toList, splitFields_joinFields _ (by simp)]
  · simp only [List.map_cons, List.map_nil, String.ofList_toList]
  · intro f hf
    simp only [List.mem_cons, List.mem_nil_iff, or_false] at hf
    rcases hf with rfl | rfl | rfl | rfl
    · decide +kernel
    · exact actChars_pipe_free m
    · exact hw
    · exact hb

theorem parseComponentsLegacy_encodeLegacy (m : Neuron)
    (hw : '|' ∉ (toString m.weight).toList) (hb : '|' ∉ (toString m.bias).toList)
    (hwi : (toString m.weight).toInt? = some m.weight)
    (hbi : (toString m.bias).toInt? = some m.bias) :
    parseComponentsLegacy (encodeLegacy m) = some m := by
  unfold parseComponentsLegacy
  rw [encode_splitOn m hw hb]
  cases hm : m with
  | mk act w b =>
    rw [hm] at hwi hbi
    cases act <;> simp [actChars, hwi, hbi]


/-! ## The conditional roundtrip and its corollaries -/

/-- The core integer contract on the bounded range: rendering contains no delimiter and
core `toInt?` inverts core `toString`. -/
def CoreIntContract : Prop :=
  ∀ z : Int, -32 ≤ z → z ≤ 32 → '|' ∉ (toString z).toList ∧ (toString z).toInt? = some z

/-- **The assignment's target statement**, for the unmodified `decodeLegacy`/`encodeLegacy`,
under the explicit core contract. -/
theorem decode_encode_of_bounded_of_core (hcore : CoreIntContract) (m : Neuron)
    (h : valid m = true) : decodeLegacy (encodeLegacy m) = some m := by
  have hb : -32 ≤ m.weight ∧ m.weight ≤ 32 ∧ -32 ≤ m.bias ∧ m.bias ≤ 32 :=
    (decide_eq_true_eq).mp h
  obtain ⟨hw1, hwi⟩ := hcore m.weight hb.1 hb.2.1
  obtain ⟨hb1, hbi⟩ := hcore m.bias hb.2.2.1 hb.2.2.2
  unfold decodeLegacy
  rw [parseComponentsLegacy_encodeLegacy m hw1 hb1 hwi hbi]
  simp [h]

theorem encode_injective_of_bounded_of_core (hcore : CoreIntContract) {m₁ m₂ : Neuron}
    (h₁ : valid m₁ = true) (h₂ : valid m₂ = true) (he : encodeLegacy m₁ = encodeLegacy m₂) :
    m₁ = m₂ := by
  have e1 := decode_encode_of_bounded_of_core hcore m₁ h₁
  rw [he, decode_encode_of_bounded_of_core hcore m₂ h₂] at e1
  exact (Option.some.inj e1).symm

theorem toString_eq_ofList_render_of_append_spec
    (happ : ∀ s : String, String.Internal.append "-" s = "-" ++ s) (z : Int) :
    toString z = String.ofList (renderInt z) := by
  apply String.toList_inj.mp
  rw [String.toList_ofList, toString_toList_of_append_spec happ]

/-- The contract reduces to (i) the runtime behaviour of the opaque append on `"-"` and
(ii) a statement about core `toInt?` on the *transparent* canonical renderings. -/
theorem coreIntContract_of
    (happ : ∀ s : String, String.Internal.append "-" s = "-" ++ s)
    (hparse : ∀ z : Int, -32 ≤ z → z ≤ 32 → (String.ofList (renderInt z)).toInt? = some z) :
    CoreIntContract := by
  intro z h1 h2
  rw [toString_eq_ofList_render_of_append_spec happ, String.toList_ofList]
  exact ⟨pipe_not_mem_renderInt z, hparse z h1 h2⟩

/-! ## Unconditional results for the nonnegative fragment -/

theorem toString_toList_of_nonneg {z : Int} (h : 0 ≤ z) : (toString z).toList = renderInt z := by
  obtain ⟨n, rfl⟩ := Int.eq_ofNat_of_zero_le h
  exact toString_ofNat_toList n

theorem pipe_free_toString_of_nonneg {z : Int} (h : 0 ≤ z) : '|' ∉ (toString z).toList := by
  rw [toString_toList_of_nonneg h]; exact pipe_not_mem_renderInt z

/-- Nonnegative fragment of the target statement: needs **no** assumption about the
opaque append, only the parser fact on `[0, 32]`. -/
theorem decode_encode_of_bounded_nonneg
    (hparse : ∀ z : Int, 0 ≤ z → z ≤ 32 → (String.ofList (renderInt z)).toInt? = some z)
    (m : Neuron) (h : valid m = true) (hw : 0 ≤ m.weight) (hb : 0 ≤ m.bias) :
    decodeLegacy (encodeLegacy m) = some m := by
  have hb' : -32 ≤ m.weight ∧ m.weight ≤ 32 ∧ -32 ≤ m.bias ∧ m.bias ≤ 32 :=
    (decide_eq_true_eq).mp h
  have ew : toString m.weight = String.ofList (renderInt m.weight) := by
    apply String.toList_inj.mp; rw [String.toList_ofList, toString_toList_of_nonneg hw]
  have eb : toString m.bias = String.ofList (renderInt m.bias) := by
    apply String.toList_inj.mp; rw [String.toList_ofList, toString_toList_of_nonneg hb]
  unfold decodeLegacy
  rw [parseComponentsLegacy_encodeLegacy m (pipe_free_toString_of_nonneg hw) (pipe_free_toString_of_nonneg hb)
    (by rw [ew]; exact hparse _ hw hb'.2.1) (by rw [eb]; exact hparse _ hb hb'.2.2.2)]
  simp [h]

theorem actChars_injective {m₁ m₂ : Neuron} (h : actChars m₁ = actChars m₂) :
    m₁.useReLU = m₂.useReLU := by
  unfold actChars at h
  cases h1 : m₁.useReLU <;> cases h2 : m₂.useReLU <;> simp_all

/-- `encodeLegacy` is injective on neurons with nonnegative parameters — unconditionally. -/
theorem encode_injective_nonneg {m₁ m₂ : Neuron}
    (hw₁ : 0 ≤ m₁.weight) (hb₁ : 0 ≤ m₁.bias) (hw₂ : 0 ≤ m₂.weight) (hb₂ : 0 ≤ m₂.bias)
    (he : encodeLegacy m₁ = encodeLegacy m₂) : m₁ = m₂ := by
  have hs := congrArg (fun s => s.splitOn "|") he
  simp only at hs
  rw [encode_splitOn m₁ (pipe_free_toString_of_nonneg hw₁) (pipe_free_toString_of_nonneg hb₁),
    encode_splitOn m₂ (pipe_free_toString_of_nonneg hw₂) (pipe_free_toString_of_nonneg hb₂)] at hs
  simp only [List.cons.injEq, String.ofList_inj, true_and, and_true] at hs
  obtain ⟨ha, hw, hb⟩ := hs
  have hw' : renderInt m₁.weight = renderInt m₂.weight := by
    rw [← toString_toList_of_nonneg hw₁, ← toString_toList_of_nonneg hw₂, hw]
  have hb' : renderInt m₁.bias = renderInt m₂.bias := by
    rw [← toString_toList_of_nonneg hb₁, ← toString_toList_of_nonneg hb₂, hb]
  cases m₁; cases m₂
  simp only [PCS.V2.ProofGatedSelfImprovement.Neuron.mk.injEq]
  exact ⟨actChars_injective ha, renderInt_injective hw', renderInt_injective hb'⟩

/-- Soundness of the original decoder does **not** depend on any core-library fact:
whatever the opaque primitive does, an accepted text is the canonical encoding of a
bounded neuron (restating `decode_canonical` / `decode_bounded`). -/
theorem decode_sound_unconditional {raw : String} {m : Neuron} (h : decodeLegacy raw = some m) :
    encodeLegacy m = raw ∧ valid m = true := by
  unfold decodeLegacy at h
  cases hc : parseComponentsLegacy raw with
  | none => simp [hc] at h
  | some c =>
      by_cases hv : (valid c && (encodeLegacy c == raw)) = true
      · have hm : c = m := by simpa [hc, hv] using h
        subst hm
        simp only [Bool.and_eq_true, beq_iff_eq] at hv
        exact ⟨hv.2, hv.1⟩
      · simp [hc, hv] at h

/-! ## Byte compatibility of the verified `PGSI1` encoder with the legacy one

`ProofGatedArtifacts.encode` (verified renderer) and `encodeLegacy` (core `toString`)
produce the same text: unconditionally when both parameters are nonnegative, and for
all neurons under the runtime hypothesis that the opaque append behaves as `++` on the
prefix `"-"`. Consequently every artifact written by the legacy encoder is accepted by
the verified decoder, which has an unconditional roundtrip theorem. -/

theorem encode_toList_eq (m : Neuron) :
    (encode m).toList = joinFields ["PGSI1".toList, actChars m,
      renderInt m.weight, renderInt m.bias] := by
  simp only [encode, encodeChars, String.toList_ofList]
  rfl

theorem encode_eq_encodeLegacy_of_nonneg (m : Neuron) (hw : 0 ≤ m.weight) (hb : 0 ≤ m.bias) :
    encode m = encodeLegacy m := by
  apply String.toList_inj.mp
  rw [encode_toList_eq, encode_toList, toString_toList_of_nonneg hw,
    toString_toList_of_nonneg hb]

theorem encode_eq_encodeLegacy_of_append_spec
    (happ : ∀ s : String, String.Internal.append "-" s = "-" ++ s) (m : Neuron) :
    encode m = encodeLegacy m := by
  apply String.toList_inj.mp
  rw [encode_toList_eq, encode_toList, toString_toList_of_append_spec happ,
    toString_toList_of_append_spec happ]

/-- Legacy-written artifacts are accepted by the verified decoder (under the runtime
append hypothesis only; no assumption about core `toInt?` is needed any more). -/
theorem decode_encodeLegacy_of_append_spec
    (happ : ∀ s : String, String.Internal.append "-" s = "-" ++ s) (m : Neuron)
    (h : valid m = true) : decode (encodeLegacy m) = some m := by
  rw [← encode_eq_encodeLegacy_of_append_spec happ]
  exact decode_encode_of_bounded m h

end PCS.V2.ProofGatedV1Analysis
