import PCSConditionalRuntime.Semantics

/-!
# Fuel monotonicity of the heap interpreter

`Out.le x y` — `x` is `fuel` or equals `y`.  If level `r` is below level `r'` pointwise, then
every evaluation at the level built on `r` is below the same evaluation built on `r'`
(`evalE_mono`, …, `mkLevel_mono`).  Hence `interp c k ≤ interp c k'` for `k ≤ k'`
(`interp_mono`): **a run that produces a value or an exception with some fuel produces exactly
the same value/exception, heap and store with all larger fuel**, and `fuel` is the only
outcome that more fuel can change.
-/

namespace PCSCR

def Out.le {α : Type} (x y : Out α) : Prop := x = .fuel ∨ x = y

theorem Out.le_refl {α : Type} (x : Out α) : x.le x := Or.inr rfl

theorem Out.le_trans {α : Type} {x y z : Out α} (h1 : x.le y) (h2 : y.le z) : x.le z := by
  rcases h1 with rfl | rfl
  · exact Or.inl rfl
  · exact h2

theorem Out.le_app {α β : Type} {x x' : Out α} {F G : Out α → Out β} (h : x.le x')
    (hF : F .fuel = .fuel) (hFG : ∀ z, (F z).le (G z)) : (F x).le (G x') := by
  rcases h with rfl | rfl
  · rw [hF]; exact Or.inl rfl
  · exact hFG x

theorem Out.bind_mono {α β : Type} {x x' : Out α} {f g : α → Heap → Out β} (h : x.le x')
    (hfg : ∀ a h, (f a h).le (g a h)) : (x.bind f).le (x'.bind g) :=
  Out.le_app (F := fun z => z.bind f) (G := fun z => z.bind g) h rfl
    (fun z => by cases z <;> simp only [Out.bind] <;> first | exact hfg _ _ | exact Out.le_refl _)

theorem bindS_mono {env : Env} {x x' : Out V} {f g : V → Heap → Out Flow} (h : x.le x')
    (hfg : ∀ a h, (f a h).le (g a h)) : (bindS env x f).le (bindS env x' g) :=
  Out.le_app (F := fun z => bindS env z f) (G := fun z => bindS env z g) h rfl
    (fun z => by cases z <;> simp only [bindS] <;> first | exact hfg _ _ | exact Out.le_refl _)

theorem bindE_mono {env : Env} {x x' : Out Env} {f g : Env → Heap → Out Flow} (h : x.le x')
    (hfg : ∀ a h, (f a h).le (g a h)) : (bindE env x f).le (bindE env x' g) :=
  Out.le_app (F := fun z => bindE env z f) (G := fun z => bindE env z g) h rfl
    (fun z => by cases z <;> simp only [bindE] <;> first | exact hfg _ _ | exact Out.le_refl _)

theorem seqF_mono {x x' : Out Flow} {f g : Env → Heap → Out Flow} (h : x.le x')
    (hfg : ∀ a h, (f a h).le (g a h)) : (seqF x f).le (seqF x' g) :=
  Out.le_app (F := fun z => seqF z f) (G := fun z => seqF z g) h rfl
    (fun z => by
      rcases z with ⟨fl, h⟩ | ⟨e, h⟩ | _
      · cases fl <;> simp only [seqF] <;> first | exact hfg _ _ | exact Out.le_refl _
      · exact Out.le_refl _
      · exact Out.le_refl _)

theorem loopK_mono {x x' : Out Flow} {f g : Env → Heap → Out Flow} (h : x.le x')
    (hfg : ∀ a h, (f a h).le (g a h)) : (loopK x f).le (loopK x' g) :=
  Out.le_app (F := fun z => loopK z f) (G := fun z => loopK z g) h rfl
    (fun z => by
      rcases z with ⟨fl, h⟩ | ⟨e, h⟩ | _
      · cases fl <;> simp only [loopK] <;> first | exact hfg _ _ | exact Out.le_refl _
      · exact Out.le_refl _
      · exact Out.le_refl _)

theorem onRaise_mono {x x' : Out Flow} {f g : Exc → Env → Heap → Out Flow} (h : x.le x')
    (hfg : ∀ e a h, (f e a h).le (g e a h)) : (onRaise x f).le (onRaise x' g) :=
  Out.le_app (F := fun z => onRaise z f) (G := fun z => onRaise z g) h rfl
    (fun z => by
      rcases z with ⟨fl, h⟩ | ⟨e, h⟩ | _
      · cases fl <;> simp only [onRaise] <;> first | exact hfg _ _ _ | exact Out.le_refl _
      · exact Out.le_refl _
      · exact Out.le_refl _)

theorem fuelpres_mono {α β : Type} {F : Out α → Out β} (hF : F .fuel = .fuel) {x x' : Out α}
    (h : x.le x') : (F x).le (F x') :=
  Out.le_app h hF (fun _ => Out.le_refl _)

theorem eraseAfter_mono {x : String} {y y' : Out Flow} (h : y.le y') : (eraseAfter x y).le (eraseAfter x y') :=
  fuelpres_mono (F := eraseAfter x) rfl h

theorem compResult_mono {a : Nat} {y y' : Out Flow} (h : y.le y') : (compResult a y).le (compResult a y') :=
  fuelpres_mono (F := compResult a) rfl h

theorem finishCall_mono {d : Dialect} {y y' : Out Flow} (h : y.le y') : (finishCall d y).le (finishCall d y') :=
  fuelpres_mono (F := finishCall d) rfl h

theorem ite_mono {α : Type} {p : Prop} [Decidable p] {a a' b b' : Out α} (h1 : p → a.le a')
    (h2 : ¬ p → b.le b') : (if p then a else b).le (if p then a' else b') := by
  by_cases hp : p
  · simp only [hp, if_true]; exact h1 hp
  · simp only [hp, if_false]; exact h2 hp

structure Lvl.le (r r' : Lvl) : Prop where
  call : ∀ f args h, (r.call f args h).le (r'.call f args h)
  forLoop : ∀ env h t v k body, (r.forLoop env h t v k body).le (r'.forLoop env h t v k body)
  whileLoop : ∀ env h e body, (r.whileLoop env h e body).le (r'.whileLoop env h e body)

variable {c : Ctx} {r r' : Lvl}

mutual
theorem evalE_mono (hr : r.le r') : ∀ env h e, (evalE c r env h e).le (evalE c r' env h e)
  | env, h, .var x => by simp only [evalE]; exact Out.le_refl _
  | env, h, .lit v => by simp only [evalE]; exact Out.le_refl _
  | env, h, .tup es => by simp only [evalE]; exact Out.bind_mono (evalL_mono hr env h es) (fun _ _ => Out.le_refl _)
  | env, h, .listD es => by simp only [evalE]; exact Out.bind_mono (evalL_mono hr env h es) (fun _ _ => Out.le_refl _)
  | env, h, .dictD es => by simp only [evalE]; exact Out.bind_mono (evalL_mono hr env h es) (fun _ _ => Out.le_refl _)
  | env, h, .setD es => by simp only [evalE]; exact Out.bind_mono (evalL_mono hr env h es) (fun _ _ => Out.le_refl _)
  | env, h, .attr e f => by simp only [evalE]; exact Out.bind_mono (evalE_mono hr env h e) (fun _ _ => Out.le_refl _)
  | env, h, .sub e i => by
      simp only [evalE]
      exact Out.bind_mono (evalE_mono hr env h e) (fun _ h => Out.bind_mono (evalE_mono hr env h i) (fun _ _ => Out.le_refl _))
  | env, h, .sliceFrom e i => by
      simp only [evalE]
      exact Out.bind_mono (evalE_mono hr env h e) (fun _ h => Out.bind_mono (evalE_mono hr env h i) (fun _ _ => Out.le_refl _))
  | env, h, .bin op a b => by
      simp only [evalE]
      exact Out.bind_mono (evalE_mono hr env h a) (fun _ h => Out.bind_mono (evalE_mono hr env h b) (fun _ _ => Out.le_refl _))
  | env, h, .cmp2 op1 op2 a b e3 => by
      simp only [evalE]
      exact Out.bind_mono (evalE_mono hr env h a) (fun _ h => Out.bind_mono (evalE_mono hr env h b) (fun _ h =>
        Out.bind_mono (Out.le_refl _) (fun _ h => ite_mono
          (fun _ => Out.bind_mono (evalE_mono hr env h e3) (fun _ _ => Out.le_refl _)) (fun _ => Out.le_refl _))))
  | env, h, .not a => by simp only [evalE]; exact Out.bind_mono (evalE_mono hr env h a) (fun _ _ => Out.le_refl _)
  | env, h, .and a b => by
      simp only [evalE]
      exact Out.bind_mono (evalE_mono hr env h a) (fun _ h => ite_mono (fun _ => evalE_mono hr env h b) (fun _ => Out.le_refl _))
  | env, h, .or a b => by
      simp only [evalE]
      exact Out.bind_mono (evalE_mono hr env h a) (fun _ h => ite_mono (fun _ => Out.le_refl _) (fun _ => evalE_mono hr env h b))
  | env, h, .cond e t f => by
      simp only [evalE]
      exact Out.bind_mono (evalE_mono hr env h e) (fun _ h => ite_mono (fun _ => evalE_mono hr env h t) (fun _ => evalE_mono hr env h f))
  | env, h, .isNone a neg => by simp only [evalE]; exact Out.bind_mono (evalE_mono hr env h a) (fun _ _ => Out.le_refl _)
  | env, h, .typeIs a ty neg => by simp only [evalE]; exact Out.bind_mono (evalE_mono hr env h a) (fun _ _ => Out.le_refl _)
  | env, h, .mem x e neg => by
      simp only [evalE]
      exact Out.bind_mono (evalE_mono hr env h x) (fun _ h => Out.bind_mono (evalE_mono hr env h e) (fun _ _ => Out.le_refl _))
  | env, h, .call f args => by
      simp only [evalE]
      refine ite_mono (fun _ => Out.bind_mono (evalL_mono hr env h args) (fun _ _ => hr.call _ _ _)) (fun _ => ?_)
      split
      · exact Out.bind_mono (evalL_mono hr env h args) (fun _ _ => ite_mono (fun _ => Out.le_refl _)
          (fun _ => Out.bind_mono (hr.call _ _ _) (fun _ _ => Out.le_refl _)))
      · exact ite_mono (fun _ => Out.bind_mono (evalL_mono hr env h args) (fun _ _ => Out.le_refl _))
          (fun _ => Out.bind_mono (evalL_mono hr env h args) (fun _ _ => Out.le_refl _))
  | env, h, .mcall o m args => by
      simp only [evalE]
      refine Out.bind_mono (evalE_mono hr env h o) (fun vo h => Out.bind_mono (evalL_mono hr env h args) (fun vs h => ?_))
      split
      · split
        · exact ite_mono (fun _ => hr.call _ _ _) (fun _ => Out.le_refl _)
        · exact Out.le_refl _
      · exact Out.le_refl _
  | env, h, .kwcall o m ks args => by
      simp only [evalE]
      exact Out.bind_mono (evalE_mono hr env h o) (fun _ h => Out.bind_mono (evalL_mono hr env h args) (fun _ _ => Out.le_refl _))
  | env, h, .comp elt x it filt => by
      simp only [evalE]
      exact Out.bind_mono (evalE_mono hr env h it) (fun _ _ => compResult_mono (hr.forLoop _ _ _ _ _ _))
theorem evalL_mono (hr : r.le r') : ∀ env h es, (evalL c r env h es).le (evalL c r' env h es)
  | env, h, [] => by simp only [evalL]; exact Out.le_refl _
  | env, h, e :: es => by
      simp only [evalL]
      exact Out.bind_mono (evalE_mono hr env h e) (fun _ h => Out.bind_mono (evalL_mono hr env h es) (fun _ _ => Out.le_refl _))
end

mutual
theorem assignT_mono (hr : r.le r') : ∀ env h v t, (assignT c r env h v t).le (assignT c r' env h v t)
  | env, h, v, .name x => by simp only [assignT]; exact Out.le_refl _
  | env, h, v, .attr e f => by
      simp only [assignT]; exact Out.bind_mono (evalE_mono hr env h e) (fun _ _ => Out.le_refl _)
  | env, h, v, .sub e i => by
      simp only [assignT]
      exact Out.bind_mono (evalE_mono hr env h e) (fun _ h => Out.bind_mono (evalE_mono hr env h i) (fun _ _ => Out.le_refl _))
  | env, h, v, .tup ts => by
      simp only [assignT]
      split
      · exact ite_mono (fun _ => assignTs_mono hr env h _ ts) (fun _ => Out.le_refl _)
      · exact Out.le_refl _
theorem assignTs_mono (hr : r.le r') : ∀ env h vs ts, (assignTs c r env h vs ts).le (assignTs c r' env h vs ts)
  | env, h, v :: vs, t :: ts => by
      simp only [assignTs]
      exact Out.bind_mono (assignT_mono hr env h v t) (fun env h => assignTs_mono hr env h vs ts)
  | env, h, [], _ => by simp only [assignTs]; exact Out.le_refl _
  | env, h, _ :: _, [] => by simp only [assignTs]; exact Out.le_refl _
end

theorem assignAll_mono (hr : r.le r') : ∀ env h v ts, (assignAll c r env h v ts).le (assignAll c r' env h v ts)
  | env, h, v, [] => by simp only [assignAll]; exact Out.le_refl _
  | env, h, v, t :: ts => by
      simp only [assignAll]
      exact Out.bind_mono (assignT_mono hr env h v t) (fun env h => assignAll_mono hr env h v ts)

mutual
theorem execS_mono (hr : r.le r') : ∀ env h s, (execS c r env h s).le (execS c r' env h s)
  | env, h, .assign ts e => by
      simp only [execS]
      exact bindS_mono (evalE_mono hr env h e) (fun v h => bindE_mono (assignAll_mono hr env h v ts) (fun _ _ => Out.le_refl _))
  | env, h, .aug t op e => by
      simp only [execS]
      split
      · split
        · exact Out.le_refl _
        · exact bindS_mono (evalE_mono hr env h e) (fun _ _ => Out.le_refl _)
      · exact bindS_mono (evalE_mono hr env h _) (fun _ h => bindS_mono (Out.le_refl _) (fun _ h =>
          bindS_mono (evalE_mono hr env h e) (fun _ _ => Out.le_refl _)))
      · exact Out.le_refl _
  | env, h, .expr e => by
      simp only [execS]; exact bindS_mono (evalE_mono hr env h e) (fun _ _ => Out.le_refl _)
  | env, h, .ifte e t f => by
      simp only [execS]
      exact bindS_mono (evalE_mono hr env h e) (fun _ h => ite_mono (fun _ => execB_mono hr env h t) (fun _ => execB_mono hr env h f))
  | env, h, .forIn t it body => by
      simp only [execS]; exact bindS_mono (evalE_mono hr env h it) (fun _ _ => hr.forLoop _ _ _ _ _ _)
  | env, h, .while e body => by simp only [execS]; exact hr.whileLoop _ _ _ _
  | env, h, .ret e => by simp only [execS]; exact bindS_mono (evalE_mono hr env h e) (fun _ _ => Out.le_refl _)
  | env, h, .brk => by simp only [execS]; exact Out.le_refl _
  | env, h, .raise e => by simp only [execS]; exact bindS_mono (evalE_mono hr env h e) (fun _ _ => Out.le_refl _)
  | env, h, .try body cls x handler => by
      simp only [execS]
      exact onRaise_mono (execB_mono hr env h body) (fun ex env' h' =>
        ite_mono (fun _ => eraseAfter_mono (execB_mono hr _ h' handler)) (fun _ => Out.le_refl _))
  | env, h, .assert e => by simp only [execS]; exact bindS_mono (evalE_mono hr env h e) (fun _ _ => Out.le_refl _)
  | env, h, .pass => by simp only [execS]; exact Out.le_refl _
theorem execB_mono (hr : r.le r') : ∀ env h ss, (execB c r env h ss).le (execB c r' env h ss)
  | env, h, [] => by simp only [execB]; exact Out.le_refl _
  | env, h, s :: ss => by
      simp only [execB]
      exact seqF_mono (execS_mono hr env h s) (fun env h => execB_mono hr env h ss)
end

theorem mkLevel_mono (hr : r.le r') : (mkLevel c r).le (mkLevel c r') where
  call f args h := by
    simp only [mkLevel, callBody]
    split
    · exact Out.le_refl _
    · exact ite_mono (fun _ => Out.le_refl _) (fun _ => finishCall_mono (execB_mono hr _ _ _))
  forLoop env h t v k body := by
    simp only [mkLevel, forIter]
    split
    · exact Out.le_refl _
    · exact Out.le_refl _
    · exact bindE_mono (assignT_mono hr _ _ _ _) (fun _ _ => loopK_mono (execB_mono hr _ _ _) (fun _ _ => hr.forLoop _ _ _ _ _ _))
  whileLoop env h e body := by
    simp only [mkLevel, whileIter]
    exact bindS_mono (evalE_mono hr _ _ _) (fun _ _ => ite_mono
      (fun _ => loopK_mono (execB_mono hr _ _ _) (fun _ _ => hr.whileLoop _ _ _ _)) (fun _ => Out.le_refl _))

theorem Lvl.le_refl (r : Lvl) : r.le r :=
  ⟨fun _ _ _ => Out.le_refl _, fun _ _ _ _ _ _ => Out.le_refl _, fun _ _ _ _ => Out.le_refl _⟩

theorem Lvl.le_trans {r1 r2 r3 : Lvl} (h1 : r1.le r2) (h2 : r2.le r3) : r1.le r3 :=
  ⟨fun _ _ _ => Out.le_trans (h1.call _ _ _) (h2.call _ _ _),
   fun _ _ _ _ _ _ => Out.le_trans (h1.forLoop _ _ _ _ _ _) (h2.forLoop _ _ _ _ _ _),
   fun _ _ _ _ => Out.le_trans (h1.whileLoop _ _ _ _) (h2.whileLoop _ _ _ _)⟩

theorem fuelLvl_le (r : Lvl) : fuelLvl.le r :=
  ⟨fun _ _ _ => Or.inl rfl, fun _ _ _ _ _ _ => Or.inl rfl, fun _ _ _ _ => Or.inl rfl⟩

theorem interp_succ_le (c : Ctx) : ∀ k, (interp c k).le (interp c (k + 1))
  | 0 => fuelLvl_le _
  | k + 1 => mkLevel_mono (interp_succ_le c k)

/-- **Fuel monotonicity.** -/
theorem interp_mono (c : Ctx) {k k' : Nat} (h : k ≤ k') : (interp c k).le (interp c k') := by
  induction h with
  | refl => exact Lvl.le_refl _
  | step _ ih => exact Lvl.le_trans ih (interp_succ_le c _)

/-- A non-`fuel` outcome is stable under more fuel. -/
theorem run_stable (c : Ctx) {k k' : Nat} (hk : k ≤ k') (f : String) (args : List V) (h : Heap)
    (hne : run c k f args h ≠ .fuel) : run c k' f args h = run c k f args h := by
  rcases (interp_mono c hk).call f args h with h1 | h1
  · exact absurd h1 hne
  · exact h1.symm

/-- `Eventually x r`: for all sufficiently large fuel the run gives exactly `r`. -/
def Eventually {α : Type} (x : Nat → Out α) (r : Out α) : Prop := ∃ N, ∀ k, N ≤ k → x k = r

/-- If a run eventually gives `r ≠ fuel`, then with **every** fuel it gives either `fuel` or
exactly `r`: resource exhaustion is the only alternative outcome. -/
theorem run_fuel_or (c : Ctx) {f : String} {args : List V} {h : Heap} {r : Out V}
    (he : Eventually (fun k => run c k f args h) r) (k : Nat) :
    run c k f args h = .fuel ∨ run c k f args h = r := by
  obtain ⟨N, hN⟩ := he
  rcases (interp_mono c (Nat.le_max_left k N)).call f args h with h1 | h1
  · exact Or.inl h1
  · right; rw [show (interp c k).call f args h = run c k f args h from rfl] at h1
    rw [h1]; exact hN _ (Nat.le_max_right _ _)

end PCSCR
