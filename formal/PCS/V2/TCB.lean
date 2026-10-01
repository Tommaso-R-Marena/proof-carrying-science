import PCS.V2.Reproducibility
import PCS.V2.Ed25519

/-!
# Trusted computing base, made explicit

Every external dependency of the v0.6 assurance chain is either

* proved in Lean,
* checked by Lean code that the flagship theorem is *about*, or
* a named hypothesis (a `Prop`-valued definition, never an `axiom`) that appears
  only in the theorems that need it.

`TCBItem`/`tcbStatus` is the machine-readable inventory used by the report.
`production_accept_implies_scientific_assurance` retains the general
`ProductionRefinesLean` contract for an arbitrary external production verifier.
The deployed high-assurance path no longer treats Python-only acceptance as
authoritative: `PCS.V2.Authority` gates production on Lean acceptance and proves
the corresponding conjunction pattern refines Lean. Raw ZIP decoding,
materialization/invocation, and external replay/capture meaning remain explicit
implementation or semantic boundaries.
-/

namespace PCS.V2.TCB

open PCS.V2.Json PCS.V2.SHA256 PCS.V2.Package PCS.V2.Signature PCS.V2.Replay PCS.V2.EndToEnd
open PCS.V2.Flagship

inductive TCBItem where
  | leanKernel | parserCodec | canonicalizer | sha256Impl | sha256Collision
  | ed25519Impl | ed25519Unforgeability | archiveExtractor | filesystemOS
  | pythonRuntime | rRuntime | containerRuntime | captureFidelity
  | reconstructionFidelity | replayExecutor | scientificPredicate | freshnessAuthority
  | unicodeTables | productionCorrespondence
  deriving DecidableEq, Repr

inductive TCBStatus where
  /-- part of the logical foundation; not removable -/
  | foundation
  /-- implemented in Lean and proved (no hypothesis) -/
  | provedInLean
  /-- implemented in Lean as an executable specification transcribed from a standard;
      validated by known-answer vectors -/
  | leanSpecification
  /-- appears only as a named hypothesis in the theorems that use it -/
  | namedHypothesis
  /-- not used by PCS v0.6 at all -/
  | notApplicable
  deriving DecidableEq, Repr

def tcbStatus : TCBItem → TCBStatus
  | .leanKernel => .foundation
  | .parserCodec => .provedInLean            -- parseCanonicalBytes_sound/_unique/_complete
  | .canonicalizer => .provedInLean          -- parse_ser, jcsBytes_injective
  | .sha256Impl => .leanSpecification        -- PCS.V2.SHA256.sha256 (FIPS 180-4)
  | .sha256Collision => .namedHypothesis     -- appears as `Sha256Collision` disjuncts only
  | .ed25519Impl => .leanSpecification       -- PCS.V2.Ed25519.verify (RFC 8032)
  | .ed25519Unforgeability => .namedHypothesis   -- `NoForgery`
  | .archiveExtractor => .namedHypothesis    -- `ZipDecoder` + `ZipDecoderFaithful`
  | .filesystemOS => .notApplicable          -- the Lean checker reads no filesystem state
  | .pythonRuntime => .namedHypothesis       -- inside `ReplayFaithful` / `CaptureSound`
  | .rRuntime => .namedHypothesis            -- inside `ReplayFaithful`
  | .containerRuntime => .notApplicable      -- v0.6 replay never builds/runs containers
  | .captureFidelity => .namedHypothesis     -- `CaptureSound`
  | .reconstructionFidelity => .notApplicable    -- v0.6 does not reconstruct environments
  | .replayExecutor => .namedHypothesis      -- `ReplayFaithful`; proved for `reaction_balance`
                                             -- (`PCS.V2.Chemistry.chemExecWith_faithful`)
  | .scientificPredicate => .namedHypothesis -- the `Holds` / `Describes` relations
  | .freshnessAuthority => .notApplicable    -- freshness is re-execution; no stored state
  | .unicodeTables => .namedHypothesis       -- `UnicodeOps` (portability meaning only)
  | .productionCorrespondence => .namedHypothesis  -- `ProductionRefinesLean`

/-! ## Named correspondence hypotheses (not axioms) -/

/-- Python `hashlib.sha256` (OpenSSL) computes FIPS 180-4 SHA-256.  Needed only to
    relate *production* digests to the Lean checker; the Lean checker recomputes
    every digest itself. -/
def Sha256ProductionAgrees (hashlib : List UInt8 → List UInt8) : Prop := ∀ m, hashlib m = sha256 m

/-- The ZIP decoder returns exactly the archive's (name, decompressed bytes) members,
    for the archive format semantics `ZipSemantics`. -/
def ZipDecoderFaithful (zip : ZipDecoder) (ZipSemantics : ByteArray → List (String × ByteArray) → Prop) :
    Prop :=
  ∀ raw entries, zip raw = some entries → ZipSemantics raw entries

/-- The production verifier (Python `verify_package_zip_end_to_end_v06`), viewed as a
    function of the archive bytes, accepts only what the Lean checker accepts. -/
def ProductionRefinesLean (production : ByteArray → Bool) (O : Oracles) (zip : ZipDecoder)
    (T : TrustAnchor) : Prop :=
  ∀ raw, production raw = true → (acceptArchive O zip T raw).isSome = true

/-- Production acceptance of raw archive bytes implies scientific assurance, under the
    single correspondence hypothesis plus the external contracts. -/
theorem production_accept_implies_scientific_assurance {production : ByteArray → Bool}
    {O : Oracles} {zip : ZipDecoder} {T : TrustAnchor} (K : ExternalContracts O T)
    (hP : ProductionRefinesLean production O zip T) {raw : ByteArray}
    (h : production raw = true) :
    ∃ inp r, acceptArchive O zip T raw = some (inp, r) ∧ ScientificAssurance O T K inp r := by
  have hs := hP raw h
  cases hr : acceptArchive O zip T raw with
  | none => rw [hr] at hs; cases hs
  | some ir =>
    obtain ⟨inp, r⟩ := ir
    exact ⟨inp, r, rfl, (pcs_archive_accept_implies_scientific_assurance K hr).2⟩

/-- With the Lean Ed25519 specification plugged in, hypothesis (A) disappears: only
    unforgeability (B) of the RFC 8032 scheme for the trust-anchor key remains. -/
def contractsWithLeanEd25519 {O : Oracles} {T : TrustAnchor} (hO : O.ed25519 = PCS.V2.Ed25519.verify)
    (signed : List UInt8 → Prop) (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    (describes : List InventoryItem → JVal → Prop) (hC : CaptureSound O.capture describes)
    (holds : ReplayRequest → Prop) (hR : ReplayFaithful O.exec holds) : ExternalContracts O T :=
  { ed25519Spec := PCS.V2.Ed25519.verify, signed, ed25519ImplCorrect := by rw [hO]; exact fun _ _ _ => rfl,
    noForgery := hB, describes, captureSound := hC, holds, replayFaithful := hR }

end PCS.V2.TCB
