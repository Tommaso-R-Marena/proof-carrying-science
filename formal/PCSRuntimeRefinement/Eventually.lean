import PCSRuntimeRefinement.Core

/-!
# Fuel-free reasoning about the interpreter

`EvE d env e r` — for **all sufficiently large fuel**, evaluating `e` yields `r`.  The
compositional rules below let correspondence proofs reason about programs without tracking
fuel; any `EvE … r` fact gives an explicit fuel threshold beyond which the executable
interpreter returns exactly `r` (in particular, never the `fuel` outcome).
-/

namespace PCSRuntimeRefinement

variable {d : Dialect}

def EvE (d : Dialect) (env : Env) (e : E) (r : Res Val) : Prop := ∃ N, ∀ n, N ≤ n → evalE d n env e = r
def EvL (d : Dialect) (env : Env) (es : List E) (r : Res (List Val)) : Prop :=
  ∃ N, ∀ n, N ≤ n → evalL d n env es = r
def EvC (d : Dialect) (env : Env) (elt : E) (p : Pat) (f : Option E) (xs : List Val) (r : Res (List Val)) :
    Prop := ∃ N, ∀ n, N ≤ n → evalComp d n env elt p f xs = r
def ExS (d : Dialect) (env : Env) (s : S) (r : Res Flow) : Prop := ∃ N, ∀ n, N ≤ n → execS d n env s = r
def ExB (d : Dialect) (env : Env) (ss : List S) (r : Res Flow) : Prop :=
  ∃ N, ∀ n, N ≤ n → execB d n env ss = r
def ExF (d : Dialect) (env : Env) (p : Pat) (body : List S) (xs : List Val) (r : Res Flow) : Prop :=
  ∃ N, ∀ n, N ≤ n → execFor d n env p body xs = r

private theorem succ_of_ge {n N : Nat} (h : N + 1 ≤ n) : ∃ m, n = m + 1 ∧ N ≤ m := ⟨n - 1, by omega, by omega⟩

/-! ## Expressions -/

theorem EvE.var {env : Env} {x : String} {v : Val} (h : env.get x = some v) : EvE d env (.var x) (.ok v) :=
  ⟨1, fun n hn => by obtain ⟨m, rfl, -⟩ := succ_of_ge hn; simp [evalE, h]⟩

theorem EvE.lit {env : Env} (v : Val) : EvE d env (.lit v) (.ok v) :=
  ⟨1, fun n hn => by obtain ⟨m, rfl, -⟩ := succ_of_ge hn; simp [evalE]⟩

theorem EvE.list {env : Env} {es : List E} {vs : List Val} (h : EvL d env es (.ok vs)) :
    EvE d env (.list es) (.ok (.list vs)) := by
  obtain ⟨N, h⟩ := h
  exact ⟨N + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h m hm]⟩

theorem EvE.tuple {env : Env} {es : List E} {vs : List Val} (h : EvL d env es (.ok vs)) :
    EvE d env (.tuple es) (.ok (.tuple vs)) := by
  obtain ⟨N, h⟩ := h
  exact ⟨N + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h m hm]⟩

theorem EvE.index {env : Env} {a i : E} {va vi : Val} (ha : EvE d env a (.ok va)) (hi : EvE d env i (.ok vi)) :
    EvE d env (.index a i) (indexOp d va vi) := by
  obtain ⟨N1, h1⟩ := ha; obtain ⟨N2, h2⟩ := hi
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m (by omega), h2 m (by omega)]⟩

theorem EvE.field {env : Env} {a : E} {k : String} {va : Val} (ha : EvE d env a (.ok va)) :
    EvE d env (.field a k) (fieldOp d va k) := by
  obtain ⟨N1, h1⟩ := ha
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m hm]⟩

theorem EvE.sliceFrom {env : Env} {a i : E} {va vi : Val} (ha : EvE d env a (.ok va))
    (hi : EvE d env i (.ok vi)) : EvE d env (.sliceFrom a i) (sliceOp va vi) := by
  obtain ⟨N1, h1⟩ := ha; obtain ⟨N2, h2⟩ := hi
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m (by omega), h2 m (by omega)]⟩

theorem EvE.bin {env : Env} {op : Op} {a b : E} {va vb : Val} (ha : EvE d env a (.ok va))
    (hb : EvE d env b (.ok vb)) : EvE d env (.bin op a b) (binOp d op va vb) := by
  obtain ⟨N1, h1⟩ := ha; obtain ⟨N2, h2⟩ := hb
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m (by omega), h2 m (by omega)]⟩

theorem EvE.not {env : Env} {a : E} {va : Val} (ha : EvE d env a (.ok va)) :
    EvE d env (.not a) (.ok (.bool !(truthy d va))) := by
  obtain ⟨N1, h1⟩ := ha
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m hm]⟩

theorem EvE.and_t {env : Env} {a b : E} {va : Val} {r : Res Val} (ha : EvE d env a (.ok va))
    (ht : truthy d va = true) (hb : EvE d env b r) : EvE d env (.and a b) r := by
  obtain ⟨N1, h1⟩ := ha; obtain ⟨N2, h2⟩ := hb
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m (by omega), h2 m (by omega), ht]⟩

theorem EvE.and_f {env : Env} {a b : E} {va : Val} (ha : EvE d env a (.ok va))
    (ht : truthy d va = false) : EvE d env (.and a b) (.ok va) := by
  obtain ⟨N1, h1⟩ := ha
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m hm, ht]⟩

theorem EvE.cond {env : Env} {c t f : E} {vc : Val} {r : Res Val} (hc : EvE d env c (.ok vc))
    (hb : EvE d env (if truthy d vc then t else f) r) : EvE d env (.cond c t f) r := by
  obtain ⟨N1, h1⟩ := hc; obtain ⟨N2, h2⟩ := hb
  refine ⟨max N1 N2 + 1, fun n hn => ?_⟩
  obtain ⟨m, rfl, hm⟩ := succ_of_ge hn
  have := h2 m (by omega)
  cases ht : truthy d vc <;> simp_all [evalE, h1 m (by omega)]

theorem EvE.isNone {env : Env} {a : E} {va : Val} (ha : EvE d env a (.ok va)) :
    EvE d env (.isNone a) (.ok (.bool (isNoneV va))) := by
  obtain ⟨N1, h1⟩ := ha
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m hm]⟩

theorem EvE.mem {env : Env} {x xs : E} {vx vs : Val} {b : Bool} (hx : EvE d env x (.ok vx))
    (hs : EvE d env xs (.ok vs)) (hm : memOp d vx vs = .ok b) : EvE d env (.mem x xs) (.ok (.bool b)) := by
  obtain ⟨N1, h1⟩ := hx; obtain ⟨N2, h2⟩ := hs
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm'⟩ := succ_of_ge hn; simp [evalE, h1 m (by omega), h2 m (by omega), hm]⟩

theorem EvE.copy {env : Env} {a : E} {va : Val} {xs : List Val} (ha : EvE d env a (.ok va))
    (hi : iterOf d va = .ok xs) : EvE d env (.copy a) (.ok (.list xs)) := by
  obtain ⟨N1, h1⟩ := ha
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m hm, hi]⟩

theorem EvE.min {env : Env} {a : E} {va : Val} {xs : List Val} (ha : EvE d env a (.ok va))
    (hi : iterOf d va = .ok xs) : EvE d env (.min a) (minOp d xs) := by
  obtain ⟨N1, h1⟩ := ha
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m hm, hi]⟩

theorem EvE.comp {env : Env} {elt it : E} {p : Pat} {f : Option E} {vi : Val} {xs vs : List Val}
    (hit : EvE d env it (.ok vi)) (hi : iterOf d vi = .ok xs) (hc : EvC d env elt p f xs (.ok vs)) :
    EvE d env (.comp elt p it f) (.ok (.list vs)) := by
  obtain ⟨N1, h1⟩ := hit; obtain ⟨N2, h2⟩ := hc
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m (by omega), hi, h2 m (by omega)]⟩

theorem EvE.objLit {env : Env} {ks : List String} {es : List E} {vs : List Val}
    (h : EvL d env es (.ok vs)) : EvE d env (.objLit ks es) (.ok (.obj (ks.zip vs))) := by
  obtain ⟨N1, h1⟩ := h
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalE, h1 m hm]⟩

theorem EvL.nil {env : Env} : EvL d env [] (.ok []) :=
  ⟨1, fun n hn => by obtain ⟨m, rfl, -⟩ := succ_of_ge hn; simp [evalL]⟩

theorem EvL.cons {env : Env} {e : E} {es : List E} {v : Val} {vs : List Val} (h1 : EvE d env e (.ok v))
    (h2 : EvL d env es (.ok vs)) : EvL d env (e :: es) (.ok (v :: vs)) := by
  obtain ⟨N1, h1⟩ := h1; obtain ⟨N2, h2⟩ := h2
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalL, h1 m (by omega), h2 m (by omega)]⟩

theorem EvC.nil {env : Env} {elt : E} {p : Pat} {f : Option E} : EvC d env elt p f [] (.ok []) :=
  ⟨1, fun n hn => by obtain ⟨m, rfl, -⟩ := succ_of_ge hn; simp [evalComp]⟩

theorem EvC.cons_none {env env' : Env} {elt : E} {p : Pat} {x : Val} {xs : List Val} {v : Val}
    {vs : List Val} (hb : bindPat d p x env = .ok env') (he : EvE d env' elt (.ok v))
    (hr : EvC d env elt p none xs (.ok vs)) : EvC d env elt p none (x :: xs) (.ok (v :: vs)) := by
  obtain ⟨N1, h1⟩ := he; obtain ⟨N2, h2⟩ := hr
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [evalComp, hb, h1 m (by omega), h2 m (by omega)]⟩

theorem EvC.cons_keep {env env' : Env} {elt c : E} {p : Pat} {x : Val} {xs : List Val} {vc v : Val}
    {vs : List Val} (hb : bindPat d p x env = .ok env') (hc : EvE d env' c (.ok vc))
    (ht : truthy d vc = true) (he : EvE d env' elt (.ok v))
    (hr : EvC d env elt p (some c) xs (.ok vs)) : EvC d env elt p (some c) (x :: xs) (.ok (v :: vs)) := by
  obtain ⟨N0, h0⟩ := hc; obtain ⟨N1, h1⟩ := he; obtain ⟨N2, h2⟩ := hr
  exact ⟨max N0 (max N1 N2) + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn
    simp [evalComp, hb, h0 m (by omega), ht, h1 m (by omega), h2 m (by omega)]⟩

theorem EvC.cons_drop {env env' : Env} {elt c : E} {p : Pat} {x : Val} {xs : List Val} {vc : Val}
    {vs : List Val} (hb : bindPat d p x env = .ok env') (hc : EvE d env' c (.ok vc))
    (ht : truthy d vc = false) (hr : EvC d env elt p (some c) xs (.ok vs)) :
    EvC d env elt p (some c) (x :: xs) (.ok vs) := by
  obtain ⟨N0, h0⟩ := hc; obtain ⟨N2, h2⟩ := hr
  exact ⟨max N0 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn
    simp [evalComp, hb, h0 m (by omega), ht, h2 m (by omega)]⟩

/-! ## Statements -/

theorem ExS.assign {env env' : Env} {p : Pat} {e : E} {v : Val} (he : EvE d env e (.ok v))
    (hb : bindPat d p v env = .ok env') : ExS d env (.assign p e) (.ok (.normal env')) := by
  obtain ⟨N1, h1⟩ := he
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execS, h1 m hm, hb]⟩

theorem ExS.augIndex {env : Env} {x : String} {i e : E} {op : Op} {vx vi old ve nv vx' : Val}
    (hx : env.get x = some vx) (hi : EvE d env i (.ok vi)) (ho : indexOp d vx vi = .ok old)
    (he : EvE d env e (.ok ve)) (hop : binOp d op old ve = .ok nv) (hs : storeOp d vx vi nv = .ok vx') :
    ExS d env (.augIndex x i op e) (.ok (.normal (env.set x vx'))) := by
  obtain ⟨N1, h1⟩ := hi; obtain ⟨N2, h2⟩ := he
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn
    simp [execS, hx, h1 m (by omega), ho, h2 m (by omega), hop, hs]⟩

theorem ExS.append {env : Env} {x : String} {e : E} {xs : List Val} {v : Val}
    (hx : env.get x = some (.list xs)) (he : EvE d env e (.ok v)) :
    ExS d env (.append x e) (.ok (.normal (env.set x (.list (xs ++ [v]))))) := by
  obtain ⟨N1, h1⟩ := he
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execS, hx, h1 m hm]⟩

theorem ExS.forIn {env : Env} {p : Pat} {it : E} {body : List S} {vi : Val} {xs : List Val}
    {r : Res Flow} (hit : EvE d env it (.ok vi)) (hi : iterOf d vi = .ok xs)
    (hf : ExF d env p body xs r) : ExS d env (.forIn p it body) r := by
  obtain ⟨N1, h1⟩ := hit; obtain ⟨N2, h2⟩ := hf
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execS, h1 m (by omega), hi, h2 m (by omega)]⟩

theorem ExS.if_false {env : Env} {c : E} {body : List S} {vc : Val} (hc : EvE d env c (.ok vc))
    (ht : truthy d vc = false) : ExS d env (.ifThen c body) (.ok (.normal env)) := by
  obtain ⟨N1, h1⟩ := hc
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execS, h1 m hm, ht]⟩

theorem ExS.if_cont {env env' : Env} {c : E} {body : List S} {vc : Val} (hc : EvE d env c (.ok vc))
    (ht : truthy d vc = true) (hb : ExB d env body (.ok (.cont env'))) :
    ExS d env (.ifThen c body) (.ok (.cont (exitBlock d env env'))) := by
  obtain ⟨N1, h1⟩ := hc; obtain ⟨N2, h2⟩ := hb
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execS, h1 m (by omega), ht, h2 m (by omega)]⟩

theorem ExS.cont {env : Env} : ExS d env .cont (.ok (.cont env)) :=
  ⟨1, fun n hn => by obtain ⟨m, rfl, -⟩ := succ_of_ge hn; simp [execS]⟩

theorem ExS.ret {env : Env} {e : E} {v : Val} (he : EvE d env e (.ok v)) : ExS d env (.ret e) (.ok (.ret v)) := by
  obtain ⟨N1, h1⟩ := he
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execS, h1 m hm]⟩

theorem ExB.nil {env : Env} : ExB d env [] (.ok (.normal env)) :=
  ⟨1, fun n hn => by obtain ⟨m, rfl, -⟩ := succ_of_ge hn; simp [execB]⟩

theorem ExB.cons_normal {env env' : Env} {s : S} {ss : List S} {r : Res Flow}
    (h1 : ExS d env s (.ok (.normal env'))) (h2 : ExB d env' ss r) : ExB d env (s :: ss) r := by
  obtain ⟨N1, h1⟩ := h1; obtain ⟨N2, h2⟩ := h2
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execB, h1 m (by omega), h2 m (by omega)]⟩

theorem ExB.cons_cont {env env' : Env} {s : S} {ss : List S}
    (h1 : ExS d env s (.ok (.cont env'))) : ExB d env (s :: ss) (.ok (.cont env')) := by
  obtain ⟨N1, h1⟩ := h1
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execB, h1 m hm]⟩

theorem ExB.cons_ret {env : Env} {s : S} {ss : List S} {v : Val}
    (h1 : ExS d env s (.ok (.ret v))) : ExB d env (s :: ss) (.ok (.ret v)) := by
  obtain ⟨N1, h1⟩ := h1
  exact ⟨N1 + 1, fun n hn => by obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execB, h1 m hm]⟩

theorem ExF.nil {env : Env} {p : Pat} {body : List S} : ExF d env p body [] (.ok (.normal env)) :=
  ⟨1, fun n hn => by obtain ⟨m, rfl, -⟩ := succ_of_ge hn; simp [execFor]⟩

theorem ExF.cons_normal {env env1 env' : Env} {p : Pat} {body : List S} {x : Val} {xs : List Val}
    {r : Res Flow} (hb : bindPat d p x env = .ok env1) (h1 : ExB d env1 body (.ok (.normal env')))
    (h2 : ExF d (exitBlock d env env') p body xs r) : ExF d env p body (x :: xs) r := by
  obtain ⟨N1, h1⟩ := h1; obtain ⟨N2, h2⟩ := h2
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execFor, hb, h1 m (by omega), h2 m (by omega)]⟩

theorem ExF.cons_cont {env env1 env' : Env} {p : Pat} {body : List S} {x : Val} {xs : List Val}
    {r : Res Flow} (hb : bindPat d p x env = .ok env1) (h1 : ExB d env1 body (.ok (.cont env')))
    (h2 : ExF d (exitBlock d env env') p body xs r) : ExF d env p body (x :: xs) r := by
  obtain ⟨N1, h1⟩ := h1; obtain ⟨N2, h2⟩ := h2
  exact ⟨max N1 N2 + 1, fun n hn => by
    obtain ⟨m, rfl, hm⟩ := succ_of_ge hn; simp [execFor, hb, h1 m (by omega), h2 m (by omega)]⟩

/-- A function call from an `ExB` fact about its body. -/
theorem callFn_of_ExB {f : Fn} {args : List Val} {v : Val} (hl : f.params.length = args.length)
    (h : ExB d ((f.params.zip args).reverse) f.body (.ok (.ret v))) :
    ∃ N, ∀ n, N ≤ n → callFn d n f args = .ok v := by
  obtain ⟨N, h⟩ := h
  exact ⟨N, fun n hn => by simp [callFn, hl, h n hn]⟩

/-! ## Environments -/

theorem Env.get_replace_self (env : Env) (x : String) (v : Val) (h : env.has x = true) :
    (env.replace x v).get x = some v := by
  induction env with
  | nil => simp [Env.has] at h
  | cons q qs ih =>
      obtain ⟨k, w⟩ := q
      by_cases hk : k = x
      · simp [Env.replace, Env.get, hk]
      · simp only [Env.has, Bool.or_eq_true, beq_iff_eq, hk, false_or] at h
        simp [Env.replace, Env.get, hk, ih h]

theorem Env.get_replace_ne (env : Env) {x y : String} (v : Val) (h : y ≠ x) :
    (env.replace x v).get y = env.get y := by
  induction env with
  | nil => rfl
  | cons q qs ih =>
      obtain ⟨k, w⟩ := q
      by_cases hk : k = x
      · subst hk
        have : ¬ k = y := fun e => h e.symm
        simp [Env.replace, Env.get, this, ih]
      · by_cases hky : k = y
        · subst hky; simp [Env.replace, Env.get, hk]
        · simp [Env.replace, Env.get, hk, hky, ih]

@[simp] theorem Env.get_set_self (env : Env) (x : String) (v : Val) : (env.set x v).get x = some v := by
  unfold Env.set
  split
  · rename_i h; exact Env.get_replace_self env x v h
  · simp [Env.get]

theorem Env.get_set_ne (env : Env) {x y : String} (v : Val) (h : y ≠ x) :
    (env.set x v).get y = env.get y := by
  unfold Env.set
  split
  · exact Env.get_replace_ne env v h
  · have : ¬ x = y := fun e => h e.symm
    simp [Env.get, this]

theorem Env.any_key_eq_has (outer : Env) (y : String) : outer.any (fun q => q.1 == y) = outer.has y := by
  induction outer with
  | nil => rfl
  | cons q qs ih => simp [List.any_cons, Env.has, ih]

/-- JS block exit keeps exactly the bindings that existed before the block, with their updated
values. -/
theorem Env.get_exit_js (outer env : Env) (y : String) :
    (exitBlock .js outer env).get y = if outer.has y then env.get y else none := by
  simp only [exitBlock, List.reverse_reverse, Env.restrict]
  induction env with
  | nil => simp [Env.get]
  | cons q qs ih =>
      obtain ⟨k, w⟩ := q
      simp only [List.filter_cons]
      by_cases hk : k = y
      · subst hk
        rw [Env.any_key_eq_has]
        cases hh : outer.has k <;> simp [Env.get, hh] at ih ⊢
        exact ih
      · split <;> simp [Env.get, hk, ih]

theorem Env.has_of_get {env : Env} {y : String} {v : Val} (h : env.get y = some v) : env.has y = true := by
  induction env with
  | nil => simp [Env.get] at h
  | cons q qs ih =>
      obtain ⟨k, w⟩ := q
      by_cases hk : k = y
      · simp [Env.has, hk]
      · simp only [Env.get, hk, if_false] at h
        simp [Env.has, ih h]

end PCSRuntimeRefinement
