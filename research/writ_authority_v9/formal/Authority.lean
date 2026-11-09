import Std

/-!
Writ/9 research: kernel-checkable *abstract* compositional authority.

The model covers action/label/byte scope attenuation, arbitrarily long
well-formed delegation paths, persistent ancestor revocation, and sequential
atomic hierarchical quota debits. It does NOT establish Python refinement,
cryptographic soundness, host actor authentication or tool-effect correctness.

No sorry, admit, unsafe, opaque trusted checker, or new axioms.
-/
namespace Writ9

structure Scope where
  actions : List Nat
  clearance : Nat
  maxBytes : Nat
  quota : Nat

def Attenuates (child parent : Scope) : Prop :=
  (∀ a, a ∈ child.actions → a ∈ parent.actions) ∧
  child.clearance ≤ parent.clearance ∧
  child.maxBytes ≤ parent.maxBytes ∧
  child.quota ≤ parent.quota

def Allows (s : Scope) (action label bytes : Nat) : Prop :=
  action ∈ s.actions ∧ label ≤ s.clearance ∧ bytes ≤ s.maxBytes

theorem attenuation_reflexive (s : Scope) : Attenuates s s := by
  exact ⟨(fun _ h => h), Nat.le_refl _, Nat.le_refl _, Nat.le_refl _⟩

theorem attenuation_transitive {leaf mid root : Scope}
    (h₁ : Attenuates leaf mid) (h₂ : Attenuates mid root) :
    Attenuates leaf root := by
  exact ⟨(fun x hx => h₂.1 x (h₁.1 x hx)),
         Nat.le_trans h₁.2.1 h₂.2.1,
         Nat.le_trans h₁.2.2.1 h₂.2.2.1,
         Nat.le_trans h₁.2.2.2 h₂.2.2.2⟩

theorem authorized_child_implies_parent {child parent : Scope}
    (h : Attenuates child parent) {a label bytes : Nat}
    (authorized : Allows child a label bytes) : Allows parent a label bytes := by
  exact ⟨h.1 a authorized.1,
         Nat.le_trans authorized.2.1 h.2.1,
         Nat.le_trans authorized.2.2 h.2.2.1⟩

theorem three_hop_nonamplification {leaf mid root : Scope}
    (h₁ : Attenuates leaf mid) (h₂ : Attenuates mid root)
    {a label bytes : Nat} (ok : Allows leaf a label bytes) :
    Allows root a label bytes := by
  exact authorized_child_implies_parent (attenuation_transitive h₁ h₂) ok

/-- A delegation path has a scoped attenuation at every link. -/
def SafeChain (root : Scope) : List Scope → Prop
  | [] => True
  | child :: rest => Attenuates child root ∧ SafeChain child rest

def LastScope (root : Scope) : List Scope → Scope
  | [] => root
  | child :: rest => LastScope child rest

/-- The *entire* descendant chain is no more powerful than its root. -/
theorem arbitrary_chain_attenuation (root : Scope) (chain : List Scope) :
    SafeChain root chain → Attenuates (LastScope root chain) root := by
  induction chain generalizing root with
  | nil =>
      intro _
      exact attenuation_reflexive root
  | cons child rest ih =>
      intro h
      exact attenuation_transitive (ih child h.2) h.1

theorem arbitrary_chain_nonamplification (root : Scope) (chain : List Scope)
    {a label bytes : Nat} (safe : SafeChain root chain)
    (ok : Allows (LastScope root chain) a label bytes) :
    Allows root a label bytes := by
  exact authorized_child_implies_parent (arbitrary_chain_attenuation root chain safe) ok

/-!
Shared ancestor quota model. Each *successful* admission atomically debits
every distinct delegation identifier in a path exactly once. This proof
depends on those assumptions: it is not a correctness proof for SQLite.
-/
def CanDebit (path : List Nat) (balance : Nat → Nat) : Prop :=
  ∀ id, id ∈ path → 0 < balance id

def Debit (path : List Nat) (balance : Nat → Nat) (id : Nat) : Nat :=
  if id ∈ path then balance id - 1 else balance id

def Used (id : Nat) : List (List Nat) → Nat
  | [] => 0
  | path :: tail => Used id tail + (if id ∈ path then 1 else 0)

inductive Runs : (Nat → Nat) → List (List Nat) → (Nat → Nat) → Prop where
  | done (r : Nat → Nat) : Runs r [] r
  | consume (r : Nat → Nat) (path : List Nat)
      (tail : List (List Nat)) (ending : Nat → Nat)
      (enough : CanDebit path r)
      (next : Runs (Debit path r) tail ending) :
      Runs r (path :: tail) ending

theorem debit_conservation (path : List Nat) (before : Nat → Nat)
    (enough : CanDebit path before) (id : Nat) :
    before id = Debit path before id + (if id ∈ path then 1 else 0) := by
  by_cases h : id ∈ path
  · have hpos : 0 < before id := enough id h
    simp [Debit, h]
    omega
  · simp [Debit, h]

/-- Exact accounting over arbitrarily many sequential admissions. -/
theorem trace_quota_conservation {before after : Nat → Nat}
    {trace : List (List Nat)} (run : Runs before trace after) (id : Nat) :
    before id = after id + Used id trace := by
  induction run with
  | done _ => simp [Used]
  | consume r path tail ending enough next ih =>
      have hstep := debit_conservation path r enough id
      rw [ih] at hstep
      simpa [Used, Nat.add_assoc] using hstep

/-- No ancestor can be consumed more times than its original quota. -/
theorem trace_no_overspend {before after : Nat → Nat}
    {trace : List (List Nat)} (run : Runs before trace after) (id : Nat) :
    Used id trace ≤ before id := by
  have eq := trace_quota_conservation run id
  omega

def NotRevoked (path : List Nat) (revoked : Nat → Bool) : Prop :=
  ∀ id, id ∈ path → revoked id = false

/-- Any revoked ancestor blocks admission; no descendant can mask it. -/
theorem ancestor_revocation_blocks (path : List Nat) (revoked : Nat → Bool)
    (id : Nat) (inPath : id ∈ path) (rev : revoked id = true) :
    ¬ NotRevoked path revoked := by
  intro h
  have notRev := h id inPath
  simp [rev] at notRev

end Writ9
