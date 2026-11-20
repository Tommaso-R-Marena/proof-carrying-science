import Withdrawal
import Std

/-! First line: domain tag, subject ID, exact withdrawal budget.
Second line: distinct trust-group IDs. Remaining lines: distinct world ID, target bit,
then the per-group agreement bits in header order. The caller authenticates the
subject, group partition and hypothesis table. -/
open PCSResearch.Withdrawal
namespace EvidenceWire
structure Row where
  name : String
  good : Bool
  votes : List Bool

def bit : String → Option Bool
  | "1" => some true
  | "0" => some false
  | _ => none

def ident (s : String) : Bool :=
  !s.isEmpty && s.length ≤ 64 && s.toList.all (fun c => c.isAlphanum || c == '_' || c == '-')

def row (n : Nat) (s : String) : Option Row := do
  let name :: target :: cells := s.splitOn " " | none
  guard (ident name && cells.length == n)
  return ⟨name, ← bit target, ← cells.mapM bit⟩

def classify (s : String) : Option String := do
  guard (s.length ≤ 65536)
  let header :: sources :: lines := s.trimAsciiEnd.toString.splitOn "\n" | none
  let [domain, subject, rawK] := header.splitOn " " | none
  guard (["causal-model","policy","formal-reference"].contains domain && ident subject)
  let k ← rawK.toNat?
  let tags := sources.splitOn " "
  guard (tags.length ≤ 64 && tags.all ident && tags.Nodup && toString k == rawK && k ≤ tags.length)
  guard (!lines.isEmpty && lines.length ≤ 256)
  let rows ← lines.mapM (row tags.length)
  guard ((rows.map Row.name).Nodup)
  let groups := List.range tags.length
  let agrees := fun (r : Row) (i : Nat) => r.votes[i]?.getD false
  let verdictTag := domain ++ " " ++ subject ++ " "
  if !(rows.any fun r => r.votes.all id) then return verdictTag ++ "INCONSISTENT"
  if check rows groups agrees Row.good k then return verdictTag ++ "ROBUST"
  let some w := rows.find? (fun r => !r.good && cost groups (conflicts agrees r) ≤ k) | none
  let missing := (tags.zip w.votes).filterMap (fun (tag, ok) => if ok then none else some tag)
  return verdictTag ++ "COUNTEREXAMPLE " ++ w.name ++ " " ++ String.intercalate "," missing
end EvidenceWire

def main : IO UInt32 := do
  let input ← IO.getStdin
  -- Process independent, small records as one bounded matrix per line using '|'
  -- for row separation. Matrix identifiers cannot contain that separator.
  let mut line ← input.getLine
  while !line.isEmpty do
    match EvidenceWire.classify (line.trimAsciiEnd.toString.replace "|" "\n") with
    | some v => IO.println v
    | none => IO.println "INVALID"
    line ← input.getLine
  return 0
