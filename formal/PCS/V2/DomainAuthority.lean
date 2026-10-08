import PCS.V2.DomainAdapter
import PCS.V2.Frontier

/-!
# Flagship: raw canonical signed archive âŸ¶ domain-native semantic proposition

Two authoritative paths are covered.

1. **The production Lean authority, unchanged** (`acceptArchiveWithTranscript`, the function
   whose verdict `pcs-lean-authority --zip` prints).  `pcs_generic_domain_archive_acceptance_sound`
   composes `PCS.V2.Frontier.pcs_frontier_archive_acceptance_sound` (sole cryptographic
   hypothesis: `NoForgery` for the trust anchor) with `domain_adapter_sound`.  A domain
   whose leaf obligations are discharged by the six verified built-in checkers needs no
   further hypothesis (`â€¦_builtin`); a domain relying on transcript-reported external
   validators must state the meaning of those reports explicitly (`hExt`).

2. **The authority extended with domain checkers** (`acceptArchiveWithCheckers cs`): every
   domain registers proof-carrying `CertifiedChecker`s; the built-ins keep priority, so
   their semantics are preserved (`authorityValid_builtin`).  For `cs = []` this *is* the
   production authority (`acceptArchiveWithCheckers_nil`).  `ExtendedAssurance` re-derives
   the frontier conclusions for the extended executor under the same single hypothesis
   `NoForgery`.

Trusted / assumed (all visible in the theorem types): `NoForgery` for the Lean RFC 8032
verifier and the trust-anchor key; for path 1 or 2 with external validators, `hExt`!4T4 =¶ën…ªì