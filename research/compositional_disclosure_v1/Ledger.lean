import Std.Tactic
set_option autoImplicit false
namespace PCSDisclosure
-- Four binary records; query is a public subset mask. Secret: record zero.
def bit (w i : Nat) : Bool := w / 2^i % 2 == 1
def answer (q w : Nat) : Nat := ((List.range 4).filter fun i => bit q i && bit w i).length
def secret (w : Nat) : Bool := bit w 0
def cell (k : List Nat) (q v : Nat) : List Nat := k.filter fun w => answer q w == v
def ambiguous (k : List Nat) : Bool := k.any secret && k.any (fun w => !secret w)
-- Check EVERY possible answer, not only the actual world's answer.
def safe (k : List Nat) (q : Nat) : Bool := k.all fun w => ambiguous (cell k q (answer q w))
def step (k : List Nat) (w q : Nat) : List Nat × Option Nat :=
  if safe k q then (cell k q (answer q w),some (answer q w)) else (k,none)
def run (k : List Nat) (w : Nat) : List Nat → List Nat × List (Option Nat)
  | [] => (k,[])
  | q::qs => let s := step k w q; let tail := run s.1 w qs; (tail.1,s.2::tail.2)

theorem actual_retained (k : List Nat) (w q : Nat) (h : w ∈ k) : w ∈ (step k w q).1 := by
  unfold step; split
  · simp [cell,h]
  · exact h

theorem safe_all_cells (k : List Nat) (w q : Nat) (hw : w ∈ k) (hs : safe k q = true) :
    ambiguous (cell k q (answer q w)) = true := by
  exact List.all_eq_true.mp hs w hw

theorem step_preserves_ambiguity (k : List Nat) (w q : Nat)
    (hw : w ∈ k) (hk : ambiguous k = true) : ambiguous (step k w q).1 = true := by
  unfold step; split
  · rename_i hs; exact safe_all_cells k w q hw hs
  · exact hk

theorem arbitrary_history_preserves_actual (qs k : List Nat) (w : Nat) (hw : w ∈ k) :
    w ∈ (run k w qs).1 := by
  induction qs generalizing k with
  | nil => exact hw
  | cons q qs ih => exact ih _ (actual_retained k w q hw)

theorem arbitrary_history_preserves_ambiguity (qs k : List Nat) (w : Nat)
    (hw : w ∈ k) (hk : ambiguous k = true) : ambiguous (run k w qs).1 = true := by
  induction qs generalizing k with
  | nil => exact hk
  | cons q qs ih => exact ih _ (actual_retained k w q hw) (step_preserves_ambiguity k w q hw hk)

theorem ambiguity_has_two_witnesses (k : List Nat) (h : ambiguous k = true) :
    (∃ w ∈ k, secret w = true) ∧ (∃ w ∈ k, secret w = false) := by
  simp [ambiguous,Bool.and_eq_true,List.any_eq_true] at h
  exact h

theorem cannot_determine_protected_bit (qs k : List Nat) (w : Nat)
    (hw : w ∈ k) (hk : ambiguous k = true) :
    (∃ a ∈ (run k w qs).1, secret a = true) ∧
    (∃ b ∈ (run k w qs).1, secret b = false) :=
  ambiguity_has_two_witnesses _ (arbitrary_history_preserves_ambiguity qs k w hw hk)

theorem denial_independent_of_actual (k : List Nat) (a b q : Nat) :
    (step k a q).2.isSome = (step k b q).2.isSome := by
  unfold step; split <;> rfl

theorem accepted_answer_exact (k : List Nat) (w q v : Nat) (h : (step k w q).2 = some v) :
    v = answer q w ∧ (step k w q).1 = cell k q v := by
  by_cases hs : safe k q = true
  · simp only [step,hs,if_true,Option.some.injEq] at h
    simp [step,hs,h]
  · simp [step,hs] at h

theorem denied_changes_nothing (k : List Nat) (w q : Nat) (h : safe k q = false) :
    step k w q = (k,none) := by simp [step,h]

-- Exact consistency, rather than merely a heuristic candidate set.
theorem step_candidate_exact (k : List Nat) (a b q : Nat) :
    b ∈ (step k a q).1 ↔ b ∈ k ∧ (step k b q).2 = (step k a q).2 := by
  by_cases hs : safe k q = true
  · simp [step,hs,cell]
  · simp [step,hs]

theorem same_output_same_posterior (k : List Nat) (a b q : Nat)
    (h : (step k b q).2 = (step k a q).2) : step k b q = step k a q := by
  by_cases hs : safe k q = true
  · simp only [step,hs,if_true,Option.some.injEq] at h
    simp [step,hs,h]
  · simp [step,hs]

theorem posterior_exact (qs k : List Nat) (a b : Nat) :
    b ∈ (run k a qs).1 ↔ b ∈ k ∧ (run k b qs).2 = (run k a qs).2 := by
  induction qs generalizing k with
  | nil => simp [run]
  | cons q qs ih =>
    change b ∈ (run (step k a q).1 a qs).1 ↔ _
    rw [ih,step_candidate_exact]
    constructor
    · rintro ⟨⟨hb,hs⟩,ht⟩
      have he := same_output_same_posterior k a b q hs
      exact ⟨hb,by simp [run,he,ht]⟩
    · rintro ⟨hb,ht⟩
      have hs : (step k b q).2 = (step k a q).2 := (List.cons.inj ht).1
      have he := same_output_same_posterior k a b q hs
      exact ⟨⟨hb,hs⟩,by simpa [run,he] using (List.cons.inj ht).2⟩

-- The planner is explicitly a function of PUBLIC history, with no world argument.
def adaptive (planner : List (Nat × Option Nat) → Nat) (w : Nat) :
    Nat → List Nat → List (Nat × Option Nat) → List Nat × List (Nat × Option Nat)
  | 0,k,_ => (k,[])
  | n+1,k,h =>
    let q := planner h
    let s := step k w q
    let t := adaptive planner w n s.1 (h ++ [(q,s.2)])
    (t.1,(q,s.2)::t.2)

theorem adaptive_retains_actual (planner : List (Nat × Option Nat) → Nat)
    (n : Nat) (k : List Nat) (w : Nat) (h : List (Nat × Option Nat)) (hw : w ∈ k) :
    w ∈ (adaptive planner w n k h).1 := by
  induction n generalizing k h with
  | zero => exact hw
  | succ n ih => exact ih _ _ (actual_retained k w (planner h) hw)

theorem adaptive_preserves_ambiguity (planner : List (Nat × Option Nat) → Nat)
    (n : Nat) (k : List Nat) (w : Nat) (h : List (Nat × Option Nat))
    (hw : w ∈ k) (hk : ambiguous k = true) :
    ambiguous (adaptive planner w n k h).1 = true := by
  induction n generalizing k h with
  | zero => exact hk
  | succ n ih =>
    exact ih _ _ (actual_retained k w (planner h) hw) (step_preserves_ambiguity k w (planner h) hw hk)

theorem adaptive_posterior_exact (planner : List (Nat × Option Nat) → Nat)
    (n : Nat) (k : List Nat) (a b : Nat) (h : List (Nat × Option Nat)) :
    b ∈ (adaptive planner a n k h).1 ↔
      b ∈ k ∧ (adaptive planner b n k h).2 = (adaptive planner a n k h).2 := by
  induction n generalizing k h with
  | zero => simp [adaptive]
  | succ n ih =>
    change b ∈ (adaptive planner a n (step k a (planner h)).1
      (h ++ [(planner h,(step k a (planner h)).2)])).1 ↔ _
    rw [ih,step_candidate_exact]
    constructor
    · rintro ⟨⟨hb,hs⟩,ht⟩
      have he := same_output_same_posterior k a b (planner h) hs
      exact ⟨hb,by simp [adaptive,he,ht]⟩
    · rintro ⟨hb,ht⟩
      have hs : (step k b (planner h)).2 = (step k a (planner h)).2 :=
        (Prod.mk.inj (List.cons.inj ht).1).2
      have he := same_output_same_posterior k a b (planner h) hs
      exact ⟨⟨hb,hs⟩,by simpa [adaptive,he] using (List.cons.inj ht).2⟩

theorem adaptive_public_transcript_has_both_secrets
    (planner : List (Nat × Option Nat) → Nat) (n : Nat) (k : List Nat) (w : Nat)
    (h : List (Nat × Option Nat)) (hw : w ∈ k) (hk : ambiguous k = true) :
    ∃ a ∈ k, ∃ b ∈ k, secret a = true ∧ secret b = false ∧
      (adaptive planner a n k h).2 = (adaptive planner w n k h).2 ∧
      (adaptive planner b n k h).2 = (adaptive planner w n k h).2 := by
  obtain ⟨⟨a,ha,hsa⟩,⟨b,hb,hsb⟩⟩ :=
    ambiguity_has_two_witnesses _ (adaptive_preserves_ambiguity planner n k w h hw hk)
  have aa := (adaptive_posterior_exact planner n k w a h).mp ha
  have bb := (adaptive_posterior_exact planner n k w b h).mp hb
  exact ⟨a,aa.1,b,bb.1,hsa,hsb,aa.2,bb.2⟩

def initial : List Nat := (List.range 16).filter fun w => answer 15 w == 2
-- Queries on bits 1,2,3 are individually safe but their JOINT answers reveal bit 0.
def independentRun (w : Nat) : List Nat := [2,4,8].map fun q => answer q w
theorem all_three_individually_safe : [2,4,8].all (safe initial) = true := by decide
theorem stateless_composition_discloses :
    (initial.filter fun w => independentRun w == independentRun 3) = [3] := by decide
theorem ledger_blocks_composition : (run initial 3 [2,4,8]).2 = [some 1,none,none] := by decide
theorem initial_ambiguous : ambiguous initial = true := by decide

def worlds (lo hi : UInt8) : List Nat := (List.range 16).filter fun w =>
  if w < 8 then bit lo.toNat w else bit hi.toNat (w-8)
def encode (k : List Nat) (offset : Nat) : UInt8 := UInt8.ofNat
  (((List.range 8).filter fun i => offset+i ∈ k).foldl (fun n i => n+2^i) 0)
def process : List UInt8 → List UInt8
 | [4,lo,hi,w,q] =>
   let k := worlds lo hi
   if w.toNat < 16 ∧ q.toNat < 16 ∧ w.toNat ∈ k ∧ ambiguous k = true then
     let s := step k w.toNat q.toNat
     [4,if s.2.isSome then 1 else 0,encode s.1 0,encode s.1 8,UInt8.ofNat (s.2.getD 255)]
   else [4,2,0,0,255]
 | _ => [4,2,0,0,255]
theorem malformed_refuses (raw : List UInt8) (h : raw.length ≠ 5) : process raw = [4,2,0,0,255] := by
  unfold process
  split <;> simp_all
end PCSDisclosure
