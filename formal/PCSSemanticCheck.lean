import PCS.V2.TranslationJson
import PCS.V2.SemanticFeedback
import PCS.V2.TranslationV3Json
import PCS.V2.EntailmentV3

/-!
`pcs-semantic-check` — executable front end of PCS Semantic Translation Contract v1.

    pcs-semantic-check <authority.json> <request.json>
        prints the canonical-JSON decision of `PCS.V2.Semantic.semanticCheck` (verdict,
        structured diagnostics, expected Lean source, and — only when accepted — the derived
        Explanation IR and its literal rendering); exit code 0 iff ACCEPTED, 1 otherwise.

    pcs-semantic-check --explain <authority.json> <claim.json>
        Lean → human direction: prints the Explanation IR, the deterministic literal English
        rendering and the Lean rendering of a structured claim, together with its well-typedness
        under the approved registry.  The English text is presentation only.

    pcs-semantic-check --v2 <authority.json> <request-v2.json>
        Semantic Intelligence v2: prints the canonical-JSON decision of
        `PCS.V2.Semantic.semanticCheckV2` (outcome, semantic status with the checked certificate
        or verified countermodel, diagnostics, repair obligations, explanation views).
        Exit code 0 iff CERTIFIED_TRANSLATION, 3 iff VERIFIED_COUNTEREXAMPLE, 1 otherwise.

    pcs-semantic-check --v2-record <authority.json> <request-v2.json> <provenance> <revision>
        prints the `pcs-verifier-feedback-v1` training record of the same decision.

    pcs-semantic-check --v3-strengthen <authority-v3.json> <request-v3.json> <ledger-state.json>
        Separate, explicitly authorized STRENGTHENING mode (`decideStrengtheningV3`): outcome
        CERTIFIED_STRENGTHENING (exit 4, never 0) iff the candidate logically implies the selected
        interpretation, the confirmation-role receipts attest a "strengthening-authorization"
        statement binding the exact candidate, and all receipts pass the stateful ledger
        protocol.  This is NOT a meaning-preserving translation.

    pcs-semantic-check --v3 <authority-v3.json> <request-v3.json> <ledger-state.json>
        Semantic Intelligence v3 (PRODUCTION mode): the state-aware decision
        `PCS.V2.Semantic.V3.semanticCheckV3` with replay-protected receipt envelopes.  Prints the
        canonical-JSON decision including the receipt phase, the nonces to consume and the new
        ledger.  The binary itself does NOT persist anything: the caller (the persistent receipt
        store) must commit `consumed_nonces` atomically before releasing a certified result.
        Exit code 0 iff CERTIFIED_TRANSLATION, 3 iff VERIFIED_COUNTEREXAMPLE, 1 otherwise.

    The v1 (`<authority.json> <request.json>`) and `--v2` modes validate stateless receipts and are
    NON-PRODUCTION modes: they provide no replay protection and must not be used as an authority.

    pcs-semantic-check --check-countermodel <authority.json> <bundle.json>
        independently re-verifies a serialized countermodel (`checkCountermodelBundle`);
        prints VALID_COUNTERMODEL (exit 0) or INVALID_COUNTERMODEL (exit 1).

The verdict printed is the one computed by the pure function `semanticCheck`, whose decision is
proved equal to the certified checker's (`semanticCheck_decision`, `semanticCheck_accepted_iff`).
The compiler, runtime and file IO remain trusted.
-/

open PCS.V2.Semantic PCS.V2.Json PCS.V2.Canonical

def explainOutput (authorityRaw claimRaw : ByteArray) : Option String :=
  match (parseCanonicalBytes maxInputBytes authorityRaw).bind decAuthorityConfig,
    (parseCanonicalBytes maxInputBytes claimRaw).bind decClaim with
  | some cfg, some c =>
    let R := cfg.registry
    let e := toExplanation R c
    some (String.ofList (ser (.obj [
      ("explanation", encExplanation e),
      ("explanation_literal", .str e.renderLiteral),
      ("free_variables", encStrs c.freeVars),
      ("lean_source", .str (renderClaimLean R c)),
      ("schema", .str "pcs-semantic-explanation-v1"),
      ("unsupported_constructs", encStrs c.unsupportedTags),
      ("well_typed", .bool (c.wellTypedB R && R.wellFormedB))])))
  | _, _ => none

def main (args : List String) : IO UInt32 := do
  match args with
  | ["--explain", authorityPath, claimPath] =>
    let a ← IO.FS.readBinFile authorityPath
    let c ← IO.FS.readBinFile claimPath
    match explainOutput a c with
    | some out => IO.println out; return 0
    | none => IO.eprintln "MALFORMED_INPUT: authority or claim is not canonical JSON of the expected schema"; return 1
  | ["--v2", authorityPath, requestPath] =>
    let a ← IO.FS.readBinFile authorityPath
    let r ← IO.FS.readBinFile requestPath
    let res := semanticCheckV2 a r
    let cfg := (parseCanonicalBytes maxInputBytes a).bind decAuthorityConfig
    IO.println (String.ofList (ser (encCliResultV2 cfg res)))
    return (match res.decision.outcome with
      | .certifiedTranslation => 0
      | .verifiedCounterexample => 3
      | _ => 1)
  | ["--v2-record", authorityPath, requestPath, provenance, revision] =>
    let a ← IO.FS.readBinFile authorityPath
    let r ← IO.FS.readBinFile requestPath
    match (parseCanonicalBytes maxInputBytes a).bind decAuthorityConfig,
      (parseCanonicalBytes maxInputBytes r).bind decRequestV2 with
    | some cfg, some req =>
      let res := semanticCheckV2 a r
      IO.println (String.ofList (ser (trainingRecord cfg req res.decision provenance revision)))
      return 0
    | _, _ => IO.eprintln "MALFORMED_INPUT"; return 1
  | ["--v3", authorityPath, requestPath, statePath] =>
    let a ← IO.FS.readBinFile authorityPath
    let r ← IO.FS.readBinFile requestPath
    let st ← IO.FS.readBinFile statePath
    let res := PCS.V2.Semantic.V3.semanticCheckV3 a r st
    IO.println (String.ofList (ser (PCS.V2.Semantic.V3.encCliResultV3 res)))
    return (match res.decision.outcome with
      | .certifiedTranslation => 0
      | .verifiedCounterexample => 3
      | _ => 1)
  | ["--v3-strengthen", authorityPath, requestPath, statePath] =>
    let a ← IO.FS.readBinFile authorityPath
    let r ← IO.FS.readBinFile requestPath
    let st ← IO.FS.readBinFile statePath
    let res := PCS.V2.Semantic.V3.strengthenCheckV3 a r st
    IO.println (String.ofList (ser (PCS.V2.Semantic.V3.encStrengthResult res)))
    -- exit 4 (never 0): a strengthening is not a certified translation
    return (match res.1 with
      | .certifiedStrengthening => 4
      | _ => 1)
  | ["--check-countermodel", authorityPath, bundlePath] =>
    let a ← IO.FS.readBinFile authorityPath
    let b ← IO.FS.readBinFile bundlePath
    match checkCountermodelBundle a b with
    | some true => IO.println "VALID_COUNTERMODEL"; return 0
    | some false => IO.println "INVALID_COUNTERMODEL"; return 1
    | none => IO.println "INVALID_COUNTERMODEL: malformed input"; return 1
  | [authorityPath, requestPath] =>
    let a ← IO.FS.readBinFile authorityPath
    let r ← IO.FS.readBinFile requestPath
    let res := semanticCheck a r
    IO.println (renderCliResult res)
    return (if res.decision.verdict = .accepted then 0 else 1)
  | _ =>
    IO.eprintln ("usage: pcs-semantic-check <authority.json> <request.json>\n" ++
      "       pcs-semantic-check --explain <authority.json> <claim.json>\n" ++
      "       pcs-semantic-check --v2 <authority.json> <request-v2.json>\n" ++
      "       pcs-semantic-check --v2-record <authority.json> <request-v2.json> <provenance> <revision>\n" ++
      "       pcs-semantic-check --v3-strengthen <authority-v3.json> <request-v3.json> <ledger-state.json>\n" ++
      "       pcs-semantic-check --v3 <authority-v3.json> <request-v3.json> <ledger-state.json>
        Semantic Intelligence v3 (PRODUCTION mode): the state-aware decision
        `PCS.V2.Semantic.V3.semanticCheckV3` with replay-protected receipt envelopes.  Prints the
        canonical-JSON decision including the receipt phase, the nonces to consume and the new
        ledger.  The binary itself does NOT persist anything: the caller (the persistent receipt
        store) must commit `consumed_nonces` atomically before releasing a certified result.
        Exit code 0 iff CERTIFIED_TRANSLATION, 3 iff VERIFIED_COUNTEREXAMPLE, 1 otherwise.

    The v1 (`<authority.json> <request.json>`) and `--v2` modes validate stateless receipts and are
    NON-PRODUCTION modes: they provide no replay protection and must not be used as an authority.

    pcs-semantic-check --check-countermodel <authority.json> <bundle.json>")
    return 2
