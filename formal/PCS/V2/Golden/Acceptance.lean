import PCS.V2.Golden.AuthorityStage
import PCS.V2.ZipComplete
import PCS.V2.Witnesses.AISafetyCampaign

/-!
# Kernel-checked acceptance of the committed golden AI-safety archive

This file closes the executable-to-kernel gap for the golden fixture
(`fixtures/ai_safety_golden/`): the exact function executed by `pcs-lean-authority --zip`
is proved, in Lean's trusted kernel, to print `ACCEPT` on the raw golden ZIP bytes
`goldenRaw`, and the bounded AI-safety property of the committed trace is derived from that
acceptance through the existing soundness theorems.

Chain (every arrow is a theorem):

```
goldenRaw (= canonical ZIP encoding of goldenEntries)
  ─ decodeZip_encodeZip + goldenEntries_sorted/_wellSized ─▶ decodeZip goldenRaw = some goldenEntries
  ─ fromArchiveEntries_golden ─▶ package input inputV (literal member bytes)
  ─ verifyPackage_golden (certificate, two Ed25519 signatures, manifest, file map)
  ─ acceptPCS_golden (certificate model, env, workflow, artifact table, certified
    trace_invariant replay, normalized index/wire) ─ transcriptCovers_golden
  ─▶ certifiedAuthority_golden : certifiedAuthority … goldenRaw = some (inputV, resultV)
  ─ executableAuthority_refines_certifiedAuthority ─▶ aiSafetyGoldenArchive_accepts
  ─ executableAuthority_domain_sound ─▶ aiSafetyGoldenArchive_committed_safe   (no FaithfulLog)
  ─ aiBridge.transport ─▶ aiSafetyGoldenArchive_deployed_safe                (needs FaithfulLog)
```

No `NoForgery` hypothesis is used or claimed: the signing key is the public RFC 8032 TEST 1
key, so signature verification here establishes *integrity relative to that published key*,
not provenance.
-/

set_option autoImplicit false

namespace PCS.V2.Golden

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.Replay PCS.V2.DomainAuthord�PЀL@��]�r�