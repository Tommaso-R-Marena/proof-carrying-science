import PCS.V2.Witnesses.Registry

/-!
# Witness domain 3: ML evaluation hygiene on the **unchanged production authority**

Domain claim `SplitClaim`: the committed train, validation and test tables are strict CSV
tables containing the key column, and their key sets are **pairwise disjoint** (no
train/validation/test leakage on that key).

Decomposition: root `.split c` is split by rule `"ml.pairwise"` into the three pairwise
leaves `.disjoint`, each discharged by the *existing verified built-in* `csv_disjoint`
checker (`PCS.V2.Csv`).  No new checker is registered, so this domain runs on the production
authority `acceptArchiveWithTranscript`, and `ml_archive_sound` follows from
`pcs_generic_domain_archive_acceptance_sound_builtin` with **`NoForgery` as the only
hypothesis**.

Scope: data-split disjointness of the committed tables; nothing about model quality.
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses.MLEval

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.Checkers PCS.V2.Csv PCS.V2.Chemistry PCS.V2.Package
open PCS.V2.Index PCS.V2.DomainAuthority PCS.V2.DomainAdapter PCS.V2.ClaimGraph PCS.V2.Witnesses

/-- Disjointness of two committed tables on a key. -/
def TablesDisjoint (w : List (String × ByteArray)) (a b key : String) : Prop :=
  ∃ ba bb, lookup w a = some ba ∧ lookup w b = some bb ∧
    CsvDisjoint ba.data.toList bb.data.toList key.toUTF8.data.toList

structure SplitClaim where
  train : String
  valid : String
  test : String
  key : String
  deriving DecidableEq

def mlDomain : Domain :=
  { World := List (String × ByteArray), Claim := SplitClaim,
    Holds := fun w c => TablesDisjoint w c.train c.valid c.key ∧
      TablesDisjoint w c.train c.test c.key ∧ TablesDisjoint w c.valid c.test c.key }

inductive SplitIR where
  | split (c : SplitClaim)
  | disjoint (a b key : String)
  deriving DecidableEq

def splitSem (w : List (String × ByteArray)) : SplitIR → Prop
  | .split c => TablesDisjoint w c.train c.valid c.key ∧
      TablesDisjoint w c.train c.test c.key ∧ TablesDisjoint w c.valid c.test c.key
  | .disjoint a b k => TablesDisjoint w a b k

def splitRule (r ECB1�nzr�