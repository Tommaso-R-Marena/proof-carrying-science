import PCS.V2.ExecutableFailClosed
import PCS.V2.Witnesses.AISafetyCampaign
import PCS.V2.Golden.Insider

/-!
# Kernel-checked adversarial fixtures for the fail-closed gates

Each fixture is a consistently built certificate (correct artifact digest, semantic and
integrity hashes, normalized wire and index, manifest over the members) that an insider
holding the signing key would sign.  For each, the theorems below hold **for every pair of
signature byte strings** (in particular the genuine signatures; the campaign file checks by
evaluation that those verify), every transcript (in particular one reporting `PASS` for every
evidence item) and every trust anchor:

* `m7`  â€” unregistered tag `trace_invariant_v2` over the **safe** golden trace;
* `m7b` â€” `check_spec` with **no `type` field**;
* `m7c` â€” the golden evidence plus an **unrequired** evidence item `E2` of unregistered type `external_python`, recorded `PASS`;
  these three are rejected by the check-type gate
  (`PCS.V2.ExecutableFailClosed.executableAuthority_rejects_unregistered_type`);
* `m15` â€” claim/evidence predicates with budget 2 but a certified `check_spec` with budget 4 (registered tag; the claim is false of the
  committed trace, whose cumulative risk is 4).  Rejected because a supported AI-safety claim
  that is false of the delivered bytes can never be accepted
  (`PCS.V2.ExecutableFailClosed.executableAuthority_rejects_false_supported_ai_claim`).

Only certificate parsing is evaluated in the kernel (two SHA-256 domain digests per fixture,
through the proved fast SHA-256); no signature is evaluated, because the statements quantify
over all signatures.  The hash literals were printed by `tools/PrintFailClosedLiterals.lean`
and are re-checked here by the kernel.
-/

set_option autoImplicit false

namespace PCS.V2.Golden.FailClosedFixtures

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Package PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Index
open PCS.V2.CertificateModel PCS.V2.Zip PCS.V2.DomainAuthority PCS.V2.Witnesses PCS.V2.Domains
open PCS.V2.Witnesses.AISafety PCS.V2.Witnesses.AISafetyGolden PCS.V2.PKPDCheck
open PCS.V2.Witnesses.AISafetyCampaign PCS.V2.SHA256 PCS.V2.Canonical PCS.V2.FailClosed
open PCS.V2.ExecutableFailClosed

/-- An evidence check type outside the registered list yields an offending evidence item. -/
theorem bad_of_types {m : CertModel} {o : Option StMÄnuã‡!j»