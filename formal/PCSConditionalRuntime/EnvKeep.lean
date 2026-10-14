import PCSConditionalRuntime.PyConj

/-!
# Local-store frame rule

A statement list that never binds the name `y` (no assignment, augmented assignment, loop
target or `except … as` name equal to `y`, at any nesting depth) leaves `y` unchanged in every
outcome that carries a local store: normal completion, `break`, and raised exceptions.  This
holds for every interpreter level (calls run in their own stores; loop back-edges are covered
by induction on the level).
-/

namespace PCSCR

mutual
def bindsT : Tgt → List String
  | .name x => [x]
  | .attr _ _ => []
  | .sub _ _ => []
  | .tup ts => bindsTs ts
def bindsTs : List Tgt → List String
  | [] => []
  | t :: ts => bindsT t ++ bindsTs ts
end

mutual
def bindsS : S → List String
  | .assign ts _ => bindsTs ts
  | .aug t _ _ => bindsT t
  | .ifte _ t f => bindsB t ++ bindsB f
  | .forIn t _ b => bindsT t ++ bindsB b
  | .while _ b => bindsB b
  | .try b _ x hd => bindsB b ++ x :: bindsB hd
  | .expr _ => []
  | .ret _ => []
  | .brk => []
  | .raise _ => []
  | .assert _ => []
  | .pass => []
def bindsB : List S → List String
  | [] => []
  | s :: ss => bindsS s ++ bindsB ss
end

/-- The outcome keeps the value of `y` of the store `env`. -/
def FK (y : String) (env : Env) : Out Flow → Prop
  | .ok (.normal e) _ => e.get y = env.get y
  | .ok (.brk e) _ => e.get y = env.get y
  | .ok (.raise _ e) _ => e.get y = env.get y
  | _ => True

theorem FK.trans {y : String} {env env' : Env} {o : Out Flow} (h : FK y env' o) (e : env'.get y = env.get y) :
    FK y env o := by
  rcases o with ⟨fl, h'⟩ | _ | _
  · cases fl <;> simp only [FK] at h ⊢ <;> (try rw [h, e]) <;> trivial
  · trivial
  · trivial

mutual
theorem assignT_keeps (c : Ctx) (r : Lvl) (y : String) :
    ∀ (t : Tgt) (env : Env) (h : Heap) (v : V) (env' : Env) (h' : Heap), y ∉ bindsT t →
      assignT c r env h v t = .ok env' h' → env'.get y = env.get y
  | .name x, env, h, v, env', h', hy, e => by
    simp only [bindsT, List.mem_singleton] at hy
    simp only [assignT, Out.ok.injEq] at e
    obtain ⟨rfl, rfl⟩ := e
    simp [Env.get_set, Ne.symm hy]
  | .attr o f, env, h, v, env', h', _, e => by
    simp only [assignT] at e
    cases h1 : evalE c r env h o with
    | ok vo h1' =>
      rw [h1] at e; simp only [Out.bind] at e
      cases h2 : setAttrOp h1' vo f v with
      | ok u h2' => rw [h2] at e; simp only [Out.ok.injEq] at e; rw [← e.1]
      | exc _ _ => rw [h2] at e; simp at e
      | fuel => rw [h2] at e; simp at e
    | exc _ _ => rw [h1] at e; simp at e
    | fuel => rw [h1] at e; simp at e
  | .sub o i, env, h, v, env', h', _, e => by
    simp only [assignT] at e
    cases h1 : evalE c r env h o with
    | ok vo h1' =>
      rw [h1] at e; simp only [Out.bind] at e
      cases h2 : evalE c r env h1' i with
      | ok vi h2' =>
        rw [h2] at e; dsimp only [Out.bind] at e
        cases h3 : storeOp c.dialect h2' vo vi v with
        | ok u h3' => rw [h3] at e; simp only [Out.ok.injEq] at e; rw [← e.1]
        | exc _ _ => rw [h3] at e; simp at e
        | fuel => rw [h3] at e; simp at e
      | exc _ _ => rw [h2] at e; simp at e
      | fuel => rw [h2] at e; simp at e
    | exc _ _ => rw [h1] at e; simp at e
    | fuel => rw [h1] at e; simp at e
  | .tup ts, env, h, v, env', h', hy, e => by
    simp only [bindsT] at hy
    simp only [assignT] at e
    split at e
    · split at e
      · exact assignTs_keeps c r y ts env h _ env' h' hy e
      · simp [err] at e
    · simp at e
theorem assignTs_keeps (c : Ctx) (r : Lvl) (y : String) :
    ∀ (ts : List Tgt) (env : Env) (h : Heap) (vs : List V) (env' : Env) (h' : Heap), y ∉ bindsTs ts →
      assignTs c r env h vs ts = .ok env' h' → env'.get y = env.get y
  | [], env, h, vs, env', h', _, e => by
    cases vs <;> (simp only [assignTs, Out.ok.injEq] at e; rw [← e.1])
  | t :: ts, env, h, [], env', h', _, e => by
    simp only [assignTs, Out.ok.injEq] at e; rw [← e.1]
  | t :: ts, env, h, v :: vs, env', h', hy, e => by
    simp only [bindsTs, List.mem_append, not_or] at hy
    simp only [assignTs] at e
    cases h1 : assignT c r env h v t with
    | ok env1 h1' =>
      rw [h1] at e; simp only [Out.bind] at e
      rw [assignTs_keeps c r y ts env1 h1' vs env' h' hy.2 e, assignT_keeps c r y t env h v env1 h1' hy.1 h1]
    | exc _ _ => rw [h1] at e; simp at e
    | fuel => rw [h1] at e; simp at e
end

theorem assignAll_keeps (c : Ctx) (r : Lvl) (y : String) :
    ∀ (ts : List Tgt) (env : Env) (h : Heap) (v : V) (env' : Env) (h' : Heap), y ∉ bindsTs ts →
      assignAll c r env h v ts = .ok env' h' → env'.get y = env.get y
  | [], env, h, v, env', h', _, e => by simp only [assignAll, Out.ok.injEq] at e; rw [← e.1]
  | t :: ts, env, h, v, env', h', hy, e => by
    simp only [bindsTs, List.mem_append, not_or] at hy
    simp only [assignAll] at e
    cases h1 : assignT c r env h v t with
    | ok env1 h1' =>
      rw [h1] at e; simp only [Out.bind] at e
      rw [assignAll_keeps c r y ts env1 h1' v env' h' hy.2 e, assignT_keeps c r y t env h v env1 h1' hy.1 h1]
    | exc _ _ => rw [h1] at e; simp at e
    | fuel => rw [h1] at e; simp at e

/-- The loop back-edges of a level keep `y`. -/
def LvlK (y : String) (r : Lvl) : Prop :=
  (∀ env h t v k body, y ∉ bindsT t → y ∉ bindsB body → FK y env (r.forLoop env h t v k body)) ∧
  (∀ env h e body, y ∉ bindsB body → FK y env (r.whileLoop env h e body))

theorem FK_bindS {y : String} {env : Env} (x : Out V) (k : V → Heap → Out Flow)
    (hk : ∀ v h, FK y env (k v h)) : FK y env (bindS env x k) := by
  rcases x with ⟨v, h⟩ | ⟨e, h⟩ | _
  · exact hk v h
  · simp [bindS, FK]
  · simp [bindS, FK]

theorem Env.get_erase (env : Env) (x y : String) (hxy : x ≠ y) : (env.erase x).get y = env.get y := by
  induction env with
  | nil => rfl
  | cons p rest ih =>
    obtain ⟨k, w⟩ := p
    simp only [Env.erase]
    by_cases hk : k = x
    · subst hk; simp [Env.get, hxy, ih]
    · simp [Env.get, hk, ih]

mutual
theorem execS_keeps (c : Ctx) (r : Lvl) (y : String) (hr : LvlK y r) :
    ∀ (s : S) (env : Env) (h : Heap), y ∉ bindsS s → FK y env (execS c r env h s)
  | .assign ts e, env, h, hy => by
    simp only [bindsS] at hy
    simp only [execS]
    refine FK_bindS _ _ (fun v h1 => ?_)
    cases h2 : assignAll c r env h1 v ts with
    | ok env' h' => simp only [bindE, FK]; exact assignAll_keeps c r y ts env h1 v env' h' hy h2
    | exc _ _ => simp [bindE, FK]
    | fuel => simp [bindE, FK]
  | .aug t op e, env, h, hy => by
    simp only [bindsS] at hy
    cases t with
    | name x =>
      simp only [bindsT, List.mem_singleton] at hy
      simp only [execS]
      cases hx : env.get x with
      | none => simp [FK]
      | some old =>
        refine FK_bindS _ _ (fun v h1 => FK_bindS _ _ (fun nv h2 => ?_))
        simp [FK, Env.get_set, Ne.symm hy]
    | attr o f =>
      simp only [execS]
      refine FK_bindS _ _ (fun _ _ => FK_bindS _ _ (fun _ _ => FK_bindS _ _ (fun _ _ =>
        FK_bindS _ _ (fun _ _ => FK_bindS _ _ (fun _ _ => ?_)))))
      simp [FK]
    | sub _ _ => simp [execS, FK]
    | tup _ => simp [execS, FK]
  | .expr e, env, h, _ => by
    simp only [execS]; exact FK_bindS _ _ (fun _ _ => by simp [FK])
  | .ifte e t f, env, h, hy => by
    simp only [bindsS, List.mem_append, not_or] at hy
    simp only [execS]
    refine FK_bindS _ _ (fun v h1 => ?_)
    split
    · exact execB_keeps c r y hr t env h1 hy.1
    · exact execB_keeps c r y hr f env h1 hy.2
  | .forIn t it body, env, h, hy => by
    simp only [bindsS, List.mem_append, not_or] at hy
    simp only [execS]
    exact FK_bindS _ _ (fun v h1 => hr.1 env h1 t v 0 body hy.1 hy.2)
  | .while e body, env, h, hy => by
    simp only [bindsS] at hy
    simp only [execS]
    exact hr.2 env h e body hy
  | .ret e, env, h, _ => by
    simp only [execS]; exact FK_bindS _ _ (fun _ _ => by simp [FK])
  | .brk, env, h, _ => by simp [execS, FK]
  | .raise e, env, h, _ => by
    simp only [execS]; exact FK_bindS _ _ (fun _ _ => by simp [FK])
  | .try body cls x handler, env, h, hy => by
    simp only [bindsS, List.mem_append, List.mem_cons, not_or] at hy
    simp only [execS]
    have hb := execB_keeps c r y hr body env h hy.1
    generalize execB c r env h body = o at hb
    rcases o with ⟨fl, h1⟩ | _ | _
    · cases fl with
      | raise ex env' =>
        simp only [FK] at hb
        simp only [onRaise]
        split
        · have hh := execB_keeps c r y hr handler (env'.set x (excVal ex)) h1 hy.2.2
          generalize execB c r (env'.set x (excVal ex)) h1 handler = o2 at hh
          rcases o2 with ⟨fl2, h2⟩ | _ | _
          · cases fl2 with
            | normal e2 =>
              simp only [eraseAfter, FK] at hh ⊢
              rw [Env.get_erase _ _ _ (Ne.symm hy.2.1), hh, Env.get_set]; simp [Ne.symm hy.2.1, hb]
            | brk e2 =>
              simp only [eraseAfter, FK] at hh ⊢
              rw [hh, Env.get_set]; simp [Ne.symm hy.2.1, hb]
            | raise ex2 e2 =>
              simp only [eraseAfter, FK] at hh ⊢
              rw [hh, Env.get_set]; simp [Ne.symm hy.2.1, hb]
            | ret _ => simp [eraseAfter, FK]
          · simp [eraseAfter, FK]
          · simp [eraseAfter, FK]
        · simp [FK, hb]
      | normal e => simpa [onRaise, FK] using hb
      | brk e => simpa [onRaise, FK] using hb
      | ret v => simp [onRaise, FK]
    · simp [onRaise, FK]
    · simp [onRaise, FK]
  | .assert e, env, h, _ => by
    simp only [execS]; exact FK_bindS _ _ (fun _ _ => by split <;> simp [FK])
  | .pass, env, h, _ => by simp [execS, FK]
theorem execB_keeps (c : Ctx) (r : Lvl) (y : String) (hr : LvlK y r) :
    ∀ (ss : List S) (env : Env) (h : Heap), y ∉ bindsB ss → FK y env (execB c r env h ss)
  | [], env, h, _ => by simp [execB, FK]
  | s :: ss, env, h, hy => by
    simp only [bindsB, List.mem_append, not_or] at hy
    simp only [execB]
    have hs := execS_keeps c r y hr s env h hy.1
    generalize execS c r env h s = o at hs
    rcases o with ⟨fl, h1⟩ | _ | _
    · cases fl with
      | normal e =>
        simp only [seqF]
        exact (execB_keeps c r y hr ss e h1 hy.2).trans hs
      | brk e => simpa [seqF, FK] using hs
      | raise ex e => simpa [seqF, FK] using hs
      | ret v => simp [seqF, FK]
    · simp [seqF, FK]
    · simp [seqF, FK]
end

theorem FK_loopK {y : String} {env : Env} (x : Out Flow) (k : Env → Heap → Out Flow) (hx : FK y env x)
    (hk : ∀ e h, e.get y = env.get y → FK y env (k e h)) : FK y env (loopK x k) := by
  rcases x with ⟨fl, h1⟩ | _ | _
  · cases fl with
    | normal e => exact hk e h1 hx
    | brk e => simpa [loopK, FK] using hx
    | raise ex e => simpa [loopK, FK] using hx
    | ret v => simp [loopK, FK]
  · simp [loopK, FK]
  · simp [loopK, FK]

theorem interp_keeps (c : Ctx) (y : String) : ∀ k, LvlK y (interp c k)
  | 0 => ⟨fun _ _ _ _ _ _ _ _ => by simp [interp, fuelLvl, FK], fun _ _ _ _ _ => by simp [interp, fuelLvl, FK]⟩
  | k + 1 => by
    have ih := interp_keeps c y k
    refine ⟨fun env h t v j body ht hb => ?_, fun env h e body hb => ?_⟩
    · simp only [interp, mkLevel, forIter]
      split
      · simp [FK]
      · simp [FK]
      · rename_i x _
        cases h1 : assignT c (interp c k) env h x t with
        | ok env1 h1' =>
          simp only [bindE]
          have e1 := assignT_keeps c (interp c k) y t env h x env1 h1' ht h1
          refine FK_loopK _ _ ((execB_keeps c _ y ih body env1 h1' hb).trans e1) (fun e2 h2 he => ?_)
          exact (ih.1 e2 h2 t v (j + 1) body ht hb).trans he
        | exc _ _ => simp [bindE, FK]
        | fuel => simp [bindE, FK]
    · simp only [interp, mkLevel, whileIter]
      refine FK_bindS _ _ (fun vc h1 => ?_)
      split
      · exact FK_loopK _ _ (execB_keeps c _ y ih body env h1 hb) (fun e2 h2 he => (ih.2 e2 h2 e body hb).trans he)
      · simp [FK]

/-- **Frame rule for local stores.** -/
theorem execB_keeps_interp (c : Ctx) (k : Nat) (y : String) (ss : List S) (env : Env) (h : Heap)
    (hy : y ∉ bindsB ss) : FK y env (execB c (interp c k) env h ss) :=
  execB_keeps c _ y (interp_keeps c y k) ss env h hy

end PCSCR
