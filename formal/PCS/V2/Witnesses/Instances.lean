import PCS.V2.Witnesses.Biology
import PCS.V2.Witnesses.AISafety
import PCS.V2.Witnesses.MLEval
import PCS.V2.Proposer

/-!
# Witness instances: one authority registry, three domains, non-vacuity

* `witnessRegistry` registers the biology and AI-safety checkers together in one extended
  authority; `witnessRegistry_registered` discharges the registration conditions.
* `bio_assurance`, `ai_assurance` â€” the domain theorems for that concrete authority
  (sole hypothesis `NoForgery`); `ml_archive_sound` already applies to the unchanged
  production authority.
* Non-vacuity: concrete runs of each checker that PASS on good data and FAIL on bad data,
  and concrete obligation graphs accepted by the induced PCS obligation checker.  (The
  generic theorems are therefore not vacuous: the checkers and graph checker do accept
  real inputs.)
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses.Instances

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.ClaimGraph
open PCS.V2.DomainAdapter PCS.V2.DomainAuthority PCS.V2.Witnesses
open PCS.V2.Witnesses.Biology PCS.V2.Witnesses.AISafety PCS.V2.Witnesses.MLEval

def witnessRegistry : List DomainChecker := [boundsChecker, scoreChecker, traceChecker]

theorem witnessRegistry_registered : Registered witnessRegistry :=
  âŸ¨by decide, by decideâŸ©

theorem bio_assurance {t : PCS.V2.Authority.AuthorityTranscript}
    {T : PCS.V2.EndToEnd.TrustAnchor} {signed : List UInt8 â†’ Prop}
    (hB : PCS.V2.Signature.NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} {inp : PCS.V2.Package.PackageInput} {r : PCS.V2.EndToEnd.AcceptedResult}
    (h : acceptArchiveWithCheckers (registry witnessRegistry) t T raw = some (inp, r))
    {cid : String} {g : Graph String BioIR} {c : BioClaim}
    (hd : domainAccepts bioAdapter r cid g = some c) :
    âˆƒ sq st, artBytes r.table c.seqA = some sq âˆ§ artBytes r.table a4T4 =tçÎ…ªì