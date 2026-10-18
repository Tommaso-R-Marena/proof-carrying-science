import PCSEpistemic.Evaluate

/-!
# Principal soundness theorems for the epistemic lattice

Finite theorems about well-formedness barriers and dependency joins.
They do not establish scientific truth, biological adequacy, or package authority.
-/
set_option autoImplicit false

namespace PCSEpistemic

/-- Empirical claims without falsifiers are not well-formed. -/
theorem empirical_requires_falsifier (id : Nat) (deps : List Nat) (supports : List Literal) :
    Claim.wellFormed ⟨id, .empirical, deps, [], supports⟩ = false := by
  simp [Claim.wellFormed, requiresFalsifier]

/-- Computational claims without falsifiers are not well-formed. -/
theorem computational_requires_falsifier (id : Nat) (deps : List Nat) (supports : List Literal) :
    Claim.wellFormed ⟨id, .computational, deps, [], supports⟩ = false := by
  simp [Claim.wellFormed, requiresFalsifier]

/-- Formal claims may omit falsifiers when they are not self-dependent. -/
theorem formal_may_omit_falsifier (id : Nat) (supports : List Literal) :
    Claim.wellFormed ⟨id, .formal, [], [], supports⟩ = true := by
  simp [Claim.wellFormed, requiresFalsifier]

/-- Provenance claims may omit falsifiers when they are not self-dependent. -/
theorem provenance_may_omit_falsifier (id : Nat) (supports : List Literal) :
    Claim.wellFormed ⟨id, .provenance, [], [], supports⟩ = true := by
  simp [Claim.wellFormed, requiresFalsifier]

/-- Exact class match is required for compatibility. -/
theorem classCompatible_iff (a b : EvidenceClass) :
    classCompatible a b = true ↔ a = b := by
  simp [classCompatible, beq_iff_eq]

/-- Unsound absorbs in dependency join. -/
theorem depJoin_unsound_cons (xs : List Status) :
    depJoin (.unsound :: xs) = .unsound := by
  simp [depJoin]

/-- Refuted precedes open/supported when the head is refuted and the list has no unsound. -/
theorem depJoin_refuted_only :
    depJoin [.refuted] = .refuted := by
  simp [depJoin]

/-- All-supported nonempty join. -/
theorem depJoin_supported_pair :
    depJoin [.supported, .supported] = .supported := by
  simp [depJoin]

/-- Open blocks supported join. -/
theorem depJoin_open_blocks :
    depJoin [.supported, .open_] = .open_ := by
  simp [depJoin]

/-- Empty empirical package is structurally unsound. -/
theorem empty_empirical_package_unsound :
    Package.structurallySound
      { claims := [⟨0, .empirical, [], [], []⟩]
        evidence := []
        observations := ⟨[]⟩ } = false := by
  simp [Package.structurallySound, Package.idsUnique, Package.depsResolved, hasDup,
        Claim.wellFormed, requiresFalsifier]

/-- Well-formed empirical claim with a matched falsifier evaluates to refuted
when dependencies join to supported. -/
theorem evalClaim_falsifier_refutes
    (id : Nat) (ℓ : Literal) (supports : List Literal)
    (evs : List Evidence) (o : Observations)
    (hf : anyFalsifier [ℓ] o = true) :
    evalClaim ⟨id, .empirical, [], [ℓ], supports⟩ [] evs o = .refuted := by
  simp [evalClaim, Claim.wellFormed, requiresFalsifier, depJoin, hf]

/-- Wrong-class evidence does not discharge: evidenceFor returns none. -/
theorem evidenceFor_wrong_class
    (claimId : Nat) (pass : Bool) :
    evidenceFor [⟨claimId, .formal, pass⟩] claimId .empirical = none := by
  simp [evidenceFor, classCompatible]

/-- Matched support literal. -/
theorem literal_matches_known (a : Atom) (b : Bool) :
    Literal.matches ⟨a, b⟩ ⟨[(a, b)]⟩ = true := by
  simp [Literal.matches, Observations.lookup]

end PCSEpistemic
