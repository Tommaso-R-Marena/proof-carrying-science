import PCS.V2.FailClosedProofs

/-!
# The executable authority runs the certified domain-checker registry

`pcs-lean-authority` (`PCSAuthority.lean`) now prints the verdict of
`executableAuthority` (raw `--zip` mode) / `executableAuthorityEntries` (directory mode).
Both run the **extended certified authority** `acceptArchiveWithCheckers cs` of
`PCS.V2.DomainAuthority`, where `cs` is built by the fail-closed registration function
`buildRegistry` from the production domain-checker list `productionCheckers`
(computational biology `residue_bounds`, `hydrophobic_score`; AI safety `trace_invariant`).

* `buildRegistry` accepts a list of `DomainChecker`s only if their tags are pairwise distinct
  and disjoint from the six built-in tags (`buildRegistry_eq_some_iff`); otherwise it returns
  `none` and the executable rejects **every** archive with stage `checker_registry`
  (`executableAuthorityWith_dup`).  A `DomainChecker` carries its soundness theorem as a
  field, so a checker without a formal soundness proof cannot even be written down.
* The six built-in checkers keep priority, so their meaning is unchanged
  (`executor_builtin_unchanged`); a request handled by no registered checker is executed
  exactly as by the production authority (`executor_unhandled_unchanged`).
* With an empty registry every executable `ACCEPT` is a production `ACCEPT`
  (`executableAuthorityWith_nil`); the converse fails exactly for transcript-trusted kinds.
* **Fail closed (current behaviour).**  The executed functions run the *strict* authority of
  `PCS.V2.FailClosed`: an evidence item whose `check_spec.type` is missing or unregistered is
  rejected before replay (stage `unsupported_check_type`), whatever the transcript reports;
  supported claims of registered domains must be bound by their own certified evidence
  (stage `claim_binding`); the replay fallback is the constant-`FAIL` executor, so transcript
  replay reports are never used as outcomes.  The earlier transcript-fallback extended
  authority (`acceptArchiveWithCheckers`) is kept as an analysis object: strict acceptance
  implies it (`certifiedAuthority_extended`), so its theorems still apply.
* `executableAuthority_refines_certifiedAuthority`: the executed function prints `ACCEPT`
  **iff** the certified strict authority `certifiedAuthority` accepts.
* `executableAuthority_sound`: `ACCEPT` â‡’ frontier-strength `ExtendedAssurance` plus the
  AI-safety and biology domain propositions for every domain-accepted claim, with
  `NoForgery` as the only hypothesis.
-/

set_option autoImplicit false

namespace PCS.V2.DomainAuthority

open PCS PCS.V2.Json PCS.V2.EndToEnd PCS.V2.Archive PCS.V2.Authority PCS.V2.HighAssurance
open PCS.V2.Zip PCS.V2.TCB PCS.V2.Package PCS.V2.CanonicalArchive PCS.V2.Replay PCS.V2.Signature
open PCS.V2.Checkers PCS.V2.CertificateModel PCS.V2.DomainAdapter PCS.V2.ClaimGraph
open PCS.V2.Index PCS.V2.Witnesses PCS.V2.PKPDCheck

/-! ## Oracle-generic transcript-gated acceptance and its diagnostic mirror -/

/-- Transcript-gated acceptance for arbitrary oracles. -/
def acceptPCSGated (O : Oracles) (t : AuthorityTranscript) (T : TrustAnchor)
    (inp : PackageInput) : Option AcceptedResult :=
  match acceptPCS O T inp with
  | none => none
  | some r => if transcriptCovers t r then some r else none

/-- Fail-closed diagnostic mirror of `acceptPCSGated` (same body as
    `diagnosePCSWithTranscript`, for arbitrary oracles). -/
def diagnosePCSGated (O : Oracles) (t : AuthorityTranscript) (T : TrustAnchor)
    (i4T4 =ýïÝœ…ªì