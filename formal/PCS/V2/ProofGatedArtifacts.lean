import PCS.V2.ProofGatedSelfImprovement

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

def encode (m : Neuron) : String :=
  "PGSI1|" ++ (if m.useReLU then "R" else "L") ++ "|" ++
    toString m.weight ++ "|" ++ toString m.bias

def parseComponents (raw : String) : Option Neuron := do
  match raw.splitOn "|" with
  | ["PGSI1", activation, weightText, biasText] =>
    let activation ← if activation == "R" then some true
                     else if activation == "L" then some false else none
    let weight ← weightText.toInt?
    let bias ← biasText.toInt?
    some ⟨activation, weight, bias⟩
  | _ => none

def valid (m : Neuron) : Bool :=
  decide (-32 ≤ m.weight ∧ m.weight ≤ 32 ∧ -32 ≤ m.bias ∧ m.bias ≤ 32)

def decode (raw : String) : Option Neuron :=
  match parseComponents raw with
  | none => none
  | some m => if valid m && encode m == raw then some m else none

theorem decode_canonical {raw : String} {m : Neuron}
    (h : decode raw = some m) : encode m = raw := by
  unfold decode at h
  cases hc : parseComponents raw with
  | none => simp [hc] at h
  | some candidate =>
    by_cases hv : valid candidate && encode candidate == raw = true
    · simp [hc, hv] at h
      subst m
      exact (beq_iff_eq).mp ((Bool.and_eq_true.mp hv).2)
    · simp [hc, hv] at h

theorem decode_bounded {raw : String} {m : Neuron}
    (h : decode raw = some m) :
    -32 ≤ m.weight ∧ m.weight ≤ 32 ∧ -32 ≤ m.bias ∧ m.bias ≤ 32 := by
  unfold decode at h
  cases hc : parseComponents raw with
  | none => simp [hc] at h
  | some candidate =>
    by_cases hv : valid candidate && encode candidate == raw = true
    · simp [hc, hv] at h
      subst m
      exact (decide_eq_true_eq).mp ((Bool.and_eq_true.mp hv).1)
    · simp [hc, hv] at h

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
      exact ⟨old, candidate, ho, hn, decode_canonical ho,
        decode_canonical hn, accept_sound ha⟩

example : decode "PGSI1|R|1|1" = some intermediate := by decide
example : decode "PGSI1|R|2|1" = some optimum := by decide
example : acceptWire "PGSI1|R|0|0" "PGSI1|R|1|1" = true := by decide
example : acceptWire "PGSI1|R|1|1" "PGSI1|R|2|1" = true := by decide
example : acceptWire "PGSI1|R|1|1" "PGSI1|R|1|2" = false := by decide
example : decode "PGSI1|R|01|1" = none := by decide
example : decode "PGSI1|R|-0|0" = none := by decide
example : decode "PGSI1|R|33|0" = none := by decide
example : decode "PGSI1|R|1|1\n" = none := by decide
example : decode "PGSI1|R|1|1|override" = none := by decide

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
