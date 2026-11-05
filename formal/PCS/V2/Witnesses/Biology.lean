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

/-! ## Claim IR -/

inductive BioIR where
  | sites (c : BioClaim)
  | inRange (seqA sitesA : String)
  | score (seqA sitesA : String) (threshold : Nat)
  deriving DecidableEq

def bioSem (w : List (String × ByteArray)) : BioIR → Prop
  | .sites c => (∃ sq st, artBytes w c.seqA = some sq ∧ artBytes w c.sitesA = some st ∧
      SitesInRange sq st) ∧
    (∃ sq st, artBytes w c.seqA = some sq ∧ artBytes w c.sitesA = some st ∧
      c.threshold ≤ hydroScore sq st)
  | .inRange s t => ∃ sq st, artBytes w s = some sq ∧ artBytes w t = some st ∧ SitesInRange sq st
  | .score s t k => ∃ sq st, artBytes w s = some sq ∧ artBytes w t = some st ∧
      k ≤ hydroScore sq st

/-! ## Proof-carrying checkers -/

def sitesInRangeB (sq st : List UInt8) : Bool :=
  st.all (fun i => decide (1 ≤ i.toNat ∧ i.toNat ≤ sq.length))

theorem sitesInRangeB_sound {sq st : List UInt8} (h : sitesInRangeB sq st = true) :
    SitesInRange sq st := by
  intro i hi
  simp only [sitesInRangeB, List.all_eq_true, decide_eq_true_eq] at h
  exact h i hi

def parseBounds (ev : JVal) : Option (String × String) :=
  match specStr ev "sequence_artifact", specStr ev "sites_artifact" with
  | some s, some t => some (s, t)
  | _, _ => none

def parseScore (ev : JVal) : Option (String × String × Nat) :=
  match specStr ev "sequence_artifact", specStr ev "sites_artifact", specNat ev "threshold" with
  | some s, some t, some k => some (s, t, k)
  | _, _, _ => none

def boundsTest (x : String × String) (w : List (String × ByteArray)) : Bool :=
  match artBytes w x.1, artBytes w x.2 with
  | some sq, some st => sitesInRangeB sq st
  | _, _ => false

def scoreTest (x : String × String × Nat) (w : List (String × ByteArray)) : Bool :=
  match artBytes w x.1, artBytes w x.2.1 with
  | some sq, some st => decide (x.2.2 ≤ hydroScore sq st)
  | _, _ => false

theorem boundsTest_sound (x : String × String) (w : List (String × ByteArray))
    (h : boundsTest x w = true) : bioSem w (.inRange x.1 x.2) := by
  unfold boundsTest at h
  split at h
  · rename_i sq st h1 h2; exact ⟨sq, st, h1, h2, sitesInRangeB_sound h⟩
  · cases h

theorem scoreTest_sound (x : String × String × Nat) (w : List (String × ByteArray))
    (h : scoreTest x w = true) : bioSem w (.score x.1 x.2.1 x.2.2) := by
  unfold scoreTest at h
  split at h
  · rename_i sq st h1 h2; exact ⟨sq, st, h1, h2, of_decide_eq_true h⟩
  · cases h

def boundsChecker : DomainChecker :=
  specChecker "residue_bounds" parseBounds boundsTest (fun x w => bioSem w (.inRange x.1 x.2))
    boundsTest_sound

def scoreChecker : DomainChecker :=
  specChecker "hydrophobic_score" parseScore scoreTest
    (fun x w => bioSem w (.score x.1 x.2.1 x.2.2)) scoreTest_sound

/-! ## The adapter -/

def bioNodeOf (ev : JVal) : Option BioIR :=
  if isCheckType "residue_bounds" ev then (parseBounds ev).map (fun x => .inRange x.1 x.2)
  else if isCheckType "hydrophobic_score" ev then
    (parseScore ev).map (fun x => .score x.1 x.2.1 x.2.2)
  else none

def bioRule (r : String) (p : BioIR) (cs : List BioIR) : Bool :=
  r == "bio.split" &&
    match p with
    | .sites c => decide (cs = [.inRange c.seqA c.sitesA, .score c.seqA c.sitesA c.threshold])
    | _ => false

def bioAdapter : DomainAdapter bioDomain :=
  { IR := BioIR,
    decode := fun v => match predStr v "kind",
        predStr v "sequence_artifact",
        predStr v "sites_artifact",
        predNat v "threshold" with
      | some "bio.residue_sites", some s, some t, some k => some ⟨s, t, k⟩
      | _, _, _, _ => none,
    compile := fun c => some (.sites c),
    world := id,
    sem := bioSem,
    leafCheck := fun ev n => decide (bioNodeOf ev = some n),
    ruleCheck := bioRule }

/-- **The local adapter contract**, in any authority registry that contains the two
    biology checkers (with unique, non-built-in tags). -/
theorem bioAdapter_sound {ks : List DomainChecker} (hreg : Registered ks)
    (hb : boundsChecker ∈ ks) (hs : scoreChecker ∈ ks) (ExtHolds : ReplayRequest → Prop) :
    AdapterSound bioAdapter (AuthorityValid (registry ks) ExtHolds) where
  compile_sound := by
    intro w c ir hc hsem
    cases hc
    obtain ⟨⟨sq, st, h1, h2, hr⟩, ⟨sq', st', h1', h2', hk⟩⟩ := hsem
    rw [h1] at h1'; rw [h2] at h2'
    cases h1'; cases h2'
    exact ⟨sq, st, h1, h2, hr, hk⟩
  rule_sound := by
    intro w r p cs h hcs
    simp only [bioAdapter, bioRule, Bool.and_eq_true] at h
    obtain ⟨_, h⟩ := h
    cases p with
    | sites c =>
      simp only [decide_eq_true_eq] at h
      subst h
      exact ⟨hcs _ List.mem_cons_self, hcs _ (List.mem_cons_of_mem _ List.mem_cons_self)⟩
    | inRange _ _ => cases h
    | score _ _ _ => cases h
  leaf_sound := by
    intro req n hl hv
    simp only [bioAdapter, decide_eq_true_eq] at hl
    unfold bioNodeOf at hl
    split at hl
    · rename_i ht
      obtain ⟨x, hx, rfl⟩ := Option.map_eq_some_iff.mp hl
      obtain ⟨x', hx', hsem⟩ := registry_valid hreg hb ht hv
      rw [hx] at hx'; cases hx'
      exact hsem
    · split at hl
      · rename_i _ ht
        obtain ⟨x, hx, rfl⟩ := Option.map_eq_some_iff.mp hl
        obtain ⟨x', hx', hsem⟩ := registry_valid hreg hs ht hv
        rw [hx] at hx'; cases hx'
        exact hsem
      · cases hl

/-- **Biology assurance from a raw signed archive**, obtained from the generic flagship:
    sole hypotheses `NoForgery` and the domain-independent registration conditions. -/
theorem bio_archive_sound {ks : List DomainChecker} (hreg : Registered ks)
    (hb : boundsChecker ∈ ks) (hs : scoreChecker ∈ ks)
    {t : PCS.V2.Authority.AuthorityTranscript} {T : PCS.V2.EndToEnd.TrustAnchor}
    {signed : List UInt8 → Prop}
    (hB : PCS.V2.Signature.NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {raw : ByteArray} {inp : PCS.V2.Package.PackageInput} {r : PCS.V2.EndToEnd.AcceptedResult}
    (h : acceptArchiveWithCheckers (registry ks) t T raw = some (inp, r))
    {cid : String} {g : Graph String BioIR} {c : BioClaim}
    (hd : domainAccepts bioAdapter r cid g = some c) :
    ∃ sq st, artBytes r.table c.seqA = some sq ∧ artBytes r.table c.sitesA = some st ∧
      SitesInRange sq st ∧ c.threshold ≤ hydroScore sq st :=
  ((pcs_generic_domain_archive_acceptance_sound_certified (registry ks) hB h bioAdapter
    (bioAdapter_sound hreg hb hs _) hd).2).holds

end PCS.V2.Witnesses.Biology
