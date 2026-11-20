import EvolvingSafetyGate

/-! Research reference checker with receiver-owned class and evaluation records. -/
set_option autoImplicit false
namespace PromotionReplay
open EvolvingSafetyGate

/-- The reviewer supplies a fixed set of cases, their expected outcomes, observed
predictions, and the mapping of candidate identities to reviewed mechanism classes.
An unavailable run is represented by none, including timeouts and errors.
IDs are exact values in this model. Authenticating their bytes is outside it. -/
structure Review where
  version : Nat
  cases : List Nat
  label : Nat → Bool
  observed : Nat → Nat → Option Bool
  mechanism : Nat → Mechanism

def score (r : Review) (id : Nat) : List Nat → Option Nat
  | [] => some 0
  | c :: cs => do
    let result ← r.observed id c
    let rest ← score r id cs
    return rest + (if result = r.label c then 1 else 0)

theorem score_bounded (r : Review) (id : Nat) (cs : List Nat) (n : Nat)
    (h : score r id cs = some n) : n ≤ cs.length := by
  induction cs generalizing n with
  | nil => simpa [score] using h.symm
  | cons c cs ih =>
    cases eq : r.observed id c with
    | none => simp [score, eq] at h
    | some b =>
      cases es : score r id cs with
      | none => simp [score, eq, es] at h
      | some k =>
        have bound := ih k es
        by_cases hit : b = r.label c <;> simp [score, eq, es, hit] at h <;>
          simp only [List.length_cons] <;> omega

theorem missing_score (r : Review) (id c : Nat) (cs : List Nat)
    (mem : c ∈ cs) (miss : r.observed id c = none) : score r id cs = none := by
  induction cs with
  | nil => simp at mem
  | cons k ks ih =>
    rcases List.mem_cons.mp mem with same | later
    · subst k; simp [score, miss]
    · have hs := ih later
      cases h : r.observed id k <;> simp [score, h, hs]

structure Champion where
  id : Nat
  generation : Nat
  deriving DecidableEq, Repr

/-- An untrusted proposal carries its claimed review context, parent, and
candidate identity. There is no field through which it can set a score. -/
structure Proposal where
  review : Nat
  parent : Champion
  candidate : Nat
  deriving DecidableEq, Repr

def successor (h : Champion) (p : Proposal) : Champion :=
  ⟨p.candidate, h.generation + 1⟩

/-- Bind the request to the review and current lineage. Evaluate both IDs under
the same review. Require admission, preservation of declared detect rank, and
strict improvement on the complete fixed score. -/
def verify (r : Review) (h : Champion) (p : Proposal) : Option Champion := do
  if p.review ≠ r.version ∨ p.parent ≠ h then none else
    let old ← score r h.id r.cases
    let new ← score r p.candidate r.cases
    if admissible (r.mechanism p.candidate) &&
        decide (detectRank (r.mechanism h.id) ≤ detectRank (r.mechanism p.candidate) ∧ old < new)
    then some (successor h p) else none

/-- Independent declarative specification against the receiver's review. -/
def Licensed (r : Review) (h : Champion) (p : Proposal) : Prop :=
  p.review = r.version ∧ p.parent = h ∧ admissible (r.mechanism p.candidate) = true ∧
  detectRank (r.mechanism h.id) ≤ detectRank (r.mechanism p.candidate) ∧
  ∃ old new, score r h.id r.cases = some old ∧ score r p.candidate r.cases = some new ∧ old < new

theorem verify_exact (r : Review) (h out : Champion) (p : Proposal) :
    verify r h p = some out ↔ Licensed r h p ∧ out = successor h p := by
  by_cases ver : p.review = r.version <;> by_cases parent : p.parent = h <;>
    simp [verify, Licensed, ver, parent]
  cases score r h.id r.cases <;> cases score r p.candidate r.cases <;>
    simp
  intros
  exact eq_comm

/-- Reject a whole submitted path if any edge fails. -/
def replay (r : Review) : Champion → List Proposal → Option Champion
  | h, [] => some h
  | h, p :: ps => (verify r h p).bind (fun next => replay r next ps)

/-- Precisely the lists of licensed edges, rooted at the supplied champion. -/
inductive Lineage (r : Review) : Champion → List Proposal → Champion → Prop where
  | done (h) : Lineage r h [] h
  | step {h p ps out} : Licensed r h p → Lineage r (successor h p) ps out →
      Lineage r h (p :: ps) out

theorem replay_exact (r : Review) (h out : Champion) (ps : List Proposal) :
    replay r h ps = some out ↔ Lineage r h ps out := by
  induction ps generalizing h with
  | nil =>
    constructor
    · intro h'; simp [replay] at h'; cases h'; constructor
    · intro path; cases path; rfl
  | cons p ps ih =>
    constructor
    · intro ok
      cases eq : verify r h p with
      | none => simp [replay, eq] at ok
      | some next =>
        obtain ⟨license, rfl⟩ := (verify_exact ..).1 eq
        exact .step license ((ih _).1 (by simpa [replay, eq] using ok))
    · intro path
      cases path with
      | step license tail =>
        have eq := (verify_exact r h (successor h p) p).2 ⟨license, rfl⟩
        simpa [replay, eq] using (ih _).2 tail

/-- Every accepted path from an admitted, completely scored seed preserves the
formal class invariant. At least one additional correct answer is needed per
generation, bounding the total number of accepted promotions on one suite. -/
theorem lineage_budget {r : Review} {h out : Champion} {ps : List Proposal}
    (path : Lineage r h ps out) (initial : admissible (r.mechanism h.id) = true)
    (n : Nat) (base : score r h.id r.cases = some n) :
    admissible (r.mechanism out.id) = true ∧
    out.generation = h.generation + ps.length ∧
    ∃ m, score r out.id r.cases = some m ∧ n + ps.length ≤ m ∧ m ≤ r.cases.length := by
  induction path generalizing n with
  | done head =>
    exact ⟨initial, rfl, n, base, Nat.le_refl _, score_bounded _ _ _ _ base⟩
  | @step head p ps out license _ ih =>
    obtain ⟨_, _, nextOk, _, old, new, oldScore, newScore, better⟩ := license
    have ident : n = old := Option.some.inj (base.symm.trans oldScore)
    obtain ⟨ad, gen, m, ms, low, high⟩ := ih nextOk new newScore
    simp only [successor, List.length_cons] at gen ⊢
    exact ⟨ad, by omega, m, ms, by omega, high⟩

/-- This review has one measured case. On the held-out second case, the
strictly improving candidate changes a correct answer to an incorrect one. -/
private def fixture : Review :=
  { version := 9, cases := [0], label := fun _ => true
    observed := fun id c => some (decide (id = 1 ↔ c = 0))
    mechanism := fun _ => .jointChannel }

theorem finite_improvement_boundary :
    verify fixture ⟨0, 0⟩ ⟨9, ⟨0, 0⟩, 1⟩ = some ⟨1, 1⟩ ∧
    score fixture 0 [1] = some 1 ∧ score fixture 1 [1] = some 0 ∧
    verify fixture ⟨1, 1⟩ ⟨9, ⟨0, 0⟩, 1⟩ = none := by decide

#print axioms score_bounded
#print axioms missing_score
#print axioms verify_exact
#print axioms replay_exact
#print axioms lineage_budget
#print axioms finite_improvement_boundary

end PromotionReplay
