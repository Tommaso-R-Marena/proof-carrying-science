import PCS.V2.ProofGatedV6EndToEnd

/-!
V6 runtime fixtures and cross-checks (byte artifacts, PGSC6 certificates, protocol,
reference interpreter).

    V6_MODE=generate lake env lean scripts/proof_gated_v6_vectors.lean
    V6_MODE=check    lake env lean scripts/proof_gated_v6_vectors.lean

Fixtures written by `generate` and compared byte for byte by `check`:
* `fixtures/proof_gated/v6_interp_vectors.tsv` — the 35 kernel-checked interpreter test
  vectors (`ProofGatedInterpreter.vectors`): name, artifact bytes in hex, input, expected
  output (`none` = must be rejected). This is the file an external runtime must reproduce.
* `fixtures/proof_gated/v6_certs/step{1,2,3}.pgsc6` — the exact PGSC6 certificate bytes of
  the three-step robust chain on `[-10^9, 10^9]`, and `v6_certs/decisions.tsv` — expected
  checker decisions for genuine, replayed, tampered and cross-wired certificates.

Runtime checks (not proofs; the universal statements are `interpBytes_eq_inferBytes`,
`checkCert_sound`, `checkCert_complete`, `decodeCert_iff`, `run_invariant`):
* interpreter vs `inferBytes` on 4000 pseudo-random byte strings (random ASCII mutations of
  canonical artifacts) and 2000 pseudo-random valid networks at several inputs;
* every single-byte mutation of certificate `step1` (225 positions × 6 replacement bytes):
  if the checker accepts the mutated bytes, the decoded artifacts must satisfy the
  executable strong gate;
* the adversarial protocol run of `ProofGatedProtocol.adversarial_run`.
-/

open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedCertificate
open PCS.V2.ProofGatedCertCodec
open PCS.V2.ProofGatedProtocol
open PCS.V2.ProofGatedInterpreter

namespace V6Vectors

def dir : System.FilePath := "fixtures/proof_gated"

def hexDigit (n : Nat) : Char := "0123456789abcdef".toList.getD n '0'

def hex (bs : Bytes) : String :=
  String.ofList (bs.flatMap fun b => [hexDigit (b.toNat / 16), hexDigit (b.toNat % 16)])

def showOpt : Option Int → String
  | some z => toString z
  | none => "none"

def interpTsv : String :=
  "# name\thex_bytes\tx\texpected  (arch: maxWidth=8, bound=32)\n" ++
  String.join (vectors.map fun v =>
    s!"{v.name}\t{hex v.bytes}\t{v.x}\t{showOpt v.expected}\n")

def chainCerts : List Bytes := genCerts specWide 0 gen0 [r1, r2, gen3]

def certAt (i : Nat) : Bytes := chainCerts.getD i []

/-- Expected checker decisions at the states of the chain. -/
def decisionCases : List (String × Nat × Bytes × Bytes) :=
  let e0 := encodeBytes gen0
  let e1 := encodeBytes r1
  let e2 := encodeBytes r2
  [ ("step1_genuine", 0, e0, certAt 0)
  , ("step2_genuine", 1, e1, certAt 1)
  , ("step3_genuine", 2, e2, certAt 2)
  , ("step1_replayed_at_gen1", 1, e1, certAt 0)
  , ("step2_at_wrong_generation", 2, e1, certAt 1)
  , ("step2_against_substituted_incumbent", 1, e0, certAt 1)
  , ("step1_forged_error_level", 0, e0,
      encodeCert { genCert specWide 0 gen0 r1 with errLevel := 2000000000 })
  , ("step1_forged_gain_witness", 0, e0,
      encodeCert { genCert specWide 0 gen0 r1 with gainWitness := 7 })
  , ("step1_forged_losses", 0, e0,
      encodeCert { genCert specWide 0 gen0 r1 with incLoss := 35, candLoss := 26 })
  , ("step1_other_interval", 0, e0,
      encodeCert { genCert specWide 0 gen0 r1 with lo := -4, hi := 4 })
  , ("step1_other_version", 0, e0,
      encodeCert { genCert specWide 0 gen0 r1 with version := 5 })
  , ("step1_candidate_swapped_to_gen0", 0, e0,
      encodeCert { genCert specWide 0 gen0 r1 with candidate := encodeBytes gen0 })
  , ("step1_truncated", 0, e0, (certAt 0).take 100)
  , ("step1_extra_field", 0, e0, certAt 0 ++ ascii "|0")
  , ("empty", 0, e0, []) ]

def decisionsTsv : String :=
  "# case\tgeneration\tactive_hex\tcert_len_bytes\tdecision\n" ++
  String.join (decisionCases.map fun (n, g, act, cb) =>
    s!"{n}\t{g}\t{hex act}\t{cb.length}\t{if checkCertBytes specWide g act cb then "ACCEPT" else "REJECT"}\n")

def lcg (s : Nat) : Nat := (s * 1103515245 + 12345) % 2147483648

def drawInt (s k : Nat) : Int × Nat :=
  let s' := lcg s
  (Int.ofNat ((s' / 65536) % (2 * k + 1)) - k, s')

def files : List (System.FilePath × String) :=
  [ (dir / "v6_interp_vectors.tsv", interpTsv)
  , (dir / "v6_certs" / "decisions.tsv", decisionsTsv) ]

def certFiles : List (System.FilePath × Bytes) :=
  [ (dir / "v6_certs" / "step1.pgsc6", certAt 0)
  , (dir / "v6_certs" / "step2.pgsc6", certAt 1)
  , (dir / "v6_certs" / "step3.pgsc6", certAt 2) ]

def generate : IO UInt32 := do
  IO.FS.createDirAll (dir / "v6_certs")
  for (p, c) in files do IO.FS.writeFile p c
  for (p, b) in certFiles do IO.FS.writeBinFile p (ByteArray.mk b.toArray)
  IO.println s!"wrote {files.length + certFiles.length} V6 fixture files"
  return 0

def randomChecks : IO (Option String × Nat) := do
  let mut n := 0
  let mut s := 2026
  -- random mutations of canonical artifacts
  let bases : List Bytes := [encodeBytes gen3, ascii gen3Perm, ascii "PGSI2-WIDE|32|-32|32|-32"]
  let alphabet : List UInt8 := (ascii "0123456789-|+ PGSIWDE") ++ [0, 200]
  for i in [0:4000] do
    let base := bases.getD (i % 3) []
    let s1 := lcg s
    let pos := (s1 / 65536) % (base.length + 1)
    let s2 := lcg s1
    let c := alphabet.getD ((s2 / 65536) % alphabet.length) 0
    let s3 := lcg s2
    let op := (s3 / 65536) % 3
    s := s3
    let bs := if op == 0 then base.set pos c
      else if op == 1 then base.take pos ++ c :: base.drop pos
      else base.take pos ++ base.drop (pos + 1)
    let (x, s') := drawInt s 1000
    s := s'
    if interpBytes arch3 bs x != inferBytes arch3 bs x then
      return (some s!"interp/infer mismatch on {hex bs} at {x}", n)
    n := n + 1
  -- random valid networks
  for _ in [0:2000] do
    let (w, s1) := drawInt s 4
    let width := w.natAbs * 2
    let mut st := s1
    let mut hs : List HiddenUnit := []
    for _ in [0:width] do
      let (a, t1) := drawInt st 32
      let (b, t2) := drawInt t1 32
      let (o, t3) := drawInt t2 32
      hs := hs ++ [⟨a, b, o⟩]
      st := t3
    let (ob, t4) := drawInt st 32
    s := t4
    let m : WideNet := ⟨hs, ob⟩
    for x in [-1000000000000, -33, -1, 0, 1, 17, 1000000000000] do
      let expected := if valid arch3 m then some (predict m x) else none
      if interpBytes arch3 (encodeBytes m) x != expected then
        return (some s!"interp mismatch on {repr m} at {x}", n)
      n := n + 1
  return (none, n)

def mutationChecks : IO (Option String × Nat × Nat) := do
  let cb := certAt 0
  let act := encodeBytes gen0
  let repl : List UInt8 := ascii "0179-|"
  let mut accepted := 0
  let mut total := 0
  for i in [0:cb.length] do
    for c in repl do
      let mb := cb.set i c
      if mb == cb then continue
      total := total + 1
      if checkCertBytes specWide 0 act mb then
        accepted := accepted + 1
        match decodeCert mb with
        | some cert =>
          match decodeBytes arch3 cert.incumbent, decodeBytes arch3 cert.candidate with
          | some o, some n =>
            if !(acceptStrong specWide o n) then
              return (some s!"mutation {i} accepted but strong gate fails", total, accepted)
          | _, _ => return (some s!"mutation {i} accepted but artifacts do not decode", total, accepted)
        | none => return (some s!"mutation {i} accepted but does not decode", total, accepted)
  return (none, total, accepted)

def check : IO UInt32 := do
  let mut n := 0
  for (p, c) in files do
    let stored ← IO.FS.readFile p
    if stored != c then IO.eprintln s!"FAIL: {p} differs from regenerated content"; return 1
    n := n + 1
  for (p, b) in certFiles do
    let stored ← IO.FS.readBinFile p
    if stored.toList != b then IO.eprintln s!"FAIL: {p} differs"; return 1
    -- the stored file itself must decode and be accepted at its step
    n := n + 1
  -- decisions recomputed from stored certificate files
  let s1 ← IO.FS.readBinFile (dir / "v6_certs" / "step1.pgsc6")
  let s2 ← IO.FS.readBinFile (dir / "v6_certs" / "step2.pgsc6")
  let s3 ← IO.FS.readBinFile (dir / "v6_certs" / "step3.pgsc6")
  let st := (run specWide ⟨0, encodeBytes gen0⟩ [s1.toList, s2.toList, s3.toList]).1
  if st != ⟨3, encodeBytes gen3⟩ then IO.eprintln "FAIL: stored certificates do not replay"; return 1
  n := n + 1
  -- adversarial run
  let genuine := chainCerts
  let tampered := encodeCert { genCert specWide 0 gen0 r1 with errLevel := 2000000000 }
  let adv := [ascii "garbage", tampered] ++ genuine.take 1 ++ [genuine.getD 0 []] ++ genuine.drop 1
  let r := run specWide ⟨0, encodeBytes gen0⟩ adv
  if r.1 != ⟨3, encodeBytes gen3⟩ || acceptedCount r.2 != 3 then
    IO.eprintln "FAIL: adversarial run"; return 1
  n := n + 1
  let (e, k) ← randomChecks
  if let some msg := e then IO.eprintln s!"FAIL: {msg}"; return 1
  n := n + k
  let (e2, total, acc) ← mutationChecks
  if let some msg := e2 then IO.eprintln s!"FAIL: {msg}"; return 1
  n := n + total
  IO.println s!"OK: {n} V6 checks passed ({vectors.length} interpreter vectors, {decisionCases.length} certificate decision cases, {k} interpreter cross-checks, {total} certificate byte mutations of which {acc} accepted and re-verified)"
  return 0

end V6Vectors

def runV6Vectors : IO Unit := do
  let mode ← IO.getEnv "V6_MODE"
  let code ← match mode with
    | some "generate" => V6Vectors.generate
    | _ => V6Vectors.check
  if code != 0 then throw (IO.userError s!"proof_gated_v6_vectors failed with code {code}")

#eval runV6Vectors
