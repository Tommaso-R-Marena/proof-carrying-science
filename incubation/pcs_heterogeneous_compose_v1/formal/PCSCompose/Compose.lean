import PCSCompose.Levels

/-!
# Heterogeneous evidence composition

A composite claim is supported only when every leaf evidence atom independently
supports its claim *and* every leaf level is at least the required level.
The achieved composite level is the meet of leaf levels — never a promotion.

Untrusted producers may propose composites; acceptance is this small checker.
-/

namespace PCSCompose.Compose

open PCSCompose.Levels

/-- One independently checkable evidence atom. -/
structure EvidenceAtom where
  id : Nat
  level : Level
  /-- Fresh independent leaf check passed. -/
  supported : Bool
  claimId : Nat
  deriving DecidableEq, Repr

/-- A claimed composite of leaf evidence. -/
structure CompositeClaim where
  id : Nat
  requiredLevel : Level
  leafIds : List Nat
  deriving DecidableEq, Repr

/-- Look up an atom by id. -/
def findAtom (atoms : List EvidenceAtom) (id : Nat) : Option EvidenceAtom :=
  atoms.find? (fun a => a.id = id)

/-- Every declared leaf exists, is supported, and meets the required level. -/
def leavesOk (atoms : List EvidenceAtom) (c : CompositeClaim) : Bool :=
  c.leafIds.all fun id =>
    match findAtom atoms id with
    | none => false
    | some a => a.supported && decide (c.requiredLevel.le a.level)

/-- Achieved level = meet of leaf levels; empty or missing leaf yields `open_`. -/
def achievedLevel (atoms : List EvidenceAtom) (c : CompositeClaim) : Level :=
  if c.leafIds.isEmpty then Level.open_
  else
    Level.meetList (c.leafIds.map fun id =>
      match findAtom atoms id with
      | some a => a.level
      | none => Level.open_)

/-- Composite acceptance: nonempty leaves, leaves ok, achieved ≥ required. -/
def accept (atoms : List EvidenceAtom) (c : CompositeClaim) : Bool :=
  !c.leafIds.isEmpty &&
    leavesOk atoms c &&
      decide (c.requiredLevel.le (achievedLevel atoms c))

/-- If leavesOk, a member leaf has a supported atom at sufficient level. -/
theorem leavesOk_member
    (atoms : List EvidenceAtom) (c : CompositeClaim)
    (h : leavesOk atoms c = true) (id : Nat) (hid : id ∈ c.leafIds) :
    ∃ a, findAtom atoms id = some a ∧ a.supported = true ∧ c.requiredLevel.le a.level := by
  have hall := (List.all_eq_true).1 (by simpa [leavesOk] using h) id hid
  match hf : findAtom atoms id with
  | none => simp [hf] at hall
  | some a =>
    simp [hf, decide_eq_true_eq] at hall
    exact ⟨a, rfl, hall.1, hall.2⟩

/-- Empty composite never accepts. -/
theorem empty_rejects (atoms : List EvidenceAtom) (c : CompositeClaim)
    (h : c.leafIds = []) : accept atoms c = false := by
  simp [accept, h]

/-- Achieved level of a single formal leaf is formal when present and mapped. -/
theorem achieved_singleton_formal
    (atoms : List EvidenceAtom) (c : CompositeClaim)
    (a : EvidenceAtom)
    (hleaves : c.leafIds = [a.id])
    (ha : findAtom atoms a.id = some a)
    (hlv : a.level = Level.formal) :
    achievedLevel atoms c = Level.formal := by
  simp [achievedLevel, hleaves, ha, hlv, Level.meetList, Level.meet]

/-- Meet of empirical then formal is empirical — the heterogeneous law on levels. -/
theorem heterogeneous_level_law :
    Level.meetList [Level.empirical, Level.formal] = Level.empirical := rfl

/-- Formal-required claim with empirical achieved level is rejected. -/
theorem formal_required_empirical_achieved_rejects
    (atoms : List EvidenceAtom) (c : CompositeClaim)
    (hreq : c.requiredLevel = Level.formal)
    (hne : ¬ c.leafIds.isEmpty)
    (hach : achievedLevel atoms c = Level.empirical) :
    accept atoms c = false := by
  simp [accept, hreq, hach, hne, Level.le, Level.rank]

/-- Computational leaf alone cannot satisfy a Formal requirement (concrete). -/
theorem computational_atom_not_formal_accept :
    let a : EvidenceAtom :=
      { id := 1, level := .computational, supported := true, claimId := 0 }
    let atoms := [a]
    let c : CompositeClaim := { id := 0, requiredLevel := .formal, leafIds := [1] }
    accept atoms c = false := by
  decide

/-- Unsupported formal leaf rejects (concrete). -/
theorem unsupported_formal_rejects :
    let a : EvidenceAtom :=
      { id := 1, level := .formal, supported := false, claimId := 0 }
    accept [a] { id := 0, requiredLevel := .formal, leafIds := [1] } = false := by
  decide

/-- Underleveled empirical leaf rejects Formal requirement (concrete). -/
theorem underleveled_empirical_rejects :
    let a : EvidenceAtom :=
      { id := 1, level := .empirical, supported := true, claimId := 0 }
    accept [a] { id := 0, requiredLevel := .formal, leafIds := [1] } = false := by
  decide

/-- Heterogeneous formal+empirical pair: accepts Empirical req, rejects Formal req. -/
theorem heterogeneous_pair_law :
    let f : EvidenceAtom :=
      { id := 1, level := .formal, supported := true, claimId := 0 }
    let e : EvidenceAtom :=
      { id := 2, level := .empirical, supported := true, claimId := 1 }
    let atoms := [f, e]
    accept atoms { id := 0, requiredLevel := .empirical, leafIds := [1, 2] } = true ∧
    accept atoms { id := 1, requiredLevel := .formal, leafIds := [1, 2] } = false ∧
    achievedLevel atoms { id := 2, requiredLevel := .empirical, leafIds := [1, 2] }
      = Level.empirical := by
  decide

end PCSCompose.Compose
