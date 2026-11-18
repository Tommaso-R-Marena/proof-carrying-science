import PCS.V2.ProofGatedFormalization

/-!
# Frozen PGRA capability-artifact wire format

Canonical exact UTF-8 string (no trailing newline):

  PGRA1|0,1,2,0

Statuses are Nat codes from `CaseStatus.toNat` (`fail=0`, `abstain=1`,
`supported=2`). Parsing is `List Char`-based so examples reduce under `decide`.

Boundary: file IO is not a proof of filesystem immutability or TOCTOU safety.
-/

namespace PCS.V2.ProofGatedFormalizationArtifacts

open PCS.V2.ProofGatedFormalization

def wireMagic : List Char := "PGRA1".toList

private def renderNat : Nat → List Char
  | 0 => ['0']
  | 1 => ['1']
  | 2 => ['2']
  | _ + 3 => ['?'] -- unreachable for CaseStatus codes; keeps encode total

private def renderCodes : List Nat → List Char
  | [] => []
  | [n] => renderNat n
  | n :: rest => renderNat n ++ ',' :: renderCodes rest

def encodeChars (c : Capability) : List Char :=
  wireMagic ++ '|' :: renderCodes (c.map CaseStatus.toNat)

def encode (c : Capability) : String := String.ofList (encodeChars c)

private def parseDigit : Char → Option Nat
  | '0' => some 0
  | '1' => some 1
  | '2' => some 2
  | _ => none

private def parseCode (cs : List Char) : Option CaseStatus :=
  match cs with
  | [c] => do
      let n ← parseDigit c
      CaseStatus.ofNat? n
  | _ => none

private def splitComma : List Char → List (List Char)
  | [] => [[]]
  | c :: cs =>
      let rest := splitComma cs
      if c = ',' then
        [] :: rest
      else
        match rest with
        | [] => [[c]]
        | head :: tails => (c :: head) :: tails

private def parseCodes (body : List Char) : Option Capability :=
  if body = [] then
    some []
  else
    let rec go : List (List Char) → Option Capability
      | [] => some []
      | t :: ts => do
          let s ← parseCode t
          let rest ← go ts
          some (s :: rest)
    go (splitComma body)

def parseComponents (raw : String) : Option Capability :=
  let cs := raw.toList
  let rec splitPipe : List Char → Option (List Char × List Char)
    | [] => none
    | '|' :: rest => some ([], rest)
    | c :: rest => do
        let (pre, post) ← splitPipe rest
        some (c :: pre, post)
  match splitPipe cs with
  | some (magic, body) =>
      if magic = wireMagic then parseCodes body else none
  | none => none

def decode (raw : String) : Option Capability :=
  match parseComponents raw with
  | none => none
  | some c => if encode c == raw then some c else none

theorem decode_canonical {raw : String} {c : Capability}
    (h : decode raw = some c) : encode c = raw := by
  cases hc : parseComponents raw with
  | none =>
      simp [decode, hc] at h
  | some candidate =>
      by_cases hv : (encode candidate == raw) = true
      · have hm : candidate = c := by
          simpa [decode, hc, hv] using h
        subst c
        exact (beq_iff_eq).mp hv
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

example : encode [.fail, .abstain, .supported] = "PGRA1|0,1,2" := by decide
example : decode "PGRA1|0,1,2" = some [.fail, .abstain, .supported] := by decide
example : decode "PGRA1|0,1,3" = none := by decide
example : decode "PGRA1|01,1" = none := by decide
example : acceptWire "PGRA1|0,0,0,1" "PGRA1|2,0,0,1" = true := by decide

end PCS.V2.ProofGatedFormalizationArtifacts

def main (args : List String) : IO UInt32 := do
  match args with
  | [oldPath, candidatePath] =>
    try
      let oldRaw ← IO.FS.readFile ⟨oldPath⟩
      let candidateRaw ← IO.FS.readFile ⟨candidatePath⟩
      if PCS.V2.ProofGatedFormalizationArtifacts.acceptWire oldRaw candidateRaw then
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
