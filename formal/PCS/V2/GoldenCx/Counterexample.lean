import PCS.V2.GoldenCx.AuthorityStage
import PCS.V2.ZipComplete
import PCS.V2.ExecutableFailClosed
import PCS.V2.Witnesses.AISafetyCampaign
import PCS.V2.Golden.Acceptance

/-!
# The former counterexample: a correctly signed archive with an unregistered check type

The archive `cxRaw` (`PCS.V2.GoldenCx.Spec`) is consistently built and Ed25519-signed.  Its
claim `C1` asserts "trace `trace` never takes action `7` and its cumulative risk stays â‰¤ 4",
but the committed trace `[0, 1, 2, 4, 1, 7]` takes action `7`, and the evidence item `E1` uses
the **unregistered** tag `trace_invariant_v2`.

Before the fail-closed change the executable took `E1`'s replay outcome from the transcript
and printed `ACCEPT` (this is still true of the legacy extended authority:
`legacyAuthority_cx`, and it is why `legacy_no_unconditional_claim_bridge` holds).

Now (kernel-checked):

* `cx_package_valid` â€” both signatures verify and the evidence package is well formed;
* `cx_rejected`, `cx_entries_rejected`, `cx_cli_rejected` â€” the exact decision functions of
  `pcs-lean-authority` (zip mode on the concrete bytes, directory mode, both command-line
  wrappers) never print `ACCEPT`, for **every** transcript and every trust anchor / key
  string / pin.  Derived from the general theorem
  `PCS.V2.ExecutableFailClosed.executableAuthority_rejects_unregistered_type`.
-/

set_option autoImplicit false

namespace PCS.V2.GoldenCx

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.DomainAuthority PCS.V2.Zip
open PCS.V2.ClaimGraph PCS.V2.DomainAdapter PCS.V2.Witnesses PCS.V2.Witnesses.AISafety
open PCS.V2.Witnesses.AISafetyCampaign PCS.V2.Checkers PCS.V2.FailClosed PCS.V2.ExecutableFailClosed

/-- The seven archi4T4 =v×^œ…ªì