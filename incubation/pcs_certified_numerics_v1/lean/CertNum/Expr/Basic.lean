import CertNum.Interval.Arithmetic

/-!
# Typed rational expression language (CertNum)
-/

namespace CertNum

inductive Expr where
  | const (q : ℚ)
  | var (name : String)
  | neg (e : Expr)
  | abs (e : Expr)
  | add (l r : Expr)
  | sub (l r : Expr)
  | mul (l r : Expr)
  | div (l r : Expr)
  | powNat (base : Expr) (n : Nat)
  deriving Repr

abbrev Env := String → Option ℚ

def Expr.eval : Expr → Env → Option ℚ
  | .const q, _ => some q
  | .var v, ρ => ρ v
  | .neg e, ρ =>
      match eval e ρ with
      | some x => some (-x)
      | none => none
  | .abs e, ρ =>
      match eval e ρ with
      | some x => some |x|
      | none => none
  | .add l r, ρ =>
      match eval l ρ, eval r ρ with
      | some x, some y => some (x + y)
      | _, _ => none
  | .sub l r, ρ =>
      match eval l ρ, eval r ρ with
      | some x, some y => some (x - y)
      | _, _ => none
  | .mul l r, ρ =>
      match eval l ρ, eval r ρ with
      | some x, some y => some (x * y)
      | _, _ => none
  | .div l r, ρ =>
      match eval l ρ, eval r ρ with
      | some x, some y => if y = 0 then none else some (x / y)
      | _, _ => none
  | .powNat b n, ρ =>
      match eval b ρ with
      | some x => some (x ^ n)
      | none => none

abbrev Box := String → Interval

namespace Expr

/-- Natural interval extension using status tests (proof-friendly). -/
def evalInterval : Expr → Box → Enclosure
  | .const q, _ => Enclosure.ok (Interval.singleton q)
  | .var v, β => Enclosure.ok (β v)
  | .neg e, β =>
      let r := evalInterval e β
      if r.status = .ok then Enclosure.ok r.interval.neg else r
  | .abs e, β =>
      let r := evalInterval e β
      if r.status = .ok then Enclosure.ok r.interval.abs else r
  | .add l r, β =>
      let rl := evalInterval l β
      let rr := evalInterval r β
      if rl.status = .ok ∧ rr.status = .ok then
        Enclosure.ok (rl.interval.add rr.interval)
      else if rl.status ≠ .ok then rl else rr
  | .sub l r, β =>
      let rl := evalInterval l β
      let rr := evalInterval r β
      if rl.status = .ok ∧ rr.status = .ok then
        Enclosure.ok (rl.interval.sub rr.interval)
      else if rl.status ≠ .ok then rl else rr
  | .mul l r, β =>
      let rl := evalInterval l β
      let rr := evalInterval r β
      if rl.status = .ok ∧ rr.status = .ok then
        Enclosure.ok (rl.interval.mul rr.interval)
      else if rl.status ≠ .ok then rl else rr
  | .div l r, β =>
      let rl := evalInterval l β
      let rr := evalInterval r β
      if rl.status = .ok ∧ rr.status = .ok then
        rl.interval.div rr.interval
      else if rl.status ≠ .ok then rl else rr
  | .powNat b n, β =>
      let r := evalInterval b β
      if r.status = .ok then Enclosure.ok (r.interval.powNat n) else r

def EnvInBox (ρ : Env) (β : Box) : Prop :=
  ∀ v x, ρ v = some x → x ∈ᵢ β v

end Expr

end CertNum
