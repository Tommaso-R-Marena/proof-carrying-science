import PCS.V2.ProofGatedV7Limits

/-!
V7 runtime fixtures and cross-checks (policy authority, PGSC7 certificates, trusted/untrusted
boundary, PGSR7 receipts, sweep certificates, runtime contract).

    V7_MODE=generate lake env lean scripts/proof_gated_v7_vectors.lean
    V7_MODE=check    lake env lean scripts/proof_gated_v7_vectors.lean

Fixtures written by `generate` and compared byte for byte by `check`
(directory `fixtures/proof_gated/v7/`):
* `policies/pinned0.pgpol7` — the pinned policy bytes; `policies/mal_*.pgpol7` — the five
  malicious policy substitutions (target, interval, corpus, architecture, checker);
* `certs/step{1,2,3}.pgsc7` — the PGSC7 certificates of the robust chain under the pinned
  policy with checker id 7 (`pinned7`);
* `receipts/adv_{0..6}.pgsr7` — the receipts emitted for the adversarial trace
  `ProofGatedBoundary.advTrace`;
* `attacks.tsv` — for every attack request: the naive design's decision and the safe
  design's decision; `trace.tsv` — the per-request decisions of the adversarial trace.

Runtime checks (executed, not proofs; the universal statements are cited per check):
* stored PGSC7 certificates replay through the boundary (`propose`), stored receipts pass
  the independent chain checker (`checkChain_sound`) and the anchored check;
* the stale one-receipt prefix is rejected against the anchor (`anchored_rejects_prefix`);
* every single-byte mutation of the pinned policy bytes: either undecodable or decodes to a
  policy whose canonical bytes are the mutated bytes (`decodePolicy_iff`), and never to the
  pinned policy;
* every single-byte mutation of `step1.pgsc7`: if the checker table accepts it, the strong
  gate holds for the decoded artifacts (`runChecker_sound`);
* every single-byte mutation of receipt `adv_2`: if the independent receipt checker accepts
  it, the decoded receipt satisfies `receiptOKB` (`checkReceiptBytes_sound`);
* `checkNF (genNF …)` agrees with the V6 universal decision procedure `noForgetting` on
  pseudo-random small networks (`checkNF_iff_noForgetting`), and a forged reordering is
  rejected whenever it is not sorted;
* the reference runtime (`refRuntime int64Half`) refines the authority on the adversarial
  trace (`rtRun_refines`).
Timing of `noForgetting` versus `checkNF` is printed as a measurement only.
-/

open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedCertificate
open PCS.V2.ProofGatedCertCodec
open PCS.V2.ProofGatedNoForget (noForgetting)
open PCS.V2.ProofGatedSweepCert
open PCS.V2.ProofGatedCert7
open PCS.V2.ProofGatedPolicy
open PCS.V2.ProofGatedBoundary
open PCS.V2.ProofGatedReceipt
open PCS.V2.ProofGatedRuntimeContract

namespace V7Vectors

def dir : System.FilePath := "fixtures/proof_gated/v7"

def hexDigit (n : Nat) : Char := "0123456789abcdef".toList.getD n '0'

def hex (bs : Bytes) : String :=
  String.ofList (bs.flatMap fun b => [hexDigit (b.toNat / 16), hexDigit (b.toNat % 16)])

def showDec : Option Bytes → String
  | some c => s!"ACCEPT:{hex c}"
  | none => "REJECT"

def pinned7 : Policy := { pinned0 with checker := checkerPGSC7 }

def chain : List WideNet := [gen0, r1, r2, gen3]

def cert7At (i : Nat) : Bytes :=
  encodeCert7 (genCert7 pinned7.spec i (chain.getD i gen0) (chain.getD (i + 1) gen0))

def s0 : AState := ⟨pinned0, 0, encodeBytes gen0⟩

def advRun : AState × List Receipt := runAdv s0 advTrace

def policies : List (String × Policy) :=
  [("pinned0", pinned0), ("mal_target", malTarget), ("mal_interval", malInterval),
   ("mal_corpus", malCorpus), ("mal_arch", malArch), ("mal_checker", malChecker)]

/-- (name, active, generation, request, naive decision) -/
def attacks : List (String × Bytes × Nat × Request × Option Bytes) :=
  [ ("target", encodeBytes gen3, 0, attackTarget, naiveDecide 0 (encodeBytes gen3) attackTarget)
  , ("interval", encodeBytes gen0, 0, attackInterval, naiveDecide 0 (encodeBytes gen0) attackInterval)
  , ("corpus", encodeBytes gen2, 0, attackCorpus, naiveDecide 0 (encodeBytes gen2) attackCorpus)
  , ("arch", encodeBytes gen0, 0, attackArch, naiveDecide 0 (encodeBytes gen0) attackArch)
  , ("checker", encodeBytes gen2, 0, attackChecker, naiveLegacyDecide 0 (encodeBytes gen2) attackChecker)
  , ("stale", encodeBytes gen3, 3, attackStale, staleDecide pinned0 attackStale) ]

def attacksTsv : String :=
  "# attack\tnaive_decision\tsafe_decision (pinned0)\n" ++
  String.join (attacks.map fun (n, act, g, r, nd) =>
    s!"{n}\t{showDec nd}\t{showDec (safeDecide pinned0 g act r)}\n")

def traceTsv : String :=
  "# index\taccepted\told_gen\tnew_gen\tnew_active_hex\n" ++
  String.join ((List.range advRun.2.length).map fun i =>
    let rc := advRun.2.getD i (mkReceipt s0 [] none)
    s!"{i}\t{rc.accepted}\t{rc.oldGen}\t{rc.newGen}\t{hex rc.newActive}\n")

def textFiles : List (System.FilePath × String) :=
  [ (dir / "attacks.tsv", attacksTsv), (dir / "trace.tsv", traceTsv) ]

def binFiles : List (System.FilePath × Bytes) :=
  policies.map (fun (n, p) => (dir / "policies" / s!"{n}.pgpol7", encodePolicy p)) ++
  [0, 1, 2].map (fun i => (dir / "certs" / s!"step{i + 1}.pgsc7", cert7At i)) ++
  (List.range advRun.2.length).map (fun i =>
    (dir / "receipts" / s!"adv_{i}.pgsr7", encodeReceipt (advRun.2.getD i (mkReceipt s0 [] none))))

def generate : IO UInt32 := do
  for d in ["policies", "certs", "receipts"] do IO.FS.createDirAll (dir / d)
  for (p, c) in textFiles do IO.FS.writeFile p c
  for (p, b) in binFiles do IO.FS.writeBinFile p (ByteArray.mk b.toArray)
  IO.println s!"wrote {textFiles.length + binFiles.length} V7 fixture files"
  return 0

def lcg (s : Nat) : Nat := (s * 1103515245 + 12345) % 2147483648

def drawInt (s k : Nat) : Int × Nat :=
  let s' := lcg s
  (Int.ofNat ((s' / 65536) % (2 * k + 1)) - k, s')

def drawNet (s width k : Nat) : WideNet × Nat := Id.run do
  let mut st := s
  let mut hs : List HiddenUnit := []
  for _ in [0:width] do
    let (a, t1) := drawInt st k
    let (b, t2) := drawInt t1 k
    let (o, t3) := drawInt t2 k
    hs := hs ++ [⟨a, b, o⟩]
    st := t3
  let (ob, t4) := drawInt st k
  return (⟨hs, ob⟩, t4)

def mutations (bs : Bytes) : List Bytes := Id.run do
  let repl : List UInt8 := ascii "0179-|P"
  let mut out := []
  for i in [0:bs.length] do
    for c in repl do
      let mb := bs.set i c
      if mb != bs then out := mb :: out
  return out

def check : IO UInt32 := do
  let mut n := 0
  for (p, c) in textFiles do
    let stored ← IO.FS.readFile p
    if stored != c then IO.eprintln s!"FAIL: {p} differs from regenerated content"; return 1
    n := n + 1
  for (p, b) in binFiles do
    let stored ← IO.FS.readBinFile p
    if stored.toList != b then IO.eprintln s!"FAIL: {p} differs"; return 1
    n := n + 1
  -- the adversarial trace and the malicious policy substitutions
  if advRun.1 != ⟨pinned0, 3, encodeBytes gen3⟩ || acceptedCount advRun.2 != 3 then
    IO.eprintln "FAIL: adversarial trace"; return 1
  n := n + 1
  for (name, act, g, r, nd) in attacks do
    if nd.isNone then IO.eprintln s!"FAIL: naive design rejects attack {name}"; return 1
    if (safeDecide pinned0 g act r).isSome then IO.eprintln s!"FAIL: safe design accepts {name}"; return 1
    if (propose ⟨pinned0, g, act⟩ r).1 != ⟨pinned0, g, act⟩ then
      IO.eprintln s!"FAIL: attack {name} changed the authority state"; return 1
    n := n + 1
  -- stored PGSC7 certificates replay through the boundary under pinned7
  let mut reqs : List Request := []
  for i in [1, 2, 3] do
    let b ← IO.FS.readBinFile (dir / "certs" / s!"step{i}.pgsc7")
    reqs := reqs ++ [⟨[], 0, [], b.toList⟩]
  let r7 := runAdv ⟨pinned7, 0, encodeBytes gen0⟩ reqs
  if r7.1 != ⟨pinned7, 3, encodeBytes gen3⟩ then IO.eprintln "FAIL: PGSC7 chain replay"; return 1
  -- PGSC7 certificates are rejected under the PGSC6 policy, and vice versa
  if (runAdv s0 reqs).1 != s0 then IO.eprintln "FAIL: PGSC7 accepted under PGSC6 policy"; return 1
  if (runAdv ⟨pinned7, 0, encodeBytes gen0⟩ genuineReqs).1 != ⟨pinned7, 0, encodeBytes gen0⟩ then
    IO.eprintln "FAIL: PGSC6 accepted under PGSC7 policy"; return 1
  n := n + 3
  -- stored receipts: independent chain check, anchoring, prefix rejection
  let pb ← IO.FS.readBinFile (dir / "policies" / "pinned0.pgpol7")
  let mut rcs : List Receipt := []
  for i in [0:advRun.2.length] do
    let b ← IO.FS.readBinFile (dir / "receipts" / s!"adv_{i}.pgsr7")
    if !checkReceiptBytes pb.toList b.toList then IO.eprintln s!"FAIL: receipt {i}"; return 1
    match decodeReceipt b.toList with
    | some rc => rcs := rcs ++ [rc]
    | none => IO.eprintln s!"FAIL: receipt {i} does not decode"; return 1
    n := n + 1
  let anchor : Anchor := (3, encodeBytes gen3)
  if !checkAnchored pb.toList (0, encodeBytes gen0) rcs anchor then
    IO.eprintln "FAIL: anchored receipt chain"; return 1
  if checkAnchored pb.toList (0, encodeBytes gen0) (rcs.take 3) anchor then
    IO.eprintln "FAIL: stale prefix accepted against anchor"; return 1
  if !checkChain pb.toList (0, encodeBytes gen0) (rcs.take 3) (1, encodeBytes r1) then
    IO.eprintln "FAIL: prefix should be a valid (unanchored) chain"; return 1
  if checkChain (encodePolicy malInterval) (0, encodeBytes gen0) rcs anchor then
    IO.eprintln "FAIL: receipts accepted under a substituted policy"; return 1
  n := n + 4
  -- policy byte mutations
  let pm := mutations (encodePolicy pinned0)
  let mut pdec := 0
  for mb in pm do
    match decodePolicy mb with
    | some p =>
      pdec := pdec + 1
      if encodePolicy p != mb || p == pinned0 then IO.eprintln "FAIL: policy mutation"; return 1
    | none => pure ()
    n := n + 1
  -- PGSC7 certificate mutations
  let cm := mutations (cert7At 0)
  let mut cacc := 0
  for mb in cm do
    match runChecker pinned7 0 (encodeBytes gen0) mb with
    | some cand =>
      cacc := cacc + 1
      match decodeBytes arch3 cand with
      | some m => if !acceptStrong pinned7.spec gen0 m then IO.eprintln "FAIL: cert mutation"; return 1
      | none => IO.eprintln "FAIL: cert mutation candidate"; return 1
    | none => pure ()
    n := n + 1
  -- receipt mutations
  let rm := mutations (encodeReceipt (advRun.2.getD 2 (mkReceipt s0 [] none)))
  let mut racc := 0
  for mb in rm do
    if checkReceiptBytes (encodePolicy pinned0) mb then
      racc := racc + 1
      match decodeReceipt mb with
      | some rc => if !receiptOKB pinned0 rc then IO.eprintln "FAIL: receipt mutation"; return 1
      | none => IO.eprintln "FAIL: receipt mutation decode"; return 1
    n := n + 1
  -- sweep certificate versus the V6 decision procedure, with timing
  let mut s := 7
  let mut nets : List (WideNet × WideNet × WideNet) := []
  for i in [0:600] do
    let w := 1 + i % 4
    let (a, s1) := drawNet s w 6
    let (m, s2) := drawNet s1 w 6
    let (t, s3) := drawNet s2 w 6
    s := s3
    nets := nets ++ [(a, m, t)]
  -- make some pairs non-forgetting: candidate = incumbent
  nets := nets ++ (nets.take 200).map fun (a, _, t) => (a, a, t)
  let v6 ← IO.lazyPure fun _ => nets.map fun (a, m, t) => noForgetting a m t
  let v6n := (v6.filter id).length
  let certs ← IO.lazyPure fun _ => nets.map fun (a, m, t) => genNF a m t
  let certLen := (certs.map (·.order.length)).foldl (· + ·) 0
  let v7 ← IO.lazyPure fun _ => (nets.zip certs).map fun ((a, m, t), c) => checkNF a m t c
  -- timing on larger networks (width 24, parameters in [-1000, 1000]); measurement only
  let mut big : List (WideNet × WideNet × WideNet) := []
  for _ in [0:40] do
    let (a, s1) := drawNet s 24 1000
    let (t, s2) := drawNet s1 24 1000
    s := s2
    big := big ++ [(a, a, t)]
  let t0 ← IO.monoMsNow
  let bv6 ← IO.lazyPure fun _ => big.map fun (a, m, t) => noForgetting a m t
  IO.println s!"big V6 results: {(bv6.filter id).length}"
  let t1 ← IO.monoMsNow
  let bcerts ← IO.lazyPure fun _ => big.map fun (a, m, t) => genNF a m t
  IO.println s!"big certificate entries: {(bcerts.map (·.order.length)).foldl (· + ·) 0}"
  let t2 ← IO.monoMsNow
  let bv7 ← IO.lazyPure fun _ => (big.zip bcerts).map fun ((a, m, t), c) => checkNF a m t c
  IO.println s!"big checkNF results: {(bv7.filter id).length}"
  let t3 ← IO.monoMsNow
  if bv6 != bv7 then IO.eprintln "FAIL: checkNF disagrees with noForgetting (big)"; return 1
  n := n + big.length
  if v6 != v7 then IO.eprintln "FAIL: checkNF disagrees with noForgetting"; return 1
  n := n + nets.length
  -- forged orders: reversing a certificate with two units of distinct split points is rejected
  let mut forged := 0
  for ((a, m, t), c) in nets.zip certs do
    let rev : NFCert := ⟨c.order.reverse⟩
    if checkNF a m t rev && !sortedB rev.order then IO.eprintln "FAIL: unsorted order accepted"; return 1
    if !sortedB rev.order then forged := forged + 1
    let dropped : NFCert := ⟨c.order.drop 1⟩
    if c.order.length > 0 && checkNF a m t dropped then IO.eprintln "FAIL: incomplete order accepted"; return 1
    n := n + 2
  -- the reference runtime refines the authority on the adversarial trace
  let st := rtRun (refRuntime PCS.V2.ProofGatedInterpreter.int64Half) st0 advTrace
  if abs pinned0 st != advRun.1 || st.served != st.active then IO.eprintln "FAIL: runtime refinement"; return 1
  for x in [-1000000, -12, -1, 0, 3, 17, 1000000] do
    if rtPredict (refRuntime PCS.V2.ProofGatedInterpreter.int64Half) st x != some (predict gen3 x) then
      IO.eprintln "FAIL: runtime prediction"; return 1
    n := n + 1
  IO.println s!"timing (measured, not verified): V6 noForgetting {t1 - t0} ms; genNF (untrusted generator) {t2 - t1} ms; checkNF {t3 - t2} ms on {big.length} width-24 updates; small-suite sweep-certificate entries {certLen}; {v6n} non-forgetting updates"
  IO.println s!"OK: {n} V7 checks passed ({binFiles.length + textFiles.length} fixture files, {attacks.length} policy/generation attacks, {pm.length} policy mutations of which {pdec} decode, {cm.length} PGSC7 mutations of which {cacc} accepted and re-verified, {rm.length} receipt mutations of which {racc} accepted and re-verified, {nets.length} sweep-certificate cross-checks with {forged} rejected reversed orders)"
  return 0

end V7Vectors

def runV7Vectors : IO Unit := do
  let mode ← IO.getEnv "V7_MODE"
  let code ← match mode with
    | some "generate" => V7Vectors.generate
    | _ => V7Vectors.check
  if code != 0 then throw (IO.userError s!"proof_gated_v7_vectors failed with code {code}")

#eval runV7Vectors
