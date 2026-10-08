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
`PCS.V2.Ed25519Sign.sign` with the **published RFC 8032 Â§7.1 TEST 1 secret seed**
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

/-- RFC 8032 Â§7.1 TEST 1 secret seed (published test vector; **not** a secret). -/
def testSeed : List UInt8 := hx "9d61b19dÑPÐ€L@õëŽ¸r«