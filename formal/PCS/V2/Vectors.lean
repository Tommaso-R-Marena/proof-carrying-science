import PCS.V2.Ed25519
import PCS.V2.Flagship

/-!
# Golden vectors and adversarial mutations (executable tests, not proofs)

The real PCS v0.6 golden package (`tests/v06_golden/`) is embedded byte-for-byte.
`#guard` runs the Lean checker on it — with the Lean Ed25519 specification, so both
signatures are genuinely verified — and on a family of adversarial mutations, each
of which must be rejected.  Known-answer vectors for SHA-256, SHA-512 and Ed25519
(RFC 8032 §7.1 test 1) validate the transcriptions.
-/

namespace PCS.V2.Vectors

open PCS.V2.Json PCS.V2.Hex PCS.V2.Package PCS.V2.Signature PCS.V2.Index PCS.V2.EndToEnd
open PCS.V2.Replay

def hx (s : String) : List UInt8 := (hexDecode s).getD []

/-! ## Primitive known-answer vectors -/

#guard hexEncode (PCS.V2.SHA256.sha256 "abc".toUTF8.data.toList) =
  "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
#guard hexEncode (PCS.V2.SHA256.sha256 []) =
  "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
#guard hexEncode (PCS.V2.SHA512.sha512 "abc".toUTF8.data.toList) =
  "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f"
#guard hexEncode (PCS.V2.SHA512.sha512 []) =
  "cf83e1357eefb8bdf1542850d66d8007d620e4050b5715dc83f4a921d36ce9ce47d0d13c5d85f2b0ff8318d2877eec2f63b931bd47417a81a538327af927da3e"

-- RFC 8032 §7.1, TEST 1.
def rfcPk : List UInt8 := hx "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
def rfcSig : List UInt8 := hx ("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155" ++
  "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")

#guard PCS.V2.Ed25519.verify rfcPk [] rfcSig
#guard !PCS.V2.Ed25519.verify rfcPk [0] rfcSig
#guard !PCS.V2.Ed25519.verify rfcPk [] (rfcSig.set 63 0x1b)

/-! ## The golden package -/

def certificateText : String :=
  "{\"artifacts\":[],\"assumptions\":[{\"id\":\"A1\",\"scope\":[\"C1\"],\"statement\":\"fixture assumption\"}],\"canonical_json_profile\":\"pcs-jcs-rfc8785-v1\",\"checker_version\":\"pcs-python-kernel/0.6.0-dev\",\"claims\":[{\"assessment\":{\"reason\":\"all declared computational checks passed\",\"status\":\"COMPUTATIONALLY_SUPPORTED\"},\"assumptions\":[\"A1\"],\"id\":\"C1\",\"kind\":\"computational\",\"predicate\":{\"products\":[{\"coefficient\":2,\"formula\":\"H2O\"}],\"reactants\":[{\"coefficient\":2,\"formula\":\"H2\"},{\"coefficient\":1,\"formula\":\"O2\"}],\"type\":\"reaction_balance\"},\"required_evidence\":[\"E1\"],\"statement\":\"The fixture reaction is atom-balanced.\"}],\"evidence\":[{\"artifact_ids\":[],\"check_spec\":{\"products\":[{\"coefficient\":2,\"formula\":\"H2O\"}],\"reactants\":[{\"coefficient\":2,\"formula\":\"H2\"},{\"coefficient\":1,\"formula\":\"O2\"}],\"type\":\"reaction_balance\"},\"checker\":\"pcs-python-kernel/0.6.0-dev\",\"claim_ids\":[\"C1\"],\"id\":\"E1\",\"kind\":\"computational_test\",\"outcome\":\"PASS\",\"predicate\":{\"products\":[{\"coefficient\":2,\"formula\":\"H2O\"}],\"reactants\":[{\"coefficient\":2,\"formula\":\"H2\"},{\"coefficient\":1,\"formula\":\"O2\"}],\"type\":\"reaction_balance\"}}],\"generated_at\":\"2026-09-29T00:00:00+00:00\",\"integrity_hash\":\"0274271466110e9ac5af500dcb5682880a89c4d3529f63b8141eb5b17e272509\",\"integrity_hash_format\":\"pcs-certificate-integrity-sha256-v2\",\"mission_scope\":\"cross-language byte-contract fixture\",\"semantic_hash\":\"f3471c37a7cb90caec88909f3a69de7285b2b74011ac8260741da1bb473d5998\",\"semantic_hash_format\":\"pcs-certificate-semantic-sha256-v2\",\"spec_version\":\"pcs-0.6\",\"subject\":\"PCS v0.6 byte-contract golden fixture\",\"workflow\":{\"nodes\":[]},\"workflow_summary\":{\"node_count\":0,\"topological_order\":[]}}"

def certificateSignatureText : String :=
  "{\"algorithm\":\"Ed25519\",\"payload\":{\"domain\":\"pcs-certificate-signature-v2\",\"format\":\"pcs-jcs-ed25519-payload-v1\",\"payload\":{\"canonical_json_profile\":\"pcs-jcs-rfc8785-v1\",\"checker_version\":\"pcs-python-kernel/0.6.0-dev\",\"integrity_hash\":\"0274271466110e9ac5af500dcb5682880a89c4d3529f63b8141eb5b17e272509\",\"integrity_hash_format\":\"pcs-certificate-integrity-sha256-v2\",\"semantic_hash\":\"f3471c37a7cb90caec88909f3a69de7285b2b74011ac8260741da1bb473d5998\",\"semantic_hash_format\":\"pcs-certificate-semantic-sha256-v2\",\"spec_version\":\"pcs-0.6\",\"subject\":\"PCS v0.6 byte-contract golden fixture\"}},\"payload_sha256\":\"419d0dc6aa0a33010d311a6f36370e5cce5757d6980424909dbca7017b97f941\",\"public_key_fingerprint\":\"65b60673d6ed884bf01c2c222d82ada0740f29ac3355d6a925c81f17f47a27b8\",\"signature\":\"LqaSH3CzWmruLLdeJ7155yqYowtldhkGGfhYao9MH/q3d+ueuw4BxG4w7StG0vrI9VpBTDHJLwbauhRjYPfiAQ==\",\"signature_format\":\"pcs-ed25519-jcs-v2\"}"

def manifestText : String :=
  "{\"canonical_json_profile\":\"pcs-jcs-rfc8785-v1\",\"certificate_integrity_hash\":\"0274271466110e9ac5af500dcb5682880a89c4d3529f63b8141eb5b17e272509\",\"certificate_integrity_hash_format\":\"pcs-certificate-integrity-sha256-v2\",\"certificate_semantic_hash\":\"f3471c37a7cb90caec88909f3a69de7285b2b74011ac8260741da1bb473d5998\",\"certificate_semantic_hash_format\":\"pcs-certificate-semantic-sha256-v2\",\"certificate_spec_version\":\"pcs-0.6\",\"files\":{\"artifacts/fixture.bin\":{\"sha256\":\"0fc7c8c357dfa2cc6116cdf1172b5734908a31644d6a807152023dd63d7f151a\",\"size\":17},\"certificate.json\":{\"sha256\":\"c84103750893d5a150372ada843b200d64608ed2d4bfac7b9f12de51966a031b\",\"size\":1631},\"normalized/ab861dc170dc2e43224e45278d3d31a675b9ebc34c9b0f48c066ca1eeaed8ee6.json\":{\"sha256\":\"1b98a9cc7624067b84e254698dc3d8ef6511d895b2da1f01853d68b67e06a17a\",\"size\":1059},\"normalized/index.json\":{\"sha256\":\"5599ff4b82c5b498b6661326d9b98828c7575a3b4b7f9cbc6db41aef8b002773\",\"size\":677}},\"package_format\":\"pcs-package-v2\"}"

def packageSignatureText : String :=
  "{\"algorithm\":\"Ed25519\",\"payload\":{\"domain\":\"pcs-package-signature-v2\",\"format\":\"pcs-jcs-ed25519-payload-v1\",\"payload\":{\"canonical_json_profile\":\"pcs-jcs-rfc8785-v1\",\"certificate_integrity_hash\":\"0274271466110e9ac5af500dcb5682880a89c4d3529f63b8141eb5b17e272509\",\"certificate_integrity_hash_format\":\"pcs-certificate-integrity-sha256-v2\",\"certificate_semantic_hash\":\"f3471c37a7cb90caec88909f3a69de7285b2b74011ac8260741da1bb473d5998\",\"certificate_semantic_hash_format\":\"pcs-certificate-semantic-sha256-v2\",\"certificate_spec_version\":\"pcs-0.6\",\"files\":{\"artifacts/fixture.bin\":{\"sha256\":\"0fc7c8c357dfa2cc6116cdf1172b5734908a31644d6a807152023dd63d7f151a\",\"size\":17},\"certificate.json\":{\"sha256\":\"c84103750893d5a150372ada843b200d64608ed2d4bfac7b9f12de51966a031b\",\"size\":1631},\"normalized/ab861dc170dc2e43224e45278d3d31a675b9ebc34c9b0f48c066ca1eeaed8ee6.json\":{\"sha256\":\"1b98a9cc7624067b84e254698dc3d8ef6511d895b2da1f01853d68b67e06a17a\",\"size\":1059},\"normalized/index.json\":{\"sha256\":\"5599ff4b82c5b498b6661326d9b98828c7575a3b4b7f9cbc6db41aef8b002773\",\"size\":677}},\"package_format\":\"pcs-package-v2\"}},\"payload_sha256\":\"321f1b90cc528c6d4e762fd8133199cfcb150a6f0006ab6297db911022ec951f\",\"public_key_fingerprint\":\"65b60673d6ed884bf01c2c222d82ada0740f29ac3355d6a925c81f17f47a27b8\",\"signature\":\"qBb43dmXebE6I9bSj8VmqZgsvVU3N4N9OTgumVluMucsHoHpuDghQ+RHHoLVfORDJPnyz5epcCdk2/Jbt3ZFDw==\",\"signature_format\":\"pcs-ed25519-jcs-v2\"}"

def indexText : String :=
  "{\"canonical_json_profile\":\"pcs-jcs-rfc8785-v1\",\"certificate_integrity_hash\":\"0274271466110e9ac5af500dcb5682880a89c4d3529f63b8141eb5b17e272509\",\"certificate_semantic_hash\":\"f3471c37a7cb90caec88909f3a69de7285b2b74011ac8260741da1bb473d5998\",\"entries\":[{\"claim_id\":\"C1\",\"decision\":\"COMPUTATIONALLY_SUPPORTED\",\"path\":\"normalized/ab861dc170dc2e43224e45278d3d31a675b9ebc34c9b0f48c066ca1eeaed8ee6.json\",\"wire_semantic_hash\":\"e7fe1b888698f8a06eba17e3f7d6d70142e08e2be2deb580e20c24411b3cd6a5\"}],\"index_format\":\"pcs-normalized-decision-index-v2\",\"index_hash_format\":\"pcs-normalized-index-sha256-v2\",\"index_semantic_hash\":\"19463c8ef3196ed3a9d4df9eefdcb7d13afbfadf8f20a55458e794afa074bafa\"}"

def wireText : String :=
  "{\"canonical_json_profile\":\"pcs-jcs-rfc8785-v1\",\"claim\":{\"assumptions\":[\"A1\"],\"id\":\"C1\",\"kind\":\"computational\",\"predicate_commitment\":\"pcs-predicate-sha256-v2:41cca8b472be635d5e56b4ca09adee5868438c4977ac4cf42b239c8ca2822db7\",\"required_evidence\":[\"E1\"]},\"context\":[{\"id\":\"A1\",\"statement\":\"fixture assumption\"}],\"decision\":\"COMPUTATIONALLY_SUPPORTED\",\"evidence\":[{\"id\":\"E1\",\"kind\":\"computational_test\",\"outcome\":\"PASS\",\"predicate_commitment\":\"pcs-predicate-sha256-v2:41cca8b472be635d5e56b4ca09adee5868438c4977ac4cf42b239c8ca2822db7\"}],\"predicate_hash_format\":\"pcs-predicate-sha256-v2\",\"source\":{\"certificate_integrity_hash\":\"0274271466110e9ac5af500dcb5682880a89c4d3529f63b8141eb5b17e272509\",\"certificate_semantic_hash\":\"f3471c37a7cb90caec88909f3a69de7285b2b74011ac8260741da1bb473d5998\",\"checker_version\":\"pcs-python-kernel/0.6.0-dev\",\"claim_id\":\"C1\",\"spec_version\":\"pcs-0.6\"},\"wire_format\":\"pcs-normalized-decision-v2\",\"wire_hash_format\":\"pcs-normalized-decision-sha256-v2\",\"wire_semantic_hash\":\"e7fe1b888698f8a06eba17e3f7d6d70142e08e2be2deb580e20c24411b3cd6a5\"}"

def fixtureBytes : ByteArray := ⟨#[102, 105, 120, 116, 117, 114, 101, 32, 97, 114, 116, 105, 102, 97, 99, 116, 10]⟩
def wirePath : String := "normalized/ab861dc170dc2e43224e45278d3d31a675b9ebc34c9b0f48c066ca1eeaed8ee6.json"

def goldenFiles : FileMap :=
  [("artifacts/fixture.bin", fixtureBytes), ("certificate.json", certificateText.toUTF8),
   (wirePath, wireText.toUTF8), ("normalized/index.json", indexText.toUTF8)]

def goldenInput : PackageInput :=
  { certificateBytes := certificateText.toUTF8,
    certificateSignatureBytes := certificateSignatureText.toUTF8,
    manifestBytes := manifestText.toUTF8, packageSignatureBytes := packageSignatureText.toUTF8,
    files := goldenFiles }

def goldenKey : List UInt8 :=
  (PCS.V2.Base64.decodeCanonical "ebVWLo/mVPlAeLES6KmLp5AfhTrmlb7X4OORC60ElmQ=").getD []

def goldenAnchor : TrustAnchor := { pk := goldenKey, expected := some (PCS.V2.SHA256.sha256 goldenKey) }

-- ASCII-only folding (all golden member names are ASCII).
def asciiUnicode : UnicodeOps := { nfc := id, casefold := fun s => String.map Char.toLower s }

/-- Oracles for the test run: real Lean Ed25519; the golden certificate declares no
    environment, no workflow nodes, and one `reaction_balance` evidence item recorded
    as a passing computational test. -/
def goldenOracles : Oracles :=
  { unicode := asciiUnicode, ed25519 := PCS.V2.Ed25519.verify, capture := fun _ => .null,
    workflow := fun _ _ => true, exec := fun _ => ⟨.computationalTest, .pass⟩ }

def accepts (O : Oracles) (T : TrustAnchor) (inp : PackageInput) : Bool := (acceptPCS O T inp).isSome

#guard (PCS.V2.Base64.decodeCanonical
  "LqaSH3CzWmruLLdeJ7155yqYowtldhkGGfhYao9MH/q3d+ueuw4BxG4w7StG0vrI9VpBTDHJLwbauhRjYPfiAQ==").isSome
#guard accepts goldenOracles goldenAnchor goldenInput

/-! ## Adversarial mutations (each must be rejected) -/

def replaceFirst (s pat rep : String) : String := s.replace pat rep

-- Non-canonical base64 signature spelling (the counterexample fixed in production).
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with certificateSignatureBytes :=
      (replaceFirst certificateSignatureText "AQ==\"" "AR==\"").toUTF8 }
-- Trailing newline after canonical JSON.
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with manifestBytes := (manifestText ++ "\n").toUTF8 }
-- Insignificant whitespace.
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with manifestBytes := (replaceFirst manifestText "{\"canonical" "{ \"canonical").toUTF8 }
-- Duplicate key.
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with manifestBytes :=
      (replaceFirst manifestText "{\"canonical_json_profile\":\"pcs-jcs-rfc8785-v1\","
        "{\"canonical_json_profile\":\"pcs-jcs-rfc8785-v1\",\"canonical_json_profile\":\"pcs-jcs-rfc8785-v1\",").toUTF8 }
-- Artifact substitution (one byte changed).
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with files := goldenFiles.map fun f =>
      if f.1 = "artifacts/fixture.bin" then (f.1, (ByteArray.mk #[0] ++ fixtureBytes)) else f }
-- Extra unsigned member.
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with files := goldenFiles ++ [("extra.txt", "x".toUTF8)] }
-- Missing signed member.
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with files := goldenFiles.filter (·.1 != "artifacts/fixture.bin") }
-- Case-colliding alias of a signed member.
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with files := goldenFiles ++ [("Certificate.json", certificateText.toUTF8)] }
-- Path traversal member.
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with files := goldenFiles ++ [("../evil", "x".toUTF8)] }
-- Signature-domain confusion: certificate signature record presented as package signature.
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with packageSignatureBytes := certificateSignatureText.toUTF8 }
-- Wrong trust anchor.
#guard !accepts goldenOracles { goldenAnchor with pk := rfcPk, expected := none } goldenInput
-- Wrong pinned fingerprint.
#guard !accepts goldenOracles { goldenAnchor with expected := some (PCS.V2.SHA256.sha256 rfcPk) }
  goldenInput
-- Replay disagrees with the recorded outcome.
#guard !accepts { goldenOracles with exec := fun _ => ⟨.computationalTest, .fail⟩ } goldenAnchor
  goldenInput
-- Workflow re-derivation fails.
#guard !accepts { goldenOracles with workflow := fun _ _ => false } goldenAnchor goldenInput
-- Normalized decision tampered (decision string changed).
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with files := goldenFiles.map fun f =>
      if f.1 = wirePath then
        (f.1, (replaceFirst wireText "\"decision\":\"COMPUTATIONALLY_SUPPORTED\""
          "\"decision\":\"OPEN\"").toUTF8)
      else f }
-- Index removed.
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with files := goldenFiles.filter (·.1 != "normalized/index.json") }
-- Certificate bytes differ from the signed member (claim statement changed).
#guard !accepts goldenOracles goldenAnchor
  { goldenInput with certificateBytes :=
      (replaceFirst certificateText "atom-balanced" "atom-balanced!").toUTF8 }

end PCS.V2.Vectors
