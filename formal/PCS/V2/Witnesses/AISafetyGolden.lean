import PCS.V2.ExecutableAuthority
import PCS.V2.Ed25519Sign

/-!
# A genuinely signed golden AI-safety PCS archive

Everything here is deterministic.  The golden archive commits one bounded agent trace and
one certificate claim `C1`:

* trace artifact `trace` = `artifacts/agent_trace.bin`, bytes `[0, 1, 2, 4, 1, 8]`
  (one action code per byte; the risk of action `a` is `a mod 4`: risks `0,1,2,0,1,0`);
* declared forbidden action `7`, cumulative-risk budget `4`;
* claim predicate `{"budget":4,"forbidden":7,"kind":"ai.trace_invariant","trace_artifact":"trace"}`;
* one evidence item `E1` with `check_spec.type = "trace_invariant"` (the certified AI-safety
  checker registered in the executable authority).

`build` is a parameterised archive builder (`FixtureSpec`) used for the golden archive and
for the adversarial mutations of `PCS.V2.Witnesses.AISafetyCampaign`.  All hashes are
computed by the same Lean functions the verifier uses, the manifest and signature records
by the production encoders, and the Ed25519 signatures by the RFC 8032 signer
`PCS.V2.Ed25519Sign.sign` with the **published RFC 8032 §7.1 TEST 1 secret seed**
(test-only key; public key `testPk`).  The signer is untrusted: the golden signatures are
stored as literals (`goldenCertSig`, `goldenPkgSig`) and are checked by the authoritative
verifier like any other signature.

The golden canonical ZIP bytes are `goldenRaw = encodeZip goldenEntries`.
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses.AISafetyGolden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Package PCS.V2.Signature PCS.V2.Index PCS.V2.EndToEnd
open PCS.V2.Replay PCS.V2.Domains PCS.V2.Authority PCS.V2.CertificateModel PCS.V2.Common

def hx (s : String) : List UInt8 := (hexDecode s).getD []

/-! ## Test-only key -/

/-- RFC 8032 §7.1 TEST 1 secret seed (published test vector; **not** a secret). -/
def testSeed : List UInt8 := hx "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"

/-- RFC 8032 §7.1 TEST 1 public key. -/
def testPk : List UInt8 := hx "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"

/-- The trust anchor: the test public key, pinned by its SHA-256 fingerprint. -/
def goldenAnchor : TrustAnchor := { pk := testPk, expected := some (fingerprintOf testPk) }

/-! ## Parameterised fixture builder -/

def checkerVersion : String := "pcs-python-kernel/0.6.0-ai-safety-golden"
def traceId : String := "trace"
def tracePath : String := "artifacts/agent_trace.bin"

def predJ (budget forbidden : Nat) : JVal :=
  .obj [("budget", .num budget), ("forbidden", .num forbidden),
        ("kind", .str "ai.trace_invariant"), ("trace_artifact", .str traceId)]

def checkSpecJ (tag : String) (budget forbidden : Nat) : JVal :=
  .obj [("budget", .num budget), ("forbidden", .num forbidden),
        ("trace_artifact", .str traceId), ("type", .str tag)]

def wirePath : String := keyPath (storageKey "C1")

/-- Everything a fixture variant may change. -/
structure FixtureSpec where
  trace : ByteArray := ⟨#[0, 1, 2, 4, 1, 8]⟩
  /-- budget / forbidden action in the claim predicate -/
  claimBudget : Nat := 4
  claimForbidden : Nat := 7
  /-- budget / forbidden action in the evidence predicate and check spec -/
  evBudget : Nat := 4
  evForbidden : Nat := 7
  checkTag : String := "trace_invariant"
  /-- the evidence ids the claim requires -/
  required : List String := ["E1"]
  /-- whether the evidence item is present in the certificate -/
  withEvidence : Bool := true
  /-- digest recorded for the trace artifact (`none`: the true digest) -/
  artifactDigest : Option (List UInt8) := none
  /-- replaces the evidence `check_spec` object (`none`: the spec built from `checkTag`,
      `evBudget`, `evForbidden`) -/
  checkSpecOverride : Option JVal := none
  /-- additional evidence objects (id, JSON) appended to the certificate evidence list;
      the transcript reports `PASS` for each -/
  extraEvidence : List (String × JVal) := []

def golden : FixtureSpec := {}

namespace FixtureSpec

variable (s : FixtureSpec)

def evidenceJ : JVal :=
  .obj [("artifact_ids", .arr [.str traceId]),
        ("check_spec", s.checkSpecOverride.getD (checkSpecJ s.checkTag s.evBudget s.evForbidden)),
        ("checker", .str checkerVersion), ("claim_ids", .arr [.str "C1"]), ("id", .str "E1"),
        ("kind", .str "computational_test"), ("outcome", .str "PASS"),
        ("predicate", predJ s.evBudget s.evForbidden)]

def claimJ : JVal :=
  .obj [("assessment", .obj [("reason", .str "certified trace_invariant replay passed"),
                             ("status", .str "COMPUTATIONALLY_SUPPORTED")]),
        ("assumptions", .arr [.str "A1"]), ("id", .str "C1"), ("kind", .str "computational"),
        ("predicate", predJ s.claimBudget s.claimForbidden),
        ("required_evidence", .arr (s.required.map JVal.str)),
        ("statement", .str "The committed agent trace never takes the forbidden action and its cumulative risk stays within the budget after every step.")]

def assumptionJ : JVal :=
  .obj [("id", .str "A1"), ("scope", .arr [.str "C1"]),
        ("statement", .str "Risk of action a is a mod 4 (declared toy cost model).")]

def artifactJ : JVal :=
  .obj [("id", .str traceId), ("path", .str tracePath),
        ("sha256", .str (hexEncode (s.artifactDigest.getD (PCS.V2.SHA256.sha256 s.trace.data.toList))))]

/-- Certificate members with given semantic / integrity hash strings. -/
def certMembers (sh ih : String) : List (String × JVal) :=
  [("artifacts", .arr [s.artifactJ]), ("assumptions", .arr [assumptionJ]),
   ("canonical_json_profile", .str certProfile), ("checker_version", .str checkerVersion),
   ("claims", .arr [s.claimJ]), ("evidence", .arr ((if s.withEvidence then [s.evidenceJ] else []) ++ s.extraEvidence.map (·.2))),
   ("generated_at", .str "2026-10-05T00:00:00+00:00"), ("integrity_hash", .str ih),
   ("integrity_hash_format", .str certificateIntegrityDomain),
   ("mission_scope", .str "bounded AI-safety trace audit (golden fixture)"),
   ("semantic_hash", .str sh), ("semantic_hash_format", .str certificateSemanticDomain),
   ("spec_version", .str certSpecVersion), ("subject", .str "PCS AI-safety golden fixture"),
   ("workflow", .obj [("nodes", .arr [])]),
   ("workflow_summary", .obj [("node_count", .num 0), ("topological_order", .arr [])])]

def semHash : List UInt8 :=
  domainDigest certificateSemanticDomain (semanticProjection (s.certMembers "" ""))
def intHash : List UInt8 :=
  domainDigest certificateIntegrityDomain (integrityProjection (s.certMembers (hexEncode s.semHash) ""))

def certJ : JVal := .obj (s.certMembers (hexEncode s.semHash) (hexEncode s.intHash))
def certBytes : ByteArray := jcsBytes s.certJ

/-- The parsed certificate (as the verifier sees it). -/
def certV2 : CertV2 := { members := s.certMembers (hexEncode s.semHash) (hexEncode s.intHash),
                         semanticHash := s.semHash, integrityHash := s.intHash }

def certModel : CertModel := (decodeCertModel s.certV2).getD ⟨"", [], [], [], []⟩

def wire : NormalizedWire.WireV2 :=
  (match s.certModel.claims with
   | cl :: _ => deriveWire s.certV2 s.certModel cl
   | [] => none).getD
   { source := ⟨"", [], [], ""⟩, context := [], claim := ⟨"", .formal, [], [], []⟩,
     evidence := [], decision := .open_, wireSemanticHash := [] }

def wireBytes : ByteArray := NormalizedWire.encodedBytes s.wire
def index : IndexV2 :=
  let i0 : IndexV2 :=
    { certificateIntegrityHash := s.intHash, certificateSemanticHash := s.semHash,
      entries := [{ claimId := "C1", decision := .computational, storageKey := storageKey "C1",
                    wireSemanticHash := s.wire.wireSemanticHash }],
      indexSemanticHash := [] }
  { i0 with indexSemanticHash := Index.expectedHash i0 }
def indexBytes : ByteArray := jcsBytes (encodeIndex s.index)

/-- The signed (non-control) members, in canonical order. -/
def files : FileMap :=
  [(tracePath, s.trace), ("certificate.json", s.certBytes), (wirePath, s.wireBytes),
   (indexPath, s.indexBytes)]

def manifest : ManifestV2 :=
  { certSemanticHash := s.semHash, certIntegrityHash := s.intHash,
    files := s.files.map (fun f => (f.1, ⟨PCS.V2.SHA256.sha256 f.2.data.toList, f.2.size⟩)) }
def manifestBytes : ByteArray := jcsBytes (encodeManifest s.manifest)

def certSigPayloadJ : JVal := (certSigPayload s.certV2).getD .null
def certMsg : List UInt8 := signedMessage certificateSignatureDomain s.certSigPayloadJ
def pkgMsg : List UInt8 := signedMessage packageSignatureDomain (encodeManifest s.manifest)

def sigRecord (d : String) (p : JVal) (sg : List UInt8) : SigRecordV2 :=
  { domain := d, payload := p, payloadSha256 := PCS.V2.SHA256.sha256 (signedMessage d p),
    fingerprint := fingerprintOf testPk, signature := sg }

def certSigBytesWith (sg : List UInt8) : ByteArray :=
  jcsBytes (encodeSigRecord (sigRecord certificateSignatureDomain s.certSigPayloadJ sg))
def pkgSigBytesWith (sg : List UInt8) : ByteArray :=
  jcsBytes (encodeSigRecord (sigRecord packageSignatureDomain (encodeManifest s.manifest) sg))

/-- Archive members with the given certificate / package signatures. -/
def entriesWith (csig psig : List UInt8) : List (String × ByteArray) :=
  [(tracePath, s.trace), ("certificate.json", s.certBytes),
   ("certificate_signature.json", s.certSigBytesWith csig), (wirePath, s.wireBytes),
   (indexPath, s.indexBytes), ("package_manifest.json", s.manifestBytes),
   ("package_signature.json", s.pkgSigBytesWith psig)]

/-- Generator only (untrusted): RFC 8032 signatures under the test seed. -/
def genCertSig : List UInt8 := PCS.V2.Ed25519Sign.sign testSeed s.certMsg
def genPkgSig : List UInt8 := PCS.V2.Ed25519Sign.sign testSeed s.pkgMsg

/-- A consistently re-signed archive for this spec ("insider holding the test key"). -/
def build : ByteArray := ⟨(PCS.V2.Zip.encodeZip (s.entriesWith s.genCertSig s.genPkgSig)).toArray⟩

/-- The matching transcript (binds the certificate semantic hash; reports PASS for `E1`). -/
def transcript : AuthorityTranscript :=
  { certificateSemanticHash := s.semHash, checkerVersion := checkerVersion, workflowOk := true,
    environmentCapture := .null,
    replay := (if s.withEvidence then [⟨"E1", .computationalTest, .pass⟩] else []) ++
      s.extraEvidence.map (fun e => ⟨e.1, .computationalTest, .pass⟩),
    workflowAnalysis := [] }

end FixtureSpec

/-! ## The golden archive -/

def traceBytes : ByteArray := golden.trace
def budget : Nat := golden.claimBudget
def forbidden : Nat := golden.claimForbidden
def semHash : List UInt8 := golden.semHash

/-- The committed certificate signature (literal; produced once by the generator). -/
def goldenCertSig : List UInt8 :=
  hx ("d512512de8089e6c7f1b4485d2de9259054c2bccb2fa8dfb3965b81f56f0d0ff" ++
      "158ded1f1001dbf5faf904e90447f711ef1ab10c85d720712852363015be9605")

/-- The committed package signature (literal; produced once by the generator). -/
def goldenPkgSig : List UInt8 :=
  hx ("49043696817e20d2db58328514b6bce168a482015482cd2a712bce989efd250f" ++
      "6b35f23f45bd2419d03f79fbbdc3bdc22c59251899e1c981941a8de224363504")

/-- All archive members, in canonical (strictly sorted) order. -/
def goldenEntries : List (String × ByteArray) := golden.entriesWith goldenCertSig goldenPkgSig

/-- **The raw canonical signed ZIP bytes of the golden archive.** -/
def goldenRaw : ByteArray := ⟨(PCS.V2.Zip.encodeZip goldenEntries).toArray⟩

/-- The authority observation transcript for the golden archive.  The only evidence item
    is handled by the certified `trace_invariant` checker, so the executable authority
    computes its replay outcome itself and ignores the transcript's report for it. -/
def goldenTranscript : AuthorityTranscript := golden.transcript

/-- The transcript as canonical JSON (the file handed to `pcs-lean-authority`). -/
def goldenTranscriptJ : JVal :=
  .obj [("certificate_semantic_hash", .str (hexEncode semHash)),
        ("checker_version", .str checkerVersion), ("environment_capture", .null),
        ("format", .str authorityTranscriptFormat),
        ("replay", .arr [.obj [("evidence_id", .str "E1"), ("kind", .str "computational_test"),
                               ("outcome", .str "PASS")]]),
        ("workflow_ok", .bool true)]

def goldenTranscriptBytes : ByteArray := jcsBytes goldenTranscriptJ

end PCS.V2.Witnesses.AISafetyGolden
