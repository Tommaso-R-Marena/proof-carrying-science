import PCS.V2.AuthorityCLI
import PCS.V2.Witnesses.AISafetyDeployment

/-!
# What the executable's `ACCEPT` means for *arbitrary* archives and transcripts

This file connects the exact pure decision functions run by `pcs-lean-authority`
(`executableAuthority` for `--zip`, `executableAuthorityEntries` for directory mode, and the
command-line wrappers `AuthorityCLI.zipModeOutput` / `dirModeOutput`) to the bounded
AI-safety invariant `TraceSafe`, for **every** input: every raw byte string, every
transcript, every public key and fingerprint pin.

## What already existed, and what was missing

* `executableAuthority_refines_certifiedAuthority`: `ACCEPT` ⇔ the certified extended
  authority accepts.
* `executableAuthority_domain_sound`: `ACCEPT` ⇒ every AI-safety claim that is
  *domain-accepted with some obligation graph* holds of the committed traces.

The second theorem is general, but its conclusion is gated by `domainAccepts`, a check the
executable never runs (the obligation graph is not an input of `pcs-lean-authority`).  The
missing bridge was therefore a statement about the executable's verdict **alone**, phrased in
terms of the bytes the executable actually reads.  This file proves it:

* `executableAuthority_registered_evidence_sound` (domain-independent): `ACCEPT` ⇒ for every
  evidence item that the signed certificate records as `PASS` and whose `check_spec.type` is
  the tag of a registered certified checker, that checker's soundness proposition holds of
  the committed artifacts.  No `NoForgery`, no assumption on the transcript.
* `executableAuthority_trace_evidence_sound` (AI safety): `ACCEPT` ⇒ for every `PASS`
  evidence item tagged `trace_invariant` with parameters `(a, b, f)`, the archive member
  holding artifact `a` — its exact bytes in the decoded raw ZIP — satisfies
  `TraceSafe · b f`.
* `executableAuthority_trace_claim_sound`: the claim-level form (a certificate claim whose
  predicate decodes to "trace `a` is safe for budget `b`, forbidden action `f`" and which
  requires such a `PASS` evidence item) — derived through the *existing*
  `executableAuthority_domain_sound` via a canonical one-leaf obligation graph that is
  shown to be domain-accepted.
* `executableAuthority_rejects_unsafe_trace_evidence` (and the directory-mode and CLI
  forms): the contrapositive, stated purely in terms of **pre-acceptance parsing** of the
  input bytes.  Any archive whose certificate records a `PASS` `trace_invariant` evidence
  item over a member whose bytes violate the invariant is rejected — for every transcript and
  every trust anchor, i.e. no matter who signed it.

## Why the general result must be conditional (proved obstructions)

* **(Historical; now repaired.)**  For the earlier transcript-fallback authority,
  `PCS.V2.GoldenCx.legacy_no_unconditional_claim_bridge` (kernel-checked) exhibits a
  consistently signed archive it accepts whose AI-safety claim predicate is false of the
  committed trace (evidence tag `trace_invariant_v2`, `PASS` taken from the transcript).  The
  strict executable rejects that archive (`PCS.V2.GoldenCx.cx_rejected`), and for it the
  graph-free claim-level bridge for *supported* claims is proved:
  `PCS.V2.ExecutableFailClosed.executableAuthority_supported_claims_sound`.
* `ACCEPT` alone does not imply that any trace is safe: acceptance means the certificate is
  *honest about its replays*, not that its outcomes are positive.  A `FAIL`-recorded
  certified item over an unsafe trace is reproduced as!4T4 =�｜���