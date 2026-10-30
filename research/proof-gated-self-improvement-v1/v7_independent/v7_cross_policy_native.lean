import PCS.V2.ProofGatedPolicy

/-!
Direct executable Lean V7 oracle for a Python-generated, exact-wire PGSC6 certificate.

This is a runtime regression test, NOT a new theorem and NOT a protected
deployment authority. The input is emitted by v7_boundary_falsification.py
from the source-independent Python implementation. All decisions below come
from the *actual* V7 runChecker over the byte file, not Python's opinion.
-/

open PCS.V2.ProofGatedPolicy
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedCertCodec

def main : IO UInt32 := do
  let certPath : System.FilePath :=
    "../research/proof-gated-self-improvement-v1/v7_independent/governance_cross_policy_regression.pgsc6"
  let certFile ← IO.FS.readBinFile certPath
  let certificate := certFile.toList
  if certificate.length != 250 then
    IO.eprintln s!"FAIL: incorrect generated certificate length: {certificate.length}"
    return 1
  if (decodeCert certificate).isNone then
    IO.eprintln "FAIL: Lean PGSC6 decoder rejected independently generated canonical bytes"
    return 1

  -- Under an independently governed target change, this previously perfect
  -- model can regress relative to the *original* target.
  let expected := some (encodeBytes gen0)
  if runChecker malTarget 0 (encodeBytes gen3) certificate != expected then
    IO.eprintln "FAIL: actual Lean V7 checker did not authorize generated PGSC6 wire under changed policy"
    return 1
  if runChecker pinned0 0 (encodeBytes gen3) certificate != none then
    IO.eprintln "FAIL: actual Lean V7 checker authorized this regression under original pinned policy"
    return 1

  -- The actual verifier binds generation and incumbent; alternate requests
  -- cannot turn an otherwise authorized wire into a different transition.
  if runChecker malTarget 1 (encodeBytes gen3) certificate != none then
    IO.eprintln "FAIL: certificate replay accepted at stale generation"
    return 1
  if runChecker malTarget 0 (encodeBytes gen0) certificate != none then
    IO.eprintln "FAIL: substituted incumbent accepted"
    return 1
  let corrupted := certificate.set 0 (0 : UInt8)
  if runChecker malTarget 0 (encodeBytes gen3) corrupted != none then
    IO.eprintln "FAIL: malformed certificate accepted"
    return 1

  let pinnedFile ← IO.FS.readBinFile "fixtures/proof_gated/v7/policies/pinned0.pgpol7"
  let changedFile ← IO.FS.readBinFile "fixtures/proof_gated/v7/policies/mal_target.pgpol7"
  if decodePolicy pinnedFile.toList != some pinned0 ||
      decodePolicy changedFile.toList != some malTarget then
    IO.eprintln "FAIL: released canonical policy bytes do not match Lean definitions"
    return 1

  -- The untrusted request claims to be under the old policy and wrong state.
  -- The safe authority uses its own pinned policy, generation, and incumbent.
  let forgedRequest : Request :=
    ⟨encodePolicy pinned0, 938, encodeBytes gen0, certificate⟩
  if safeDecide malTarget 0 (encodeBytes gen3) forgedRequest != expected then
    IO.eprintln "FAIL: safe authority used request-supplied policy or generation/active"
    return 1
  if safeDecide pinned0 0 (encodeBytes gen3) forgedRequest != none then
    IO.eprintln "FAIL: safe authority bypassed original pinned policy"
    return 1

  IO.println "PASS: independent Python 250-byte PGSC6 replayed by real Lean V7 (changed policy accepted, original policy rejected; stale/forged/corrupt inputs rejected)"
  return 0
