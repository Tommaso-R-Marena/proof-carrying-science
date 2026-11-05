import PCSConditionalRuntime.PyFront

/-!
# Sound Boolean equality on extracted core programs

The core syntax (`E`, `Tgt`, `S`) is a nested inductive family, for which `DecidableEq` cannot
be derived.  `Module.beq` is a structural Boolean comparison with a soundness theorem
(`Module.beq_sound`), so that extraction certificates of the form
`lower segs = some M` can be checked by kernel evaluation (`decide +kernel` on
`Module.beqO (lower segs) (some M) = true`) instead of by elaborator unfolding.
-/

namespace PCSCR

mutual
def E.beq : E → E → Bool
  | .var x, .var y => x == y
  | .lit v, .lit w => decide (v = w)
  | .tup a, .tup b => E.beqL a b
  | .listD a, .listD b => E.beqL a b
  | .dictD a, .dictD b => E.beqL a b
  | .setD a, .setD b => E.beqL a b
  | .attr e f, .attr e' f' => E.beq e e' && f == f'
  | .sub e i, .sub e' i' => E.beq e e' && E.beq i i'
  | .sliceFrom e i, .sliceFrom e' i' => E.beq e e' && E.beq i i'
  | .bin op a b, .bin op' a' b' => decide (op = op') && E.beq a a' && E.beq b b'
  | .cmp2 o1 o2 a b c, .cmp2 o1' o2' a' b' c' =>
      decide (o1 = o1') && decide (o2 = o2') && E.beq a a' && E.beq b b' && E.beq c c'
  | .not a, .not a' => E.beq a a'
  | .and a b, .and a' b' => E.beq a a' && E.beq b b'
  | .or a b, .or a' b' => E.beq a a' && E.beq b b'
  | .cond c t f, .cond c' t' f' => E.beq c c' && E.beq t t' && E.beq f f'
  | .isNone a n, .isNone a' n' => E.beq a a' && n == n'
  | .typeIs a ty n, .typeIs a' ty' n' => E.beq a a' && ty == ty' && n == n'
  | .mem x c n, .mem x' c' n' => E.beq x x' && E.beq c c' && n == n'
  | .call f args, .call f' args' => f == f' && E.beqL args args'
  | .mcall o m args, .mcall o' m' args' => E.beq o o' && m == m' && E.beqL args args'
  | .kwcall o m ks args, .kwcall o' m' ks' args' => E.beq o o' && m == m' && ks == ks' && E.beqL args args'
  | .comp elt x it filt, .comp elt' x' it' filt' => E.beq elt elt' && x == x' && E.beq it it' && E.beqO filt filt'
  | _, _ => false
def E.beqL : List E → List E → Bool
  | [], [] => true
  | a :: as, b :: bs => E.beq a b && E.beqL as bs
  | _, _ => false
def E.beqO : Option E → Option E → Bool
  | none, none => true
  | some a, some b => E.beq a b
  | _, _ => false
end

mutual
theorem E.beq_sound : (a b : E) → E.beq a b = true → a = b
  | .var x, b, h => by cases b <;> simp_all [E.beq]
  | .lit v, b, h => by cases b <;> simp_all [E.beq]
  | .tup a, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq] at h ⊢
      rw [E.beqL_sound _ _ h]
  | .listD a, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq] at h ⊢
      rw [E.beqL_sound _ _ h]
  | .dictD a, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq] at h ⊢
      rw [E.beqL_sound _ _ h]
  | .setD a, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq] at h ⊢
      rw [E.beqL_sound _ _ h]
  | .attr e f, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true, beq_iff_eq] at h ⊢
      rw [E.beq_sound _ _ h.1, h.2]
  | .sub e i, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true] at h ⊢
      rw [E.beq_sound _ _ h.1, E.beq_sound _ _ h.2]
  | .sliceFrom e i, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true] at h ⊢
      rw [E.beq_sound _ _ h.1, E.beq_sound _ _ h.2]
  | .bin op x y, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true, decide_eq_true_eq] at h ⊢
      rw [h.1.1, E.beq_sound _ _ h.1.2, E.beq_sound _ _ h.2]
  | .cmp2 o1 o2 x y z, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true, decide_eq_true_eq] at h ⊢
      rw [h.1.1.1.1, h.1.1.1.2, E.beq_sound _ _ h.1.1.2, E.beq_sound _ _ h.1.2, E.beq_sound _ _ h.2]
  | .not x, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq] at h ⊢
      rw [E.beq_sound _ _ h]
  | .and x y, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true] at h ⊢
      rw [E.beq_sound _ _ h.1, E.beq_sound _ _ h.2]
  | .or x y, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true] at h ⊢
      rw [E.beq_sound _ _ h.1, E.beq_sound _ _ h.2]
  | .cond x y z, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true] at h ⊢
      rw [E.beq_sound _ _ h.1.1, E.beq_sound _ _ h.1.2, E.beq_sound _ _ h.2]
  | .isNone x n, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true, beq_iff_eq] at h ⊢
      rw [E.beq_sound _ _ h.1, h.2]
  | .typeIs x ty n, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true, beq_iff_eq] at h ⊢
      rw [E.beq_sound _ _ h.1.1, h.1.2, h.2]
  | .mem x c n, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true, beq_iff_eq] at h ⊢
      rw [E.beq_sound _ _ h.1.1, E.beq_sound _ _ h.1.2, h.2]
  | .call f args, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true, beq_iff_eq] at h ⊢
      rw [h.1, E.beqL_sound _ _ h.2]
  | .mcall o m args, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true, beq_iff_eq] at h ⊢
      rw [E.beq_sound _ _ h.1.1, h.1.2, E.beqL_sound _ _ h.2]
  | .kwcall o m ks args, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true, beq_iff_eq] at h ⊢
      rw [E.beq_sound _ _ h.1.1.1, h.1.1.2, h.1.2, E.beqL_sound _ _ h.2]
  | .comp elt x it filt, b, h => by
      cases b <;> simp only [E.beq, reduceCtorEq, Bool.and_eq_true, beq_iff_eq] at h ⊢
      rw [E.beq_sound _ _ h.1.1.1, h.1.1.2, E.beq_sound _ _ h.1.2, E.beqO_sound _ _ h.2]
theorem E.beqL_sound : (a b : List E) → E.beqL a b = true → a = b
  | [], b, h => by cases b <;> simp_all [E.beqL]
  | x :: xs, b, h => by
      cases b with
      | nil => simp [E.beqL] at h
      | cons y ys =>
        simp only [E.beqL, Bool.and_eq_true] at h
        rw [E.beq_sound _ _ h.1, E.beqL_sound _ _ h.2]
theorem E.beqO_sound : (a b : Option E) → E.beqO a b = true → a = b
  | none, b, h => by cases b <;> simp_all [E.beqO]
  | some x, b, h => by
      cases b with
      | none => simp [E.beqO] at h
      | some y => simp only [E.beqO] at h; rw [E.beq_sound _ _ h]
end

mutual
def Tgt.beq : Tgt → Tgt → Bool
  | .name x, .name y => x == y
  | .attr e f, .attr e' f' => E.beq e e' && f == f'
  | .sub e i, .sub e' i' => E.beq e e' && E.beq i i'
  | .tup ts, .tup ts' => Tgt.beqL ts ts'
  | _, _ => false
def Tgt.beqL : List Tgt → List Tgt → Bool
  | [], [] => true
  | a :: as, b :: bs => Tgt.beq a b && Tgt.beqL as bs
  | _, _ => false
end

mutual
theorem Tgt.beq_sound : (a b : Tgt) → Tgt.beq a b = true → a = b
  | .name x, b, h => by cases b <;> simp_all [Tgt.beq]
  | .attr e f, b, h => by
      cases b <;> simp only [Tgt.beq, reduceCtorEq, Bool.and_eq_true, beq_iff_eq] at h ⊢
      rw [E.beq_sound _ _ h.1, h.2]
  | .sub e i, b, h => by
      cases b <;> simp only [Tgt.beq, reduceCtorEq, Bool.and_eq_true] at h ⊢
      rw [E.beq_sound _ _ h.1, E.beq_sound _ _ h.2]
  | .tup ts, b, h => by
      cases b <;> simp only [Tgt.beq, reduceCtorEq] at h ⊢
      rw [Tgt.beqL_sound _ _ h]
theorem Tgt.beqL_sound : (a b : List Tgt) → Tgt.beqL a b = true → a = b
  | [], b, h => by cases b <;> simp_all [Tgt.beqL]
  | x :: xs, b, h => by
      cases b with
      | nil => simp [Tgt.beqL] at h
      | cons y ys =>
        simp only [Tgt.beqL, Bool.and_eq_true] at h
        rw [Tgt.beq_sound _ _ h.1, Tgt.beqL_sound _ _ h.2]
end

mutual
def S.beq : S → S → Bool
  | .assign ts e, .assign ts' e' => Tgt.beqL ts ts' && E.beq e e'
  | .aug t op e, .aug t' op' e' => Tgt.beq t t' && decide (op = op') && E.beq e e'
  | .expr e, .expr e' => E.beq e e'
  | .ifte c t f, .ifte c' t' f' => E.beq c c' && S.beqL t t' && S.beqL f f'
  | .forIn t it b, .forIn t' it' b' => Tgt.beq t t' && E.beq it it' && S.beqL b b'
  | .while c b, .while c' b' => E.beq c c' && S.beqL b b'
  | .ret e, .ret e' => E.beq e e'
  | .brk, .brk => true
  | .raise e, .raise e' => E.beq e e'
  | .try b c x hd, .try b' c' x' hd' => S.beqL b b' && c == c' && x == x' && S.beqL hd hd'
  | .assert e, .assert e' => E.beq e e'
  | .pass, .pass => true
  | _, _ => false
def S.beqL : List S → List S → Bool
  | [], [] => true
  | a :: as, b :: bs => S.beq a b && S.beqL as bs
  | _, _ => false
end

mutual
theorem S.beq_sound : (a b : S) → S.beq a b = true → a = b
  | .assign ts e, b, h => by
      cases b <;> simp only [S.beq, reduceCtorEq, Bool.and_eq_true] at h ⊢
      rw [Tgt.beqL_sound _ _ h.1, E.beq_sound _ _ h.2]
  | .aug t op e, b, h => by
      cases b <;> simp only [S.beq, reduceCtorEq, Bool.and_eq_true, decide_eq_true_eq] at h ⊢
      rw [Tgt.beq_sound _ _ h.1.1, h.1.2, E.beq_sound _ _ h.2]
  | .expr e, b, h => by
      cases b <;> simp only [S.beq, reduceCtorEq] at h ⊢
      rw [E.beq_sound _ _ h]
  | .ifte c t f, b, h => by
      cases b <;> simp only [S.beq, reduceCtorEq, Bool.and_eq_true] at h ⊢
      rw [E.beq_sound _ _ h.1.1, S.beqL_sound _ _ h.1.2, S.beqL_sound _ _ h.2]
  | .forIn t it bd, b, h => by
      cases b <;> simp only [S.beq, reduceCtorEq, Bool.and_eq_true] at h ⊢
      rw [Tgt.beq_sound _ _ h.1.1, E.beq_sound _ _ h.1.2, S.beqL_sound _ _ h.2]
  | .while c bd, b, h => by
      cases b <;> simp only [S.beq, reduceCtorEq, Bool.and_eq_true] at h ⊢
      rw [E.beq_sound _ _ h.1, S.beqL_sound _ _ h.2]
  | .ret e, b, h => by
      cases b <;> simp only [S.beq, reduceCtorEq] at h ⊢
      rw [E.beq_sound _ _ h]
  | .brk, b, h => by cases b <;> simp_all [S.beq]
  | .raise e, b, h => by
      cases b <;> simp only [S.beq, reduceCtorEq] at h ⊢
      rw [E.beq_sound _ _ h]
  | .try bd c x hd, b, h => by
      cases b <;> simp only [S.beq, reduceCtorEq, Bool.and_eq_true, beq_iff_eq] at h ⊢
      rw [S.beqL_sound _ _ h.1.1.1, h.1.1.2, h.1.2, S.beqL_sound _ _ h.2]
  | .assert e, b, h => by
      cases b <;> simp only [S.beq, reduceCtorEq] at h ⊢
      rw [E.beq_sound _ _ h]
  | .pass, b, h => by cases b <;> simp_all [S.beq]
theorem S.beqL_sound : (a b : List S) → S.beqL a b = true → a = b
  | [], b, h => by cases b <;> simp_all [S.beqL]
  | x :: xs, b, h => by
      cases b with
      | nil => simp [S.beqL] at h
      | cons y ys =>
        simp only [S.beqL, Bool.and_eq_true] at h
        rw [S.beq_sound _ _ h.1, S.beqL_sound _ _ h.2]
end

def Fn.beq (a b : Fn) : Bool := a.params == b.params && S.beqL a.body b.body

theorem Fn.beq_sound {a b : Fn} (h : Fn.beq a b = true) : a = b := by
  obtain ⟨p, bd⟩ := a; obtain ⟨p', bd'⟩ := b
  simp only [Fn.beq, Bool.and_eq_true, beq_iff_eq] at h
  rw [h.1, S.beqL_sound _ _ h.2]

def funsBeq : List (String × Fn) → List (String × Fn) → Bool
  | [], [] => true
  | (q, f) :: fs, (q', f') :: fs' => q == q' && Fn.beq f f' && funsBeq fs fs'
  | _, _ => false

theorem funsBeq_sound : (a b : List (String × Fn)) → funsBeq a b = true → a = b
  | [], b, h => by cases b <;> simp_all [funsBeq]
  | (q, f) :: fs, b, h => by
      cases b with
      | nil => simp [funsBeq] at h
      | cons p ps =>
        obtain ⟨q', f'⟩ := p
        simp only [funsBeq, Bool.and_eq_true, beq_iff_eq] at h
        rw [h.1.1, Fn.beq_sound h.1.2, funsBeq_sound _ _ h.2]

def classesBeq : List ClassDef → List ClassDef → Bool
  | [], [] => true
  | c :: cs, c' :: cs' => c.name == c'.name && c.methods == c'.methods && c.isException == c'.isException &&
      classesBeq cs cs'
  | _, _ => false

theorem classesBeq_sound : (a b : List ClassDef) → classesBeq a b = true → a = b
  | [], b, h => by cases b <;> simp_all [classesBeq]
  | c :: cs, b, h => by
      cases b with
      | nil => simp [classesBeq] at h
      | cons c' cs' =>
        obtain ⟨n, m, e⟩ := c; obtain ⟨n', m', e'⟩ := c'
        simp only [classesBeq, Bool.and_eq_true, beq_iff_eq] at h
        rw [h.1.1.1, h.1.1.2, h.1.2, classesBeq_sound _ _ h.2]

def Py.Module.beq (a b : Py.Module) : Bool :=
  funsBeq a.funs b.funs && classesBeq a.classes b.classes && a.externs == b.externs && S.beqL a.init b.init

theorem Py.Module.beq_sound {a b : Py.Module} (h : Py.Module.beq a b = true) : a = b := by
  obtain ⟨f, c, x, i⟩ := a; obtain ⟨f', c', x', i'⟩ := b
  simp only [Py.Module.beq, Bool.and_eq_true, beq_iff_eq] at h
  rw [funsBeq_sound _ _ h.1.1.1, classesBeq_sound _ _ h.1.1.2, h.1.2, S.beqL_sound _ _ h.2]

def Py.Module.beqO : Option Py.Module → Option Py.Module → Bool
  | some a, some b => Py.Module.beq a b
  | none, none => true
  | _, _ => false

theorem Py.Module.beqO_sound {a b : Option Py.Module} (h : Py.Module.beqO a b = true) : a = b := by
  cases a <;> cases b <;> simp [Py.Module.beqO] at h ⊢
  exact Py.Module.beq_sound h

end PCSCR
