import PCSRuntimeRefinement.Core

/-!
# Fuel monotonicity: resource exhaustion is the only budget-dependent outcome

`Res.le x y` — `x` is `fuel` (unresolved) or equal to `y`.  Every evaluator of the shared
semantics is monotone in fuel for this order: once a run with some budget returns a value or
an exception, every larger budget returns exactly the same.  Hence a run never fabricates a
budget-dependent answer; the only effect of a small budget is the explicit `fuel` outcome.
-/

namespace PCSRuntimeRefinement

/-- `x` is unresolved or agrees with `y`. -/
def Res.le {α : Type} (x y : Res α) : Prop := x = .fuel ∨ x = y

theorem Res.le_refl {α : Type} (x : Res α) : Res.le x x := Or.inr rfl

theorem Res.le_fuel {α : Type} (y : Res α) : Res.le .fuel y := Or.inl rfl

theorem Res.bind_mono {α β : Type} {x x' : Res α} {f g : α → Res β} (h : Res.le x x')
    (hf : ∀ a, Res.le (f a) (g a)) : Res.le (x.bind f) (x'.bind g) := by
  rcases h with h | h
  · subst h; exact Or.inl rfl
  · subst h
    cases x with
    | ok a => exact hf a
    | exc e => exact Or.inr rfl
    | fuel => exact Or.inl rfl

theorem Res.ite_mono {α : Type} (c : Prop) [Decidable c] {a a' b b' : Res α} (ha : Res.le a a')
    (hb : Res.le b b') : Res.le (if c then a else b) (if c then a' else b') := by
  split <;> assumption

theorem Res.le_ok {α : Type} {x : Res α} {a : α} (h : Res.le x (.ok a)) : x = .fuel ∨ x = .ok a := h

/-- **Fuel monotonicity of the whole interpreter.** -/
theorem fuel_mono (d : Dialect) : ∀ n m, n ≤ m →
    (∀ env e, Res.le (evalE d n env e) (evalE d m env e)) ∧
    (∀ env es, Res.le (evalL d n env es) (evalL d m env es)) ∧
    (∀ env elt p f xs, Res.le (evalComp d n env elt p f xs) (evalComp d m env elt p f xs)) ∧
    (∀ env s, Res.le (execS d n env s) (execS d m env s)) ∧
    (∀ env ss, Res.le (execB d n env ss) (execB d m env ss)) ∧
    (∀ env p body xs, Res.le (execFor d n env p body xs) (execFor d m env p body xs)) := by
  intro n
  induction n with
  | zero =>
      intro m _
      refine ⟨fun _ _ => ?_, fun _ _ => ?_, fun _ _ _ _ _ => ?_, fun _ _ => ?_, fun _ _ => ?_,
        fun _ _ _ _ => ?_⟩ <;> first
        | (simp only [evalE]; exact Res.le_fuel _)
        | (simp only [evalL]; exact Res.le_fuel _)
        | (simp only [evalComp]; exact Res.le_fuel _)
        | (simp only [execS]; exact Res.le_fuel _)
        | (simp only [execB]; exact Res.le_fuel _)
        | (simp only [execFor]; exact Res.le_fuel _)
  | succ n ih =>
      intro m hm
      obtain ⟨m, rfl⟩ : ∃ m', m = m' + 1 := ⟨m - 1, by omega⟩
      obtain ⟨hE, hL, hC, hS, hB, hF⟩ := ih m (by omega)
      have M := @Res.bind_mono
      have R := @Res.le_refl
      refine ⟨fun env e => ?_, fun env es => ?_, fun env elt p f xs => ?_, fun env s => ?_,
        fun env ss => ?_, fun env p body xs => ?_⟩
      · cases e <;> simp only [evalE]
        case var x => exact R _
        case lit => exact R _
        all_goals first
          | exact M (hL _ _) (fun _ => R _)
          | exact M (hE _ _) (fun _ => M (hE _ _) (fun _ => R _))
          | exact M (hE _ _) (fun _ => R _)
          | exact M (hE _ _) (fun _ => Res.ite_mono _ (hE _ _) (R _))
          | exact M (hE _ _) (fun _ => Res.ite_mono _ (hE _ _) (hE _ _))
          | exact M (hE _ _) (fun _ => M (hE _ _) (fun _ => M (R _) (fun _ => R _)))
          | exact M (hE _ _) (fun _ => M (R _) (fun _ => R _))
          | exact M (hE _ _) (fun _ => M (R _) (fun _ => M (hC _ _ _ _ _) (fun _ => R _)))
      · cases es <;> simp only [evalL]
        · exact R _
        · exact M (hE _ _) (fun _ => M (hL _ _) (fun _ => R _))
      · cases xs with
        | nil => cases f <;> simp only [evalComp] <;> exact R _
        | cons x xs =>
            cases f with
            | none =>
                simp only [evalComp]
                exact M (R _) (fun _ => M (hE _ _) (fun _ => M (hC _ _ _ _ _) (fun _ => R _)))
            | some c =>
                simp only [evalComp]
                exact M (R _) (fun _ => M (hE _ _) (fun _ =>
                  Res.ite_mono _ (M (hE _ _) (fun _ => M (hC _ _ _ _ _) (fun _ => R _))) (hC _ _ _ _ _)))
      · cases s <;> simp only [execS]
        case assign => exact M (hE _ _) (fun _ => R _)
        case augIndex x i op e =>
          split
          · exact R _
          · exact M (hE _ _) (fun _ => M (R _) (fun _ => M (hE _ _) (fun _ => R _)))
        case append x e =>
          split
          · exact M (hE _ _) (fun _ => R _)
          · exact R _
          · exact R _
        case forIn => exact M (hE _ _) (fun _ => M (R _) (fun _ => hF _ _ _ _))
        case ifThen => exact M (hE _ _) (fun _ => Res.ite_mono _ (M (hB _ _) (fun _ => R _)) (R _))
        case cont => exact R _
        case ret => exact M (hE _ _) (fun _ => R _)
      · cases ss <;> simp only [execB]
        · exact R _
        · exact M (hS _ _) (fun fl => by cases fl <;> first | exact hB _ _ | exact R _)
      · cases xs <;> simp only [execFor]
        · exact R _
        · exact M (R _) (fun _ => M (hB _ _) (fun fl => by cases fl <;> first | exact hF _ _ _ _ | exact R _))

/-- Function calls are fuel-monotone. -/
theorem callFn_mono (d : Dialect) (f : Fn) (args : List Val) {n m : Nat} (h : n ≤ m) :
    Res.le (callFn d n f args) (callFn d m f args) := by
  unfold callFn
  split
  · exact Res.le_refl _
  · exact Res.bind_mono ((fuel_mono d n m h).2.2.2.2.1 _ _) (fun _ => Res.le_refl _)

/-- **Every budget gives the eventual answer or the explicit unresolved outcome.** -/
theorem callFn_fuel_or_eventual {d : Dialect} {f : Fn} {args : List Val} {r : Res Val}
    (h : ∃ N, ∀ fuel, N ≤ fuel → callFn d fuel f args = r) (fuel : Nat) :
    callFn d fuel f args = .fuel ∨ callFn d fuel f args = r := by
  obtain ⟨N, hN⟩ := h
  have := callFn_mono d f args (Nat.le_max_left fuel N)
  rwa [hN _ (Nat.le_max_right fuel N)] at this

end PCSRuntimeRefinement
