import PromotionReplay

/-! Independent line-oriented reference verifier for the typed PromotionReplay model. -/
set_option autoImplicit false
namespace CheckLineage
open EvolvingSafetyGate PromotionReplay

abbrev Parse := Except String

def natural (s : String) : Parse Nat := do
  let some n := s.toNat? | throw "expected unsigned decimal"
  if toString n != s then throw "noncanonical unsigned decimal"
  return n

def bit : String → Parse Bool
  | "0" => .ok false
  | "1" => .ok true
  | _ => .error "expected 0 or 1"

def mechanism : String → Parse Mechanism
  | "channel1Only" => .ok .channel1Only
  | "jointChannel" => .ok .jointChannel
  | "correctingGuard" => .ok .correctingGuard
  | "jointDetectingGuard" => .ok .jointDetectingGuard
  | "ensembleProbe" => .ok .ensembleProbe
  | "composedStack" => .ok .composedStack
  | _ => .error "unknown mechanism class"

def fields (s : String) := (s.splitOn " ").filter (· != "")

def lines (s : String) := ((s.splitOn "\n").map (·.trimAscii.toString)).filter (· != "")

structure Data where
  labels : List (Nat × Bool) := []
  classes : List (Nat × Mechanism) := []
  observations : List ((Nat × Nat) × Bool) := []

def lookup {K V : Type} [DecidableEq K] (rows : List (K × V)) (k : K) : Option V :=
  (rows.find? (fun row => decide (row.1 = k))).map Prod.snd

def insert {K V : Type} [DecidableEq K] (rows : List (K × V)) (k : K)
    (v : V) : Parse (List (K × V)) :=
  if (lookup rows k).isSome then .error "duplicate row identity" else .ok ((k,v)::rows)

def readReview (raw : String) : Parse (Review × Champion) := do
  let header :: rows := lines raw | throw "empty review"
  let ["review", version, seed] := fields header | throw "invalid review header"
  let v ← natural version
  let s ← natural seed
  let mut data : Data := {}
  for row in rows do
    match fields row with
    | ["case", k, b] =>
      data := {data with labels := ← insert data.labels (← natural k) (← bit b)}
    | ["class", k, m] =>
      data := {data with classes := ← insert data.classes (← natural k) (← mechanism m)}
    | ["observed", m, c, b] =>
      data := {data with observations := ← insert data.observations (← natural m, ← natural c) (← bit b)}
    | _ => throw "invalid review row"
  if data.labels.isEmpty then throw "empty case set"
  for ((m,c),_) in data.observations do
    if (lookup data.classes m).isNone || (lookup data.labels c).isNone then
      throw "unregistered observation"
  let r : Review :=
    { version := v
      cases := data.labels.map Prod.fst
      label := fun k => (lookup data.labels k).getD false
      observed := fun m c => lookup data.observations (m,c)
      mechanism := fun m => (lookup data.classes m).getD .channel1Only}
  if !(admissible (r.mechanism s)) then throw "seed lacks class admission"
  if (score r s r.cases).isNone then throw "seed lacks complete evaluation"
  return (r, ⟨s, 0⟩)

def readProposal (row : String) : Parse Proposal := do
  let ["offer", v, parent, g, c] := fields row | throw "invalid offer"
  return ⟨← natural v, ⟨← natural parent, ← natural g⟩, ← natural c⟩

def check (review path : String) : Parse String := do
  let (r, seed) ← readReview review
  let ps ← (lines path).mapM readProposal
  let some champion := replay r seed ps | throw "lineage rejected"
  let some n := score r champion.id r.cases | throw "incomplete champion evaluation"
  return s!"accepted champion={champion.id} generation={champion.generation} correct={n}/{r.cases.length}"

end CheckLineage

def main (args : List String) : IO UInt32 := do
  let [review, proposals] := args | IO.eprintln "expected REVIEW and OFFERS files"; return 2
  match CheckLineage.check (← IO.FS.readFile review) (← IO.FS.readFile proposals) with
  | .error e => IO.eprintln e; return 1
  | .ok verdict => IO.println verdict; return 0
