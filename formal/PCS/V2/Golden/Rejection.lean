import PCS.V2.Golden.Acceptance
import PCS.V2.ExecutableGeneral

/-!
# Kernel-checked rejection of a tampered golden archive

`tamperedRaw` is the canonical ZIP of the golden archive members with **only** the trace
member replaced by `[0, 1, 2, 4, 1, 7]`, which takes the forbidden action `7`.  The signed
certificate, both genuine Ed25519 signature records, the manifest, wire and index are the
original golden bytes (the "swapped artifact" attack).

`tamperedRaw_rejected` proves, in the kernel, that the function whose verdict
`pcs-lean-authority --zip` prints does **not** return `ACCEPT` on these bytes â€” for every
transcript and every trust anchor.  The proof evaluates no hash and no signature: it decodes
the ZIP (through the decoder-completeness theorem), partitions the members, reuses the golden
certificate parse, and applies the general rejection theorem
`executableAuthority_rejects_unsafe_trace_evidence`: the certificate records `E1` as a
`PASS` `trace_invariant` replay over artifact `trace`, whose archived bytes violate the
invariant, so no acceptance is possible.  (Operationally the compiled binary reports
`REJECT:package` â€” the manifest digest of the trace member no longer matches; the theorem does
not need to know which stage rejects.)
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Package PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Index
open PCS.V2.CertificateModel PCS.V2.Zip PCS.V2.DomainAuthority PCS.V2.Witnesses
open PCS.V2.Witnesses.AISafety PCS.V2.Witnesses.AISafetyGolden PCS.V2.PKPDCheck
open PCS.V2.ExecutableGeneral

/-- The tampered trace: the golden trace with its last action replaced by the forbidden `7`. -/
def tamperedTrace : ByteArray := âŸ¨#[0, 1, 2, 4, 1, 7]âŸ©

/-- The golden members with the trace member swapped. -/
def tamperedEntries : List (String Ã— ByteArray) :=
  [(tracePath, tamperedTrace), ("certificate.json", certBA), ("certificate_signature.json", certSigBA),
   (wirePath, wireBA), (indexPath, indexDÑPÐ€L@û÷}œ…ªì