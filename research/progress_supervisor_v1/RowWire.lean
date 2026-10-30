import Adapter
set_option autoImplicit false
namespace PCSProgressRows
open PCSProgressAdapter

structure Request where
  state : Nat
  action : Nat
  before : Rows
  target : Nat
  after : Rows
  deriving DecidableEq, Repr

def flag (b : Bool) : Nat := if b then 1 else 0
def Fits (r : Request) : Prop :=
  r.state < 256 ∧ r.action < 256 ∧ r.before.published < 256 ∧
  r.target < 256 ∧ r.after.published < 256

def encode (r : Request) : List Nat :=
  [80,67,83,82,1,r.state,r.action,flag r.before.isPublic,flag r.before.loaded,
   flag r.before.sanitized,r.before.published,r.target,flag r.after.isPublic,
   flag r.after.loaded,flag r.after.sanitized,r.after.published]

def decode : List Nat → Option Request
  | [80,67,83,82,1,s,a,b,l,z,p,t,c,m,n,q] =>
      if s<256 ∧ a<256 ∧ b<2 ∧ l<2 ∧ z<2 ∧ p<256 ∧ t<256 ∧ c<2 ∧ m<2 ∧ n<2 ∧ q<256
      then some ⟨s,a,⟨b==1,l==1,z==1,p⟩,t,⟨c==1,m==1,n==1,q⟩⟩ else none
  | _ => none

def check (r : Request) : Bool :=
  decide (Valid r.state r.before) && decide (step r.state r.action r.before = some (r.target,r.after))

def process (raw : List Nat) : List Nat :=
  match decode raw with
  | some r => if check r then [2,1] else [2,0]
  | none => [2,0]

def batch (raw : List Nat) : List Nat :=
  (List.range ((raw.length+15)/16)).flatMap (fun i => process ((raw.drop (i*16)).take 16))

theorem flag_bit (n : Nat) (h : n < 2) : flag (n==1) = n := by
  have : n=0 ∨ n=1 := by omega
  rcases this with rfl | rfl <;> rfl

theorem request_roundtrip (r : Request) (h : Fits r) : decode (encode r) = some r := by
  rcases r with ⟨s,a,⟨b,l,z,p⟩,t,⟨c,m,n,q⟩⟩
  cases b <;> cases l <;> cases z <;> cases c <;> cases m <;> cases n <;>
    simp_all [Fits,encode,decode,flag]

theorem request_canonical {raw : List Nat} {r : Request} (h : decode raw = some r) :
    encode r = raw ∧ Fits r := by
  unfold decode at h
  split at h
  next s a b l z p t c m n q =>
    split at h
    next bounds =>
      cases h
      simp_all [encode,Fits,flag_bit]
    next => contradiction
  next => contradiction

theorem request_injective {a b : Request} (ha : Fits a) (hb : Fits b)
    (h : encode a = encode b) : a = b := by
  have : some a = some b := by rw [← request_roundtrip a ha,h,request_roundtrip b hb]
  exact Option.some.inj this

theorem check_sound {r : Request} (h : check r = true) :
    Valid r.state r.before ∧ step r.state r.action r.before = some (r.target,r.after) := by
  simpa [check] using h

theorem raw_acceptance {raw : List Nat} (h : process raw = [2,1]) :
    ∃ r, decode raw = some r ∧ encode r = raw ∧ Fits r ∧
      Valid r.state r.before ∧ step r.state r.action r.before = some (r.target,r.after) := by
  unfold process at h
  cases hd : decode raw with
  | none => simp [hd] at h
  | some r =>
    simp only [hd] at h
    by_cases hc : check r = true
    · exact ⟨r,rfl,(request_canonical hd).1,(request_canonical hd).2,check_sound hc⟩
    · simp [hc] at h

theorem raw_refines {raw : List Nat} (h : process raw = [2,1]) :
    ∃ r, decode raw = some r ∧ Valid r.target r.after ∧
      Edge r.state r.action r.target ∧ rank r.target < rank r.state := by
  obtain ⟨r,hd,_,_,hv,hs⟩ := raw_acceptance h
  exact ⟨r,hd,step_refines hv hs⟩

theorem malformed_refuses (raw : List Nat) (h : decode raw = none) :
    process raw = [2,0] := by simp [process,h]

theorem process_octets (raw : List Nat) : ∀ n ∈ process raw, n < 256 := by
  unfold process
  cases hd : decode raw with
  | none => simp
  | some r =>
    change ∀ n ∈ (if check r then [2,1] else [2,0]), n < 256
    by_cases hc : check r = true <;> simp [hc]

theorem batch_octets (raw : List Nat) : ∀ n ∈ batch raw, n < 256 := by
  intro n hn
  obtain ⟨_,_,hp⟩ := List.mem_flatMap.mp hn
  exact process_octets _ n hp

theorem native_octets_roundtrip (raw : List Nat) :
    ((batch raw).map UInt8.ofNat).map UInt8.toNat = batch raw := by
  have bounds := batch_octets raw
  generalize batch raw = xs at bounds ⊢
  induction xs with
  | nil => rfl
  | cons b bs ih =>
    simp only [List.map_cons,List.cons.injEq]
    constructor
    · change b % 256 = b
      exact Nat.mod_eq_of_lt (bounds b (by simp))
    · exact ih (fun n hn => bounds n (List.mem_cons_of_mem b hn))
end PCSProgressRows
