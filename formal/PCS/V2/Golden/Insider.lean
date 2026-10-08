import PCS.V2.Golden.Rejection

/-!
# Kernel-checked rejection of the insider-re-signed unsafe archive

The adversarial campaign's mutation `m1` (`PCS.V2.Witnesses.AISafetyCampaign.m1`) is the
golden fixture with the trace `[0, 1, 2, 4, 1, 7]` (forbidden action `7`) and a certificate
that is **consistently rebuilt** for that trace: correct artifact digest, correct semantic and
integrity hashes, correct normalized wire and index, a manifest over the new members, and the
evidence item `E1` recorded as a `PASS` `trace_invariant` replay.  Re-signed with the test
key it is exactly what an insider holding the signing key would produce.  The *original*
production authority (transcript-only replay) accepts it (`#guard` in the campaign file).

`insider_rejected_entries` / `insider_rejected_zip` prove in the kernel that the executable's
decision function rejects it **for every pair of signature byte strings**, every transcript
and every trust anchor: the rejection cannot be bypassed by any choice of key or signature,
because it follows from the general theorem
`executableAuthority_rejects_unsafe_trace_evidence` and the certificate's own content.

Only the certificate parse is evaluated (two SHA-256 domain digests, kernel-checked through
the proved fast SHA-256); no signature is evaluated, since the statement quantifies over all
signatures.
-/

set_option autoImplicit false

namespace PCS.V2.Golden.Insider

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Package PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Index
open PCS.V2.CertificateModel PCS.V2.Zip PCS.V2.DomainAuthority PCS.V2.Witnesses PCS.V2.Domains
open PCS.V2.Witnesses.AISafety PCS.V2.Witnesses.AISafetyGolden PCS.V2.PKPDCheck
open PCS.V2.Witnesses.AISafetyCampaign PCS.V2.ExecutableGeneral PCS.V2.SHA256 PCS.V2.Canonical
open PCS.V2.Golden

/-- Semantic hash of the insider certificate (checked below by kernel evaluation). -/
def semLit : List UInt8 :=
  [158, 210, 218, 170, 208, 248, 151, 190, 79, 76, 92, 25, 73, 187, 208, 103, 235, 166, 88, 4ÑPÐ€L@ý÷Ï…ªì