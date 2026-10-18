/-!
# Epistemic Obligation Lattice — core types

This library formalizes a **falsifier-carrying** assurance calculus for PCS.
It is experimental and grants **no** package, Lean-authority, or scientific acceptance.

Scientific claims are defeasible under observation. Formal proofs are not.
The lattice makes that asymmetry machine-checkable: empirical claims must carry
explicit falsifiers; class barriers forbid silent promotion; composition cannot
hide a refuted dependency.
-/
set_option autoImplicit false

namespace PCSEpistemic

/-- Four evidence classes. They are intentionally incomparable for promotion. -/
inductive EvidenceClass where
  | formal
  | computational
  | empirical
  | provenance
  deriving DecidableEq, Repr, Inhabited

/-- Epistemic status of one obligation. -/
inductive Status where
  | unsound
  | open_
  | supported
  | refuted
  deriving DecidableEq, Repr, Inhabited

/-- Observation atoms are finite Boolean labels. -/
abbrev Atom := Nat

/-- A falsifier or support condition: atom equals an expected Boolean. -/
structure Literal where
  atom : Atom
  expects : Bool
  deriving DecidableEq, Repr

/-- One claim node in a finite epistemic graph. -/
structure Claim where
  id : Nat
  klass : EvidenceClass
  dependencies : List Nat
  falsifiers : List Literal
  supportRequires : List Literal
  deriving DecidableEq, Repr

/-- One evidence object. Class must match the claim class exactly to discharge. -/
structure Evidence where
  claimId : Nat
  klass : EvidenceClass
  pass : Bool
  deriving DecidableEq, Repr

/-- Finite observation map: atom → Boolean. Missing atoms are treated as unknown. -/
structure Observations where
  known : List (Atom × Bool)
  deriving DecidableEq, Repr

/-- Complete finite epistemic package (untrusted producer payload). -/
structure Package where
  claims : List Claim
  evidence : List Evidence
  observations : Observations
  deriving DecidableEq, Repr

/-- Lookup a known observation atom. -/
def Observations.lookup (o : Observations) (a : Atom) : Option Bool :=
  (o.known.find? (fun p => p.1 == a)).map (·.2)

/-- A literal matches only when the atom is known and equals the expected value. -/
def Literal.matches (ℓ : Literal) (o : Observations) : Bool :=
  match o.lookup ℓ.atom with
  | some b => b == ℓ.expects
  | none => false

/-- A literal is satisfied for support only when known and equal. -/
def Literal.satisfied (ℓ : Literal) (o : Observations) : Bool :=
  ℓ.matches o

/-- Any falsifier match refutes. -/
def anyFalsifier (fs : List Literal) (o : Observations) : Bool :=
  fs.any (·.matches o)

/-- All support literals must be known and true-as-expected. -/
def allSupport (ss : List Literal) (o : Observations) : Bool :=
  ss.all (·.satisfied o)

/-- Exact class match — never promote empirical evidence into formal discharge. -/
def classCompatible (need got : EvidenceClass) : Bool :=
  need == got

/-- Empirical and computational claims must declare at least one falsifier. -/
def requiresFalsifier (c : EvidenceClass) : Bool :=
  match c with
  | .empirical | .computational => true
  | .formal | .provenance => false

/-- Claim is structurally eligible for evaluation. -/
def Claim.wellFormed (c : Claim) : Bool :=
  (!requiresFalsifier c.klass || !c.falsifiers.isEmpty)
  && c.dependencies.all (fun d => !decide (d = c.id))

end PCSEpistemic
