import PCS.V2.ProofGatedSelfImprovement
import PCS.V2.ProofGatedCodec

/-!
# Frozen canonical model-artifact format and file-authorized neural update

An artifact is a *single exact UTF-8 string*:
  PGSI1|R|1|1
or PGSI1|L|0|0. R means ReLU, L means linear.

The Lean verifier itself reads both files and canonicalizes their contents.
The authorizing decision is about the content it actually read, unlike a
Python-generated numeric description of a proposed model.

Boundary: this is **not** a secure deployment gate or proof of OS file-system
immutability, symlink safety, isolation or time-of-check/time-of-use safety.
The host must securely bind verified artifact bytes to deployed bytes.
-/

namespace PCS.V2.ProofGatedArtifacts

open PCS.V2.ProofGatedSelfImprovement
open PCS.V2.ProofGatedCodec

/-! ## Verified renderer and parser (the format bytes are unchanged)

The artifact bytes are exactly the original `PGSI1|R|w|b` / `PGSI1|L|w|b` text.
Integers are rendered by the transparent decimal renderer
`ProofGatedCodec.renderInt` (built on core `Nat.toDigits 10`) and parsed by the
canonical decoder `ProofGatedCodec.parseInt`; fields are split by the verified
`ProofGatedCodec.splitFields`. The original definitions, which used core
`toString : Int → String`, `String.splitOn` and `String.toInt?`, are retained below
as `encodeLegacy` / `parseComponentsLegacy` / `decodeLegacy`. Core `toString` of a
negative integer goes through the `opaque` constant `String.Internal.append`, so no
roundtrip theorem about the legacy encoder can be derived inside Lean; the
replacement below has the same bytes (`ProofGatedV1Analysis.encode_eq_encodeLegacy_*`)
and a fully proved roundtrip (`decode_encode_of_bounded`). -/

def activationChars (useReLU : Bool) : List Char := if useReLU then ['R'] else ['L']

def encodeChars (m : Neuron) : List Char :=
  joinFields ["PGSI1".toList, activationChars m.useReLU, renderInt m.weight, renderInt m.bias]

def encode (m : Neuron) : String := String.ofList (encodeChars m)

def parseActivation (a : List Char) : Option Bool :=
  if a = ['R'] then some true else if a = ['L'] then some false else none

def parseComponents (raw : String) : Option Neuron :=
  match splitFields raw.toList with
  | [tag, activation, weightText, biasText] =>
    if tag = "PGSI1".toList then do
      let activation ← parseActivation activation
      let weight ← parseInt weightText
      let bias ← parseInt biasText
      some ⟨activation, weight, bias⟩
    else none
  | _ => none

def valid (m : Neuron) : Bool :=
  decide (-32 ≤ m.weight ∧ m.weight ≤ 32 ∧ -32 ≤ m.bias ∧ m.bias ≤ 32)

def decode (raw : String) : Option Neuron :=
  match parseComponents raw with
  | none => none
  | some m => if valid m && encode m == raw then some m else none

theorem decode_canonical {raw : String} {m : Neuron}
    (h : decode raw = some m) : encode m = raw := by
  cases hc : parseComponents raw with
  | none =>
      simp [decode, hc] at h
  | some candidate =>
      by_cases hv : (valid candidate && (encode candidate == raw)) = true
      · have hm : candidate = m := by
          simpa [decode, hc, hv] using h
        subst m
        have hvparts : valid candidate = true ∧ (encode candidate == raw) = true := by
          simpa only [Bool.and_eq_true] using hv
        exact (beq_iff_eq).mp hvparts.2
      · simp [decode, hc, hv] at h

theorem decode_bounded {raw : String} {m : Neuron}
    (h : decode raw = some m) :
    -32 ≤ m.weight ∧ m.weight ≤ 32 ∧ -32 ≤ m.bias ∧ m.bias ≤ 32 := by
  cases hc : parseComponents raw with
  | none =>
      simp [decode, hc] at h
  | some candidate =>
      by_cases hv : (valid candidate && (encode candidate == raw)) = true
      · have hm : candidate = m := by
          simpa [decode, hc, hv] using h
        subst m
        have hvparts : valid candidate = true ∧ (encode candidate == raw) = true := by
          simpa only [Bool.and_eq_true] using hv
        exact (decide_eq_true_eq).mp hvparts.1
      · simp [decode, hc, hv] at h

def acceptWire (oldRaw newRaw : String) : Bool :=
  match decode oldRaw, decode newRaw with
  | some old, some candidate => accept old candidate
  | _, _ => false

theorem acceptWire_sound {oldRaw newRaw : String}
    (h : acceptWire oldRaw newRaw = true) :
    ∃ old candidate,
      decode oldRaw = some old ∧ decode newRaw = some candidate ∧
      encode old = oldRaw ∧ encode candidate = newRaw ∧
      admissible old candidate := by
  unfold acceptWire at h
  cases ho : decode oldRaw with
  | none => simp [ho] at h
  | some old =>
    cases hn : decode newRaw with
    | none => simp [ho, hn] at h
    | some candidate =>
      have ha : accept old candidate = true := by simpa [ho, hn] using h
      exact ⟨old, candidate, by simp, by simp, decode_canonical ho,
        decode_canonical hn, accept_sound ha⟩


/-! ## Unconditional roundtrip, injectivity and exact acceptance -/

theorem activationChars_pipe_free (b : Bool) : '|' ∉ activationChars b := by
  cases b <;> decide

theorem parseActivation_activationChars (b : Bool) :
    parseActivation (activationChars b) = some b := by
  cases b <;> decide

theorem splitFields_encode (m : Neuron) :
    splitFields (encode m).toList =
      ["PGSI1".toList, activationChars m.useReLU, renderInt m.weight, renderInt m.bias] := by
  unfold encode encodeChars
  rw [String.toList_ofList, splitFields_joinFields _ (by simp)]
  intro f hf
  simp only [List.mem_cons, List.mem_nil_iff, or_false] at hf
  rcases hf with rfl | rfl | rfl | rfl
  · decide
  · exact activationChars_pipe_free _
  · exact pipe_not_mem_renderInt _
  · exact pipe_not_mem_renderInt _

/-- The parser inverts the renderer on **every** neuron (no range assumption). -/
theorem parseComponents_encode (m : Neuron) : parseComponents (encode m) = some m := by
  unfold parseComponents
  rw [splitFields_encode]
  simp [parseActivation_activationChars, parseInt_renderInt]

/-- **Priority A target statement**, for the artifact format's `decode`/`encode`. -/
theorem decode_encode_of_bounded (m : Neuron)
    (h : valid m = true) : decode (encode m) = some m := by
  simp [decode, parseComponents_encode, h]

/-- `encode` is injective on all neurons (hence in particular on bounded ones). -/
theorem encode_injective {m₁ m₂ : Neuron} (he : encode m₁ = encode m₂) : m₁ = m₂ := by
  have h := parseComponents_encode m₁
  rw [he, parseComponents_encode m₂] at h
  exact (Option.some.inj h).symm

/-- **Exact acceptance characterisation**: `decode` accepts a text exactly when it is the
canonical encoding of a neuron with weight and bias in `[-32, 32]`. Every
noncanonical spelling (`"PGSI1|R|+1|0"`, `"PGSI1|R|-0|0"`, `"PGSI1|R|01|0"`, extra
fields, whitespace, …) and every out-of-range parameter is rejected. -/
theorem decode_eq_some_iff (raw : String) (m : Neuron) :
    decode raw = some m ↔ valid m = true ∧ encode m = raw := by
  constructor
  · intro h
    exact ⟨(decide_eq_true_eq).mpr (decode_bounded h), decode_canonical h⟩
  · rintro ⟨hv, rfl⟩
    exact decode_encode_of_bounded m hv

theorem decode_eq_none_of_invalid (m : Neuron) (h : valid m = false) :
    decode (encode m) = none := by
  simp [decode, parseComponents_encode, h]

theorem encode_examples :
    encode ⟨true, 1, 1⟩ = "PGSI1|R|1|1" ∧ encode ⟨false, 0, 0⟩ = "PGSI1|L|0|0" ∧
    encode ⟨true, -32, 32⟩ = "PGSI1|R|-32|32" ∧ encode ⟨false, -7, -1⟩ = "PGSI1|L|-7|-1" := by
  decide +kernel

theorem decode_rejection_examples :
    decode "PGSI1|R|+1|1" = none ∧ decode "PGSI1|R|-0|1" = none ∧
    decode "PGSI1|R|01|1" = none ∧ decode "PGSI1|R|33|1" = none ∧
    decode "PGSI1|R|1|-33" = none ∧ decode "PGSI1|X|1|1" = none ∧
    decode "PGSI1|R|1|1|" = none ∧ decode "PGSI1|R| 1|1" = none ∧
    decode "PGSI2|R|1|1" = none ∧ decode "" = none := by
  decide +kernel

theorem decode_acceptance_examples :
    decode "PGSI1|R|-32|32" = some ⟨true, -32, 32⟩ ∧
    decode "PGSI1|L|-7|-1" = some ⟨false, -7, -1⟩ := by
  decide +kernel

/-! ## Legacy definitions (original text, retained for reference)

These are the original definitions based on core `toString`, `String.splitOn` and
`String.toInt?`. They are no longer used by `decode`, `acceptWire` or the CLI. See
`ProofGatedV1Analysis` for what can and cannot be proved about them. -/

def encodeLegacy (m : Neuron) : String :=
  "PGSI1|" ++ (if m.useReLU then "R" else "L") ++ "|" ++
    toString m.weight ++ "|" ++ toString m.bias

def parseComponentsLegacy (raw : String) : Option Neuron := do
  match raw.splitOn "|" with
  | ["PGSI1", activation, weightText, biasText] =>
    let activation ← if activation == "R" then some true
                     else if activation == "L" then some false else none
    let weight ← weightText.toInt?
    let bias ← biasText.toInt?
    some ⟨activation, weight, bias⟩
  | _ => none

def decodeLegacy (raw : String) : Option Neuron :=
  match parseComponentsLegacy raw with
  | none => none
  | some m => if valid m && encodeLegacy m == raw then some m else none

end PCS.V2.ProofGatedArtifacts

def main (args : List String) : IO UInt32 := do
  match args with
  | [oldPath, candidatePath] =>
    try
      let oldRaw ← IO.FS.readFile ⟨oldPath⟩
      let candidateRaw ← IO.FS.readFile ⟨candidatePath⟩
      if PCS.V2.ProofGatedArtifacts.acceptWire oldRaw candidateRaw then
        IO.println "ACCEPT"
        return 0
      else
        IO.println "REJECT:invalid_artifact_or_update"
        return 1
    catch _ =>
      IO.println "REJECT:read_failure"
      return 2
  | _ =>
    IO.println "REJECT:bad_arity"
    return 2
