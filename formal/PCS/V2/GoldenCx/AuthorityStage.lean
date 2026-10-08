import PCS.V2.Golden.AuthorityStage
import PCS.V2.GoldenCx.PackageStage2

/-!
# Counterexample fixture `cx`, stage 2: certificate model, replay, normalized set, transcript

*Counterexample archive `cx` (`PCS.V2.GoldenCx.Spec`).*  This file is a mechanical
clone of the corresponding `PCS.V2.Golden` file with the fixture `golden` replaced by `cx`;
all generic lemmas are reused from `PCS.V2.Golden`.

Kernel-checked evaluation of the remaining stages of `acceptPCSWithCheckers` (the
authority executed by `pcs-lean-authority`, with the certified domain-checker registry) on
the cx package input `inputV`, composed into
`acceptPCSWithCheckers_cx : acceptPCSWithCheckers certifiedRegistry cxTranscript
goldenAnchor inputV = some resultV`.

Composition lemmas (`PCS.V2.Golden.acceptPCS_of_stages`, `PCS.V2.Golden.verifyNormalizedSet_of_stages`, â€¦) are stated over
arbitrary inputs and proved by `simp` on hypotheses, so no concrete evaluation happens in the
elaborator; each concrete stage is a separate kernel-checked fact.
-/

set_option autoImplicit false

namespace PCS.V2.GoldenCx

open PCS PCS.V2.Json PCS.V2.Hex PCS.V2.Domains PCS.V2.Package PCS.V2.Signature PCS.V2.Canonical
open PCS.V2.Witnesses.AISafetyGolden PCS.V2.SHA256 PCS.V2.Index PCS.V2.CertificateModel
open PCS.V2.EndToEnd PCS.V2.Authority PCS.V2.SplitOnFuel PCS.V2.SHA256Memo PCS.V2.Replay
open PCS.V2.NormalizedWire PCS.V2.DomainAuthority PCS.V2.Checkers

/-! ## Generic composition lemmas (arbitrary inputs) -/

/-! ## Certificate model, environment, workflow, artifact table, replay -/

/-- The oracles of the executable authority for the cx transcript. -/
abbrev authO : Oracles := authorityOraclesWith certifiedRegistry cxTranscript

/-- The decoded certificate model. -/
def modelV : CertModel := (decodeCertModel certV).getD âŸ¨"", [], [], [], []âŸ©

theorem decodeCertModel_cx : decodeCertModel certV = some modelV := by ketÑPÐ€L@ýß®…ªì