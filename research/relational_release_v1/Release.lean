import Std.Tactic

/-! Research-only declassification. Public query is fixed before private access.
    Proposal decisions and audit data are private. Trusted finalization is required;
    wall-clock timing, OS/process behavior and persistence refinement are external. -/
set_option autoImplicit false
namespace PCSRelationalRelease

inductive Query where
  | count | parity
  deriving DecidableEq, Repr
structure Data where
  flags : List Bool
  hidden : Bool
  deriving DecidableEq, Repr
def view (q : Query) (d : Data) : Nat :=
  match q with
  | .count => d.flags.count true
  | .parity => d.flags.count true % 2
structure Claim where
  reported : Nat
  reverse : Bool
  deriving DecidableEq, Repr
def TrueClaim (q : Query) (d : Data) (c : Claim) : Prop := c.reported = view q d ∧ c.reported ≤ 4
instance (q : Query) (d : Data) (c : Claim) : Decidable (TrueClaim q d c) :=
  inferInstanceAs (Decidable (_ ∧ _))
def queryByte : Query → UInt8 | .count => 0 | .parity => 1
def boolByte (b : Bool) : UInt8 := if b then 1 else 0
def render (q : Query) (c : Claim) : List UInt8 :=
  [3,2,queryByte q,boolByte c.reverse,UInt8.ofNat c.reported]
def canonical (q : Query) (d : Data) : List UInt8 := render q ⟨view q d,false⟩
def truthGate (q : Query) (d : Data) (c : Claim) : Option (List UInt8) :=
  if TrueClaim q d c then some (render q c) else none

theorem truth_gate_sound {q : Query} {d : Data} {c : Claim} {b : List UInt8}
    (h : truthGate q d c = some b) : TrueClaim q d c ∧ b = render q c := by
  unfold truthGate at h
  split at h
  · rename_i ht; cases h; exact ⟨ht,rfl⟩
  · cases h
theorem both_representations_true (q : Query) (d : Data) (style : Bool) (hb : view q d ≤ 4) :
    truthGate q d ⟨view q d,style⟩ = some (render q ⟨view q d,style⟩) := by
  simp [truthGate,TrueClaim,hb]
def leakClaim (q : Query) (d : Data) : Claim := ⟨view q d,d.hidden⟩
theorem representation_channel_decodes_secret (q : Query) (d : Data) :
    (render q (leakClaim q d)).getD 3 2 = boolByte d.hidden := by rfl
theorem representation_channel_is_verified (q : Query) (d : Data) (hb : view q d ≤ 4) :
    truthGate q d (leakClaim q d) = some (render q (leakClaim q d)) :=
  both_representations_true q d d.hidden hb
theorem representation_counterexample :
    truthGate .count ⟨[true,false],false⟩ ⟨1,false⟩ ≠
      truthGate .count ⟨[true,false],true⟩ ⟨1,true⟩ := by decide

def decodeStyles (bs : List (List UInt8)) : List Bool := bs.map (fun b => b.getD 3 2 == 1)
theorem unbounded_verified_representation_channel (q : Query) (flags : List Bool) (secret : List Bool) :
    decodeStyles (secret.map (fun b => render q (leakClaim q ⟨flags,b⟩))) = secret := by
  induction secret with
  | nil => rfl
  | cons b bs ih =>
    cases b with
    | false => exact congrArg (List.cons false) ih
    | true => exact congrArg (List.cons true) ih

theorem all_encoded_claims_verified (q : Query) (bits : List Bool)
    (hb : view q ⟨bits,false⟩ ≤ 4) (secret : List Bool) :
    ∀ b ∈ secret, truthGate q ⟨bits,b⟩ (leakClaim q ⟨bits,b⟩) =
      some (render q (leakClaim q ⟨bits,b⟩)) := by
  intro b _
  apply representation_channel_is_verified
  cases q <;> exact hb

theorem bounded_render_value (q : Query) (d : Data) (c : Claim) (hc : TrueClaim q d c) :
    ((render q c).getD 4 0).toNat = c.reported := by
  change (UInt8.ofNat c.reported).toNat = c.reported
  exact UInt8.toNat_ofNat_of_lt' (by change c.reported < 256; have := hc.2; omega)

def optionalCanonical (q : Query) (d : Data) : List (List UInt8) :=
  if d.hidden then [canonical q d] else []
theorem withholding_counterexample :
    optionalCanonical .count ⟨[true,false],false⟩ ≠
      optionalCanonical .count ⟨[true,false],true⟩ := by decide
theorem adaptive_query_choice_counterexample :
    canonical .count ⟨[],false⟩ ≠ canonical .parity ⟨[],true⟩ ∧
      view .count ⟨[],false⟩ = view .parity ⟨[],true⟩ := by decide

inductive Phase where | open | done deriving DecidableEq, Repr
inductive Command where
  | propose (c : Option Claim)
  | finalize
  deriving DecidableEq, Repr
def transition (q : Query) (d : Data) (s : Phase) (a : Command) : Phase × List (List UInt8) :=
  match s,a with
  | .open,.finalize => (.done,[canonical q d])
  | _,_ => (s,[])
def run (q : Query) (d : Data) : Phase → List Command → Phase × List (List UInt8)
  | s,[] => (s,[])
  | s,a::as =>
      let (t,head) := transition q d s a
      let (u,tail) := run q d t as
      (u,head ++ tail)
theorem proposals_have_no_public_effect (q : Query) (d : Data) (s : Phase) (c : Option Claim) :
    transition q d s (.propose c) = (s,[]) := by cases s <;> rfl
theorem proposals_preserve_state (q : Query) (d : Data) (s : Phase) (cs : List (Option Claim)) :
    run q d s (cs.map Command.propose) = (s,[]) := by
  induction cs with
  | nil => rfl
  | cons c cs ih => simp [run,proposals_have_no_public_effect,ih]
theorem forced_completion_exact (q : Query) (d : Data) (cs : List (Option Claim)) :
    run q d .open (cs.map Command.propose ++ [.finalize]) = (.done,[canonical q d]) := by
  induction cs with
  | nil => rfl
  | cons c cs ih => simp [run,proposals_have_no_public_effect,ih]
theorem canonical_depends_only_on_view (q : Query) (d₁ d₂ : Data)
    (hv : view q d₁ = view q d₂) : canonical q d₁ = canonical q d₂ := by
  simp only [canonical]; rw [hv]
theorem scheduled_release_noninterference (q : Query) (d₁ d₂ : Data)
    (hv : view q d₁ = view q d₂) (cs₁ cs₂ : List (Option Claim)) :
    run q d₁ .open (cs₁.map Command.propose ++ [.finalize]) =
      run q d₂ .open (cs₂.map Command.propose ++ [.finalize]) := by
  rw [forced_completion_exact,forced_completion_exact,canonical_depends_only_on_view q d₁ d₂ hv]
theorem post_completion_has_no_effect (q : Query) (d : Data) (as : List Command) :
    run q d .done as = (.done,[]) := by
  induction as with
  | nil => rfl
  | cons a as ih => cases a <;> simp [run,transition,ih]
theorem finalize_once (q : Query) (d : Data) (as : List Command) :
    run q d .open (.finalize :: as) = (.done,[canonical q d]) := by
  simp [run,transition,post_completion_has_no_effect]

def flags (mask : UInt8) : List Bool :=
  [mask.toNat % 2 == 1,mask.toNat / 2 % 2 == 1,
   mask.toNat / 4 % 2 == 1,mask.toNat / 8 % 2 == 1]
def decodeQuery (b : UInt8) : Option Query :=
  if b = 0 then some .count else if b = 1 then some .parity else none
structure Request where
  query : Query
  data : Data
  closed : Bool
  action : UInt8
  claim : Claim
  deriving DecidableEq, Repr
def decode : List UInt8 → Option Request
  | [3,q,g,mask,h,a,style,n] => do
      let query ← decodeQuery q
      if g.toNat ≤ 1 ∧ mask.toNat ≤ 15 ∧ h.toNat ≤ 1 ∧ a.toNat ≤ 2 ∧
          style.toNat ≤ 1 ∧ n.toNat ≤ 4 ∧ (a = 1 ∨ (style = 0 ∧ n = 0)) then
        some ⟨query,⟨flags mask,h == 1⟩,g == 1,a,⟨n.toNat,style == 1⟩⟩
      else none
  | _ => none
def accepted (r : Request) : Bool :=
  !r.closed && (r.action != 1 || decide (TrueClaim r.query r.data r.claim))
def payload (r : Request) : List UInt8 :=
  if r.action = 0 then [boolByte r.data.hidden] ++ r.data.flags.map boolByte
  else if r.action = 1 then render r.query r.claim
  else canonical r.query r.data
def process (raw : List UInt8) : List UInt8 :=
  match decode raw with
  | none => [3,2,0,0]
  | some r => if accepted r then
      [3,1,if r.action = 2 then 1 else boolByte r.closed,r.action] ++ payload r
    else [3,0,boolByte r.closed,r.action]
theorem malformed_request_refuses (raw : List UInt8) (h : decode raw = none) :
    process raw = [3,2,0,0] := by simp [process,h]
theorem wire_accepted_sound (raw : List UInt8) (h : (process raw).getD 1 2 = 1) :
    ∃ r, decode raw = some r ∧ accepted r = true ∧
      process raw = [3,1,if r.action = 2 then 1 else boolByte r.closed,r.action] ++ payload r := by
  cases hd : decode raw with
  | none => simp [process,hd] at h
  | some r =>
    by_cases ha : accepted r = true
    · exact ⟨r,rfl,ha,by simp [process,hd,ha]⟩
    · simp [process,hd,ha] at h
theorem wire_claim_truth (raw : List UInt8) (r : Request)
    (_hd : decode raw = some r) (ha : accepted r = true) (hc : r.action = 1) :
    TrueClaim r.query r.data r.claim := by
  simp [accepted,hc] at ha
  exact ha.2
theorem wire_finalization_exact (raw : List UInt8) (r : Request)
    (hd : decode raw = some r) (ha : accepted r = true) (hc : r.action = 2) :
    process raw = [3,1,1,2] ++ canonical r.query r.data := by
  simp [process,hd,ha,hc,payload]
theorem closed_request_refuses (r : Request) (h : r.closed = true) : accepted r = false := by
  simp [accepted,h]

end PCSRelationalRelease
