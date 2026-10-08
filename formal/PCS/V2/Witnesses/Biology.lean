import PCS.V2.Witnesses.Registry

/-!
# Witness domain 1: computational biology (residue sites + deterministic score)

Domain claim `BioClaim`: for the committed protein-sequence artifact `seqA` (one ASCII
residue letter per byte) and the committed site-list artifact `sitesA` (one 1-based residue
index per byte),

* every reported residue index lies within the sequence (`SitesInRange`), and
* the deterministic hydrophobic-site score (number of reported sites whose residue is one
  of `A V I L M F W C`) is at least the declared threshold.

Claim IR and decomposition: the root `.sites c` is split by rule `"bio.split"` into the two
leaves `.inRange` and `.score`, each discharged by its own proof-carrying checker
(`residue_bounds`, `hydrophobic_score`).

The domain's assurance theorem `bio_archive_sound` is a one-line instance of the generic
flagship; the only domain work is `bioAdapter_sound` (the local adapter contract).

This is a toy encoding; it proves exactly the stated claim about the committed bytes, not
any biological fact about a physical protein.
-/

set_option autoImplicit false

namespace PCS.V2.Witnesses.Biology

open PCS PCS.V2.Json PCS.V2.Replay PCS.V2.Checkers PCS.V2.PKPDCheck PCS.V2.DomainAuthority
open PCS.V2.DomainAdapter PCS.V2.ClaimGraph PCS.V2.Witnesses

/-! ## Domain semantics (independent of PCS) -/

def isHydrophobic (b : UInt8) : Bool := [65, 86, 73, 76, 77, 70, 87, 67].contains b

def SitesInRange (sq st : List UInt8) : Prop := ∀ i ∈ st, 1 ≤ i.toNat ∧ i.toNat ≤ sq.length

def hydroAt (sq : List UInt8) (i : UInt8) : Bool :=
  match sq[i.toNat - 1]? with
  | some b => isHydrophobic b
  | none => false

def hydroScore (sq st : List UInt8) : Nat := (st.filter (hydroAt sq)).length

structure BioClaim where
  seqA : String
  sitesA : String
  threshold : Nat
  deriving DecidableEq

/-- The computational-biology domain. -/
def bioDomain : Domain :=
  { World := List (String × ByteArray), Claim := BioClaim,
    Holds := fun w c => ∃ sq st, artBytes w c.seqA = some sq ∧ artBytes w c.sitesA = some st ∧
      SitesInRange sq st ∧ c.threshold ≤ hydroScore sq st }

/-! ## SECB1�^5��Z�