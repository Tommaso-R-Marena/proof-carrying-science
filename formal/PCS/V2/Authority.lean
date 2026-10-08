import PCS.V2.Archive
import PCS.V2.Chemistry
import PCS.V2.Checkers
import PCS.V2.Workflow
import PCS.V2.EnvFacts
import PCS.V2.TCB

/-!
# Lean-authoritative production acceptance

Production supplies a canonical observation transcript containing only results of
external stages that Lean intentionally models as oracles: static environment
capture, static workflow replay, and non-Lean replay observations. The transcript
is bound to the verified certificate semantic hash and checker version.

Lean still reconstructs and verifies the package, certificate, artifact table,
signatures, hashes, normalized decisions, and normalized set itself. The verified
built-in checks `reaction_balance`, `unit_compatible`, `csv_disjoint`, `pkpd_contract`,
`pkpd_reference_match`, and `pkpd_peak_concentration_threshold` ignore the
transcript result and are independently replayed by the proved Lean checkers
(`PCS.V2.Checkers.builtinExecWith`); the transcript is consulted only for evidence
kinds that no certified checker handles.

`gatedProduction_refinesLean` captures the architectural point: once production
acceptance is the conjunction of a precheck and Lean acceptance,
`ProductionRefinesLean` follows without a Python-semantics refinement proof.
-/

namespace PCS.V2.Authority

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.Canonical PCS.V2.Common
open PCS.V2.Package PCS.V2.Replay PCS.V2.CertificateModel PCS.V2.EndToEnd
open PCS.V2.Index PCS.V2.Archive PCS.V2.TCB

def authorityTranscriptFormat : String := "pcs-lean-authority-observations-v1"
def maxAuthorityTranscriptBytes : Nat := 16 * 1024 * 1024

structure ReplayObservation where
  evidenceId : String
  kind : EvidenceKind
  outcome : Outcome
  deriving DecidableEq

structure AuthorityTranscript where
  certificateSemanticHash : List UInt8
  checkerVersion : String
  workflowOk : Bool
  environmentCapture : JVal
  replay : List ReplayObservation
  /-- normalized fresh static analysis of the committed workflow sources (the only
      workflow input not checked by Lean itself; see `PCS.V2.Workflow`) -/
  workflowAnalysis : List PCS.V2.Workflow.FreshSource := []

def decodeReplayObservation (v : JVMÄ^¹×g!j»