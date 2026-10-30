import PCS

/-!
Differential-testing driver for the verified Lean `unit_compatible` and `csv_disjoint`
deciders (`PCS.V2.Units.unitCompatibleB`, `PCS.V2.Csv.csvDisjointB`, `PCS.V2.Csv.parseCsv`).

Reads one query per line on stdin; every argument is `x` followed by lower-case hex of raw bytes:
  `U <left-unit> <right-unit>`        prints `PASS`, `FAIL` (or `BADUTF8`)
  `C <left-csv> <right-csv> <key>`    prints `PASS` or `FAIL`
  `P <csv>`                           prints `OK <rows>` or `REJECT`
  `W <cert-json> <analysis-json>`     runs the Lean workflow check `Workflow.workflowCheckB`
  `E <inventory-json> <capture-json>` runs the Lean environment check `EnvFacts.envFactsB`
  `Z <zip>`                           runs the Lean canonical ZIP decoder `Zip.decodeZip`
  `D <text>`                          strict decimal `PKPDCheck.decimalQ`: `num/den` or `REJECT`
  `M <model-json>`                    PK/PD contract `PKPDCheck.decodeModel`: `PASS` / `FAIL`
  `K <model-json> <csv> <rel> <abs>`  PK/PD reference match `PKPDCheck.matchB` (columns
                                      `time`, `concentration`, `effect`; tolerances as
                                      decimal text): `PASS` / `FAIL`

Usage (from `formal/`, after `lake build`):
  lake env lean --run tools/LeanBuiltinCheck.lean < queries.txt
-/

open PCS.V2 PCS.V2.Json PCS.V2.Common

/-- Arguments are written `x<hex>` so that empty byte strings stay visible. -/
def hx (s : String) : Option (List UInt8) :=
  match s.toList with
  | 'x' :: rest => Hex.hexDecode (String.ofList rest)
  | _ => none

/-- `{"artifact_id", "path", "bytes_hex", "sha256"}` inventory item. -/
def decodeItem (v : Json.JVal) : Option Replay.InventoryItem := do
  let ms ← CertificateModel.objOf v
  let a ← Package.strField ms "artifact_id"
  let p ← Package.strField ms "path"
  let b ← (Package.strField ms "bytes_hex").bind Hex.hexDecode
  let d ← (Package.strField ms "sha256").bind Hex.hexDecode
  pure { artifactId := a, path := p, bytes := ⟨b.toArray⟩, sha256 := d }

def answer (line : String) : String :=
  match line.trimAscii.toString.splitOn " " with
  | ["U", a, b] =>
    match hx a, hx b with
    | some a, some b =>
      match String.fromUTF8? ⟨a.toArray⟩, String.fromUTF8? ⟨b.toArray⟩ with
      | some a, some b => if Units.unitCompatibleB a b then "PASS" else "FAIL"
      | _, _ => "BADUTF8"
    | _, _ => "BADHEX"
  | ["C", l, r, k] =>
    match hx l, hx r, hx k with
    | some l, some r, some k => if Csv.csvDisjointB l r k then "PASS" else "FAIL"
    | _, _, _ => "BADHEX"
  | ["W", c, a] =>
    match hx c, hx a with
    | some c, some a =>
      match String.fromUTF8? ⟨c.toArray⟩, String.fromUTF8? ⟨a.toArray⟩ with
      | some c, some a =>
        match Json.parse c.toList, Json.parse a.toList with
        | some (.obj cert), some (.arr fs) =>
          match mapOpt Workflow.decodeFreshSource fs with
          | some fa => if Workflow.workflowCheckB fa cert then "PASS" else "FAIL"
          | none => "BADANALYSIS"
        | _, _ => "BADJSON"
      | _, _ => "BADUTF8"
    | _, _ => "BADHEX"
  | ["E", i, c] =>
    match hx i, hx c with
    | some i, some c =>
      match String.fromUTF8? ⟨i.toArray⟩, String.fromUTF8? ⟨c.toArray⟩ with
      | some i, some c =>
        match Json.parse i.toList, Json.parse c.toList with
        | some (.arr items), some cap =>
          match mapOpt decodeItem items with
          | some inv => if EnvFacts.envFactsB inv cap then "PASS" else "FAIL"
          | none => "BADINVENTORY"
        | _, _ => "BADJSON"
      | _, _ => "BADUTF8"
    | _, _ => "BADHEX"
  | ["Z", z] =>
    match hx z with
    | some z =>
      match Zip.decodeZip ⟨z.toArray⟩ with
      | some es => "OK " ++ String.intercalate ";" (es.map fun e =>
          Hex.hexEncode e.1.toUTF8.data.toList ++ "=" ++ Hex.hexEncode (SHA256.sha256 e.2.data.toList))
      | none => "REJECT"
    | none => "BADHEX"
  | ["P", c] =>
    match hx c with
    | some c =>
      match Csv.parseCsv c with
      | some (_, rows) => s!"OK {rows.length}"
      | none => "REJECT"
    | none => "BADHEX"
  | ["D", d] =>
    match hx d with
    | some d =>
      match String.fromUTF8? ⟨d.toArray⟩ with
      | some d =>
        match PKPDCheck.decimalQ d with
        | some q => s!"{q.num}/{q.den}"
        | none => "REJECT"
      | none => "BADUTF8"
    | none => "BADHEX"
  | ["M", m] =>
    match hx m with
    | some m => if (PKPDCheck.decodeModel m).isSome then "PASS" else "FAIL"
    | none => "BADHEX"
  | ["K", m, c, rt, at_] =>
    match hx m, hx c with
    | some m, some c =>
      match PKPDCheck.tolOf (some (.str rt)), PKPDCheck.tolOf (some (.str at_)) with
      | some rt, some at_ =>
        let ms : PKPDCheck.MatchSpec :=
          ⟨"model", "output", "time", "concentration", "effect", rt, at_⟩
        if PKPDCheck.matchB ms ⟨m.toArray⟩ ⟨c.toArray⟩ then "PASS" else "FAIL"
      | _, _ => "FAIL"
    | _, _ => "BADHEX"
  | _ => "BADQUERY"

partial def loop (stdin : IO.FS.Stream) (stdout : IO.FS.Stream) : IO Unit := do
  let line ← stdin.getLine
  if line.isEmpty then return
  stdout.putStrLn (answer line)
  loop stdin stdout

def main : IO Unit := do
  loop (← IO.getStdin) (← IO.getStdout)
