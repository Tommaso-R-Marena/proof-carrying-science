import PCS.V2.CertificateModel

/-!
# Fresh replay and static environment re-derivation (`replay_v06.py`,
  `environment_replay_v06.py`)

Arbitrary scientific checks (Python, R, containers, native code) cannot be
executed inside Lean.  They enter as *executors*, i.e. functions whose input is a
fully digest-bound request and whose output is an observation.  The Lean checker

* builds every request itself, from the verified certificate and the exact,
  SHA-256-checked delivered artifact bytes (`artifactTable`, `requestFor`);
* calls the executor on that request during verification (freshness by
  construction: no stored replay result is ever consulted);
* requires the recorded evidence kind/outcome to equal the fresh observation.

The environment stage re-derives the signed static environment description from
the delivered, digest-checked source bytes via the capture function and requires
JCS equality with the signed proposition.  It establishes *declared = captured*;
it does not (and the theorems do not claim to) establish anything about a
reconstructed or actual runtime environment.
-/

namespace PCS.V2.Replay

open PCS PCS.Decision PCS.V2.Json PCS.V2.Hex PCS.V2.SHA256 PCS.V2.Domains PCS.V2.Canonical
open PCS.V2.Common PCS.V2.NormalizedWire PCS.V2.Index PCS.V2.Package PCS.V2.CertificateModel

/-! ## Artifact table (`_artifact_bytes`) -/

def artifactEntry (files : FileMap) (a : CertArtifact) : Option (String × ByteArray) :=
  match lookup files a.path with
  | some b => if sha256 b.data.toList = a.sha256 ∧ b.size ≤ maxSingleFile then some (a.id, b) else none
  | none => none

def artifactTable (m : CertModel) (files : FileMap) : Option (List (String × ByteArray)) :=
  mapOpt (artifactEntry files) m.artifacts

/-! ## Replay requests, observations, executors -/

/-- Everything a replay execution may depend on, fixed by digests. -/
structure ReplayRequest where
  certificateSemanticHash : List UInt8
  checkerVersion : String
  /-- the verbatim evidence object (`check_spec`, `predicate`, `artifact_ids`, ...) -/
  evidence : JVal
  /-- artifact id ↦ exact delivered bytes (each SHA-256-checked against the certificate) -/
  artifacts : List (String × ByteArray)

structure Observation where
  kind : EvidenceKind
  outcome : Outcome
  deriving DecidableEq

/-- A replay executor (`_replay_one`): external, possibly native code. -/
abbrev Executor := ReplayRequest → Observation

def requestFor (c : CertV2) (m : CertModel) (table : List (String × ByteArray))
    (e : CertEvidence) : ReplayRequest :=
  { certificateSemanticHash := c.semanticHash, checkerVersion := m.checkerVersion,
    evidence := e.json, artifacts := table }

/-- `verify_certificate_replay_v06`: every recorded kind/outcome equals fresh replay. -/
def replayOK (exec : Executor) (c : CertV2) (m : CertModel)
    (table : List (String × ByteArray)) : Bool :=
  m.evidence.all (fun e => decide (exec (requestFor c m table e) = ⟨e.kind, e.outcome⟩))

/-! ## Static environment re-derivation -/

def envBindingFormat : String := "pcs-environment-binding-v1"
def envCaptureFormat : String := "pcs-environment-capture-v1"
def envNamespace : String := "pcs-manifest-environment-contract-v1"

structure InventoryItem where
  artifactId : String
  path : String
  bytes : ByteArray
  sha256 : List UInt8

/-- The static capture function (`capture_environment_v06`), external. -/
abbrev CaptureFn := List InventoryItem → JVal

structure EnvBinding where
  sourceIds : List String
  /-- members of the signed, canonical environment proposition -/
  signed : List (String × JVal)

def boolField (ms : List (String × JVal)) (k : String) : Option Bool :=
  match field ms k with
  | some (.bool b) => some b
  | _ => none

def envProposition (prop : String) : Option (List (String × JVal)) :=
  match parse prop.toList with
  | some (.obj sv) => if canonical (.obj sv) = true ∧ ser (.obj sv) = prop.toList then some sv else none
  | _ => none

def decodeEnvBinding (b : List (String × JVal)) : Option EnvBinding := do
  let ct ← (field b "contract").bind objOf
  let prop ← strField ct "proposition"
  let sv ← envProposition prop
  let ids ← (field b "source_artifact_ids").bind strArray
  let sids ← (field sv "source_artifact_ids").bind strArray
  if strField b "format" = some envBindingFormat ∧ strField ct "type" = some "external" ∧
     strField ct "namespace" = some envNamespace ∧ strField sv "format" = some envCaptureFormat ∧
     boolField sv "human_confirmed" = some true ∧ boolField sv "static_only" = some true ∧
     boolField sv "network_accessed" = some false ∧
     boolField sv "user_code_executed" = some false ∧ ids.Nodup ∧ ids = sids then
    pure { sourceIds := ids, signed := sv }
  else none

/-- `_replay_projection`: the signed proposition without its human-confirmation fields. -/
def envProjection (sv : List (String × JVal)) : JVal :=
  .obj (sv.filter (fun kv => kv.1 != "human_confirmed" && kv.1 != "confirmation_scope"))

def safeSourcePath (p : String) : Bool :=
  !(p.toList.contains '\\') && (segments p).all (fun s => s != "" && s != "." && s != "..")

def inventoryItem (files : FileMap) (asp : CertArtifact × String) : Option InventoryItem :=
  match lookup files asp.1.path with
  | some b =>
    if sha256 b.data.toList = asp.1.sha256 then
      some { artifactId := asp.1.id, path := asp.2, bytes := b, sha256 := asp.1.sha256 }
    else none
  | none => none

def sourceArtifacts (m : CertModel) : List (CertArtifact × String) :=
  m.artifacts.filterMap (fun a => a.sourcePath.map (fun sp => (a, sp)))

/-- `_artifact_inventory`. -/
def inventory (m : CertModel) (files : FileMap) : Option (List InventoryItem) :=
  let srcs := sourceArtifacts m
  if ((srcs.map (·.2)).Nodup ∧ srcs.all (fun s => safeSourcePath s.2) = true) then
    mapOpt (inventoryItem files) srcs
  else none

def capturedIds (fresh : JVal) : Option (List String) :=
  (objOf fresh).bind (fun f => (field f "source_artifact_ids").bind strArray)

/-- `verify_environment_replay_v06`: `some none` = no environment contract;
    `some (some (b, inv))` = contract re-derived from the inventory `inv`. -/
def envStage (capture : CaptureFn) (c : CertV2) (m : CertModel) (files : FileMap) :
    Option (Option (EnvBinding × List InventoryItem)) :=
  match field c.members "environment" with
  | none => some none
  | some .null => some none
  | some (.obj b) =>
    match decodeEnvBinding b, inventory m files with
    | some eb, some inv =>
      if eb.sourceIds.all (fun i => inv.any (·.artifactId == i)) = true ∧
         ser (envProjection eb.signed) = ser (capture inv) ∧
         capturedIds (capture inv) = some eb.sourceIds then
        some (some (eb, inv))
      else none
    | _, _ => none
  | some _ => none

end PCS.V2.Replay
