import Std
set_option autoImplicit false
/-! Specification of the fixed SQLite adapter's finite row abstraction.
    This is not a source-extraction theorem about Python, SQLite or external IO. -/
namespace PCSProgressAdapter
structure Rows where
  isPublic : Bool
  loaded : Bool
  sanitized : Bool
  published : Nat
  deriving DecidableEq, Repr

def privateInitial : Rows := ⟨false, false, false, 0⟩
def publicInitial : Rows := ⟨true, false, true, 0⟩
def privateLoaded : Rows := ⟨false, true, false, 0⟩
def ready : Rows := ⟨true, true, true, 0⟩
def done : Rows := ⟨true, true, true, 1⟩

def configurations : List (Nat × Rows) :=
  [(0, privateInitial), (0, publicInitial), (1, privateInitial),
   (1, publicInitial), (2, privateLoaded), (3, ready), (4, done)]
def Valid (s : Nat) (r : Rows) : Prop := (s,r) ∈ configurations
instance (s : Nat) (r : Rows) : Decidable (Valid s r) := by unfold Valid; infer_instance

/-- Full materialized row operation, including publication guards. -/
def step (s a : Nat) (r : Rows) : Option (Nat × Rows) :=
  if a = s then
    match s with
    | 0 => some (1,r)
    | 1 => some ((if r.isPublic then 3 else 2), {r with loaded := true})
    | 2 => some (3,{r with isPublic := true, sanitized := true})
    | 3 => if r.isPublic && r.loaded && r.sanitized then
        some (4,{r with published := r.published + 1}) else none
    | _ => none
  else none

def Edge (s a t : Nat) : Prop :=
  (s,a,t) ∈ [(0,0,1), (1,1,2), (1,1,3), (2,2,3), (3,3,4)]
instance (s a t : Nat) : Decidable (Edge s a t) := by unfold Edge; infer_instance

def rank (s : Nat) : Nat := 4 - s

theorem initial_valid (pre : Bool) :
    Valid 0 (if pre then publicInitial else privateInitial) := by
  cases pre <;> decide

/-- Every supported row operation refines a declared progress edge and preserves
    the complete fixed adapter invariant, conditional on that invariant initially. -/
theorem step_refines {s a t : Nat} {r out : Rows}
    (hv : Valid s r) (hs : step s a r = some (t,out)) :
    Valid t out ∧ Edge s a t ∧ rank t < rank s := by
  by_cases ha : a = s
  · subst a
    simp only [Valid, configurations, List.mem_cons, List.not_mem_nil, or_false,
      Prod.mk.injEq] at hv
    rcases hv with ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ |
      ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ <;>
      simp_all [step, privateInitial, publicInitial, privateLoaded, ready, done,
        Valid, configurations, Edge, rank] <;> omega
  · simp [step,ha] at hs

theorem valid_publication {s : Nat} {r : Rows} (h : Valid s r) :
    r.published ≤ 1 ∧ (r.published = 1 → r.isPublic = true ∧ r.loaded = true ∧
      r.sanitized = true ∧ s = 4) := by
  simp only [Valid, configurations, List.mem_cons, List.not_mem_nil, or_false,
    Prod.mk.injEq] at h
  rcases h with ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ |
    ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ <;> decide

theorem goal_halts (a : Nat) (r : Rows) : step 4 a r = none := by
  simp [step]

inductive Execution : Nat → Rows → Nat → Nat → Rows → Prop where
  | nil (s : Nat) (r : Rows) : Execution s r 0 s r
  | cons {s t u n : Nat} {r mid out : Rows} (a : Nat)
      (head : step s a r = some (t,mid))
      (tail : Execution t mid n u out) : Execution s r (n+1) u out

theorem execution_invariant {s t n : Nat} {r out : Rows}
    (hv : Valid s r) (he : Execution s r n t out) :
    Valid t out ∧ rank t + n ≤ rank s := by
  induction he with
  | nil s r => exact ⟨hv, by omega⟩
  | cons a head tail ih =>
    have one := step_refines hv head
    have rest := ih one.1
    exact ⟨rest.1, by omega⟩

theorem execution_no_private_publication {s t n : Nat} {r out : Rows}
    (hv : Valid s r) (he : Execution s r n t out) :
    out.published ≤ 1 ∧ (out.published = 1 → out.isPublic = true ∧
      out.loaded = true ∧ out.sanitized = true ∧ t = 4) :=
  valid_publication (execution_invariant hv he).1

theorem completion_rows {s t : Nat} {r out : Rows}
    (hv : Valid s r) (he : Execution s r (rank s) t out) :
    t = 4 ∧ out = done := by
  have result := execution_invariant hv he
  have zero : rank t = 0 := by omega
  have h := result.1
  simp only [Valid, configurations, List.mem_cons, List.not_mem_nil, or_false,
    Prod.mk.injEq] at h
  rcases h with ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ |
    ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ | ⟨rfl,rfl⟩ <;> simp_all [rank]
end PCSProgressAdapter
