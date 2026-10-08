import PCS.V2.Golden.Stages
import PCS.V2.GoldenCx.Provenance2
import PCS.V2.GoldenCx.Crypto
import PCS.V2.ExecutableAuthority

/-!
# Kernel-checked stage-by-stage evaluation of the authority on the cx package

*Counterexample archive `cx` (`PCS.V2.GoldenCx.Spec`).*  This file is a mechanical
clone of the corresponding `PCS.V2.Golden` file with the fixture `golden` replaced by `cx`;
all generic lemmas are reused from `PCS.V2.Golden`.

Each lemma evaluates one stage of the production checker (`PCS.V2.EndToEnd.acceptPCS`
inside `PCS.V2.DomainAuthority.certifiedAuthority`) on the cx fixture.  Canonical-JSON
byte gates are discharged by the proved completeness theorem
`PCS.V2.Canonical.parseCanonicalBytes_complete` (the bytes are, by construction, the
canonical serialization of a canonical value), never by re-parsing; everything else is
kernel evaluation (`kernel_rfl`) of the production functions, after proved rewrites
(`sha256_eq_sha256Fast`, `PCS.V2.Golden.jcsBytes_data`, literal provenance lemmas).
-/

set_option autoImplicit false

namespace PCS.V2.GoldenCx

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd

/-- The certificate JSON value with literal hashes. -/
def certJV : JVal := .obj (cx.certMembers (hexEncode Lit.semHash) (hexEncode Lit.intHash))

/-- The parsed certificate. -/
def certV : CertV2 :=
  { members := cx.certMembers (hexEncode Lit.semHash) (hexEncode Lit.intHash),
    semanticHash := Lit.semHash, integrityHash := Lit.intHash }

theorem certBytes_jcs : cx.certBytes = jcsBytes certJV := by
  rw [FixtureSpec.certBytes, certJ_eq]; rfl

theorem certJV_canonical : canonical certJV = true := by kernel_rfl

theorem verifyCertBytes_cx : verifyCertBytes cx.certBytes = some certV := by
  have hs : (jcsBytes certJV).size ≤ maxCertificateBytes := by
    rw [← certBytes_jcs, certBytes_size]; decide
  rw [certBytes_jcs, verifyCertBytes, parseCanonicalBytes_complete certJV_canonical hs]
  simp only [certJV, certHashesOK, PCS.V2.Golden.domainDigest_eq, sha256_eq_sha256Fast]
  kernel_rfl

/-! ## Member bytes as literal byte arrays -/

def certBA : ByteArray := ⟨⟨Lit.certBytes⟩⟩
def wireBA : ByteArray := ⟨⟨Lit.wireBytes⟩⟩
def indexBA : ByteArray := ⟨⟨Lit.indexM��=��Z�