import PCS.V2.SemanticEquiv

/-!
# Untrusted certificate search (Semantic Intelligence v2)

A deterministic, bounded, *untrusted* search for `EquivCert` certificates: breadth-first
exploration of the rewrite graph from both the interpretation and the candidate, meeting in
the middle.  Nothing about this file is trusted or proved: it is a certificate *producer*.
Its output only matters after `checkCert` accepts it, and `checkCert` is proved sound for
arbitrary inputs (`untrusted_translation_search_cannot_forge_certified_equivalence`).

The search is deliberately incomplete (bounded depth and frontier size).  Failure to find a
certificate is never evidence of inequivalence.
-/

set_option autoImplicit false

namespace PCS.V2.Semantic

/-- All paths into a formula (root first). -/
def NFormula.paths : NFormula → List (List Nat)
  | .not φ => [] :: (NFormula.paths φ).map (0 :: ·)
  | .and φ ψ | .or φ ψ | .imp φ ψ =>
    [] :: ((NFormula.paths φ).map (0 :: ·) ++ (NFormula.paths ψ).map (1 :: ·))
  | .quant _ _ φ => [] :: (NFormula.paths φ).map (0 :: ·)
  | _ => [[]]

/-- Rules explored by the search (`dnegIntro` applies everywhere and is only useful as a
    hand-written step, so the search leaves it out). -/
def searchRules : List Rule := Rule.all.filter (fun r => r != .dnegIntro)

/-- All one-step rewrites of a nameless claim. -/
def NClaim.neighbors (n : NClaim) : List (Step × NClaim) :=
  let targets := Target.concl :: (List.range n.assumptions.length).map Target.assm
  targets.flatMap fun t =>
    let φ := match t with
      | .concl => n.conclusion
      | .assm j => n.assumptions[j]?.getD .tt
    (NFormula.paths φ).flatMap fun p => searchRules.filterMap fun r =>
      let st : Step := ⟨t, p, r⟩
      (n.applyStep st).map (fun n' => (st, n'))

/-- Breadth-first layers (steps stored in reverse), deduplicated, with a node cap. -/
def reachLayers (cap : Nat) : Nat → List (List Step × NClaim) → List NClaim →
    List (List Step × NClaim) → List (List Step × NClaim)
  | 0, _, _, acc => acc
  | d + 1, layer, seen, acc =>
    let step := fun (st : List NClaim × List (List Step × NClaim)) (x : List Step × NClaim) =>
      (x.2.neighbors).foldl (fun (st : List NClaim × List (List Step × NClaim)) (sn : Step × NClaim) =>
        if st.1.length ≥ cap || st.1.contains sn.2 then st
        else (sn.2 :: st.1, (sn.1 :: x.1, sn.2) :: st.2)) st
    let (seen', next) := layer.foldl step (seen, [])
    if next.isEmpty then acc else reachLayers cap d next.reverse seen' (acc ++ next.reverse)

/-- Nodes reachable within `depth` rewrite steps (including the start node). -/
def reachable (depth cap : Nat) (n : NClaim) : List (List Step × NClaim) :=
  reachLayers cap depth [([], n)] [n] [([], n)]

/-- **Untrusted bidirectional certificate search.** -/
def findCert (depth cap : Nat) (n m : NClaim) : Option EquivCert :=
  let L := reachable depth cap n
  let Rr := reachable depth cap m
  L.findSome? fun (sl, a) => Rr.findSome? fun (sr, b) =>
    if a.equivB b then some ⟨sl.reverse, sr.reverse⟩ else none

/-- The search, re-checked: only certificates that pass the proved checker are returned. -/
def findCheckedCert (depth cap : Nat) (n m : NClaim) : Option EquivCert :=
  match findCert depth cap n m with
  | some c => if checkCert c n m then some c else none
  | none => none

/-- Whatever the (unverified) search does, a returned certificate passes the checker. -/
theorem findCheckedCert_checked {depth cap : Nat} {n m : NClaim} {c : EquivCert}
    (h : findCheckedCert depth cap n m = some c) : checkCert c n m = true := by
  unfold findCheckedCert at h
  split at h
  · split at h
    · cases h; assumption
    · cases h
  · cases h

end PCS.V2.Semantic
