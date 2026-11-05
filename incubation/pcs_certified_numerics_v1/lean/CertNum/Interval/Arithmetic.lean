import CertNum.Interval.Basic

/-!
# Interval arithmetic operations (exact rational endpoints)
-/

namespace CertNum.Interval

def neg : Interval → Interval
  | empty => empty
  | nonempty lo hi _ => mk' (-hi) (-lo)

def abs : Interval → Interval
  | empty => empty
  | nonempty lo hi _ =>
    if 0 ≤ lo then mk' lo hi
    else if hi ≤ 0 then mk' (-hi) (-lo)
    else mk' 0 (ratMax (-lo) hi)

def add : Interval → Interval → Interval
  | empty, _ => empty
  | _, empty => empty
  | nonempty a b _, nonempty c d _ => mk' (a + c) (b + d)

def sub (I J : Interval) : Interval := add I (neg J)

def mul : Interval → Interval → Interval
  | empty, _ => empty
  | _, empty => empty
  | nonempty a b _, nonempty c d _ =>
      mk' (ratMin4 (a*c) (a*d) (b*c) (b*d))
          (ratMax4 (a*c) (a*d) (b*c) (b*d))

def square : Interval → Interval
  | empty => empty
  | nonempty lo hi _ =>
    if 0 ≤ lo then mk' (lo*lo) (hi*hi)
    else if hi ≤ 0 then mk' (hi*hi) (lo*lo)
    else mk' 0 (ratMax (lo*lo) (hi*hi))

def recip : Interval → Enclosure
  | empty => Enclosure.fail .emptyDomain
  | nonempty lo hi _ =>
    if hi < 0 ∨ 0 < lo then
      Enclosure.ok (mk' (1 / hi) (1 / lo))
    else
      Enclosure.fail .undefined

def div (I J : Interval) : Enclosure :=
  match recip J with
  | ⟨.ok, R⟩ => Enclosure.ok (mul I R)
  | e => e

def powNat : Interval → Nat → Interval
  | _, 0 => singleton 1
  | I, n + 1 => mul (powNat I n) I

def powInt (I : Interval) (k : Int) : Enclosure :=
  if 0 ≤ k then Enclosure.ok (powNat I k.toNat)
  else
    match recip I with
    | ⟨.ok, R⟩ => Enclosure.ok (powNat R ((-k).toNat))
    | e => e

def inter : Interval → Interval → Interval
  | empty, _ => empty
  | _, empty => empty
  | nonempty a b _, nonempty c d _ => mk' (ratMax a c) (ratMin b d)

def hull : Interval → Interval → Interval
  | empty, J => J
  | I, empty => I
  | nonempty a b _, nonempty c d _ => mk' (ratMin a c) (ratMax b d)

def bisect : Interval → Option (Interval × Interval)
  | empty => none
  | nonempty lo hi _ =>
      let m := (lo + hi) / 2
      some (mk' lo m, mk' m hi)

def definitelyLt (I J : Interval) : Bool :=
  match I, J with
  | nonempty _ b _, nonempty c _ _ => decide (b < c)
  | _, _ => false

def definitelyGt (I J : Interval) : Bool := definitelyLt J I

def possiblyEq (I J : Interval) : Bool :=
  match inter I J with
  | empty => false
  | _ => true

end CertNum.Interval
