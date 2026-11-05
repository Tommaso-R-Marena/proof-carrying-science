import Wire
set_option autoImplicit false

/-! The six-byte wire contract. These are ordinary kernel proofs about the same
    functions compiled into Main; they do not prove Python, SQL or compiler
    correspondence. Bounds are explicit, including on the concrete certificate. -/
namespace PCSProgressCodec
open PCSProgress PCSProgressWire

def RequestFits (r : Request) : Prop :=
  r.state < 65536 ∧ ∀ a, r.proposal = some a → a < 65536

def requestBytes (r : Request) : List Nat :=
  match r.proposal with
  | none => [1,r.state%256,r.state/256,0,0,0]
  | some a => [1,r.state%256,r.state/256,1,a%256,a/256]

theorem request_roundtrip {r : Request} (h : RequestFits r) :
    decode (requestBytes r) = some r := by
  rcases r with ⟨s,p⟩
  rcases h with ⟨hs,hp⟩
  change s < 65536 at hs
  change ∀ a, p = some a → a < 65536 at hp
  have slo : s % 256 < 256 := Nat.mod_lt _ (by decide)
  have shi : s / 256 < 256 := by omega
  have sid : s % 256 + 256 * (s / 256) = s := by omega
  cases p with
  | none => simp [requestBytes,decode,slo,shi,sid]
  | some a =>
    have ha := hp a rfl
    have alo : a % 256 < 256 := Nat.mod_lt _ (by decide)
    have ahi : a / 256 < 256 := by omega
    have aid : a % 256 + 256 * (a / 256) = a := by omega
    simp [requestBytes,decode,slo,shi,alo,ahi,sid,aid]

theorem request_injective {r t : Request} (hr : RequestFits r) (ht : RequestFits t)
    (h : requestBytes r = requestBytes t) : r = t := by
  have := congrArg decode h
  simpa [request_roundtrip hr,request_roundtrip ht] using this

theorem request_decode_canonical {raw : List Nat} {r : Request}
    (h : decode raw = some r) : RequestFits r ∧ requestBytes r = raw := by
  unfold decode at h
  split at h
  next sl sh p al ah =>
    split at h
    next bounds =>
      rcases bounds with ⟨hsl,hsh,hal,hah⟩
      split at h
      next hp =>
        simp only [Option.some.injEq] at h
        subst r
        subst p
        constructor
        · dsimp [RequestFits]
          refine ⟨by omega,?_⟩
          intro a ha
          simp only [Option.some.injEq] at ha
          omega
        · simp only [requestBytes]
          have sl' : (sl+256*sh)%256=sl := by omega
          have sh' : (sl+256*sh)/256=sh := by omega
          have al' : (al+256*ah)%256=al := by omega
          have ah' : (al+256*ah)/256=ah := by omega
          simp [sl',sh',al',ah']
      next hp =>
        split at h
        next hz =>
          rcases hz with ⟨rfl,rfl,rfl⟩
          simp only [Option.some.injEq] at h
          subst r
          constructor
          · dsimp [RequestFits]
            exact ⟨by omega,fun _ h => by contradiction⟩
          · simp only [requestBytes]
            have sl' : (sl+256*sh)%256=sl := by omega
            have sh' : (sl+256*sh)/256=sh := by omega
            simp [sl',sh']
        next => contradiction
    next => contradiction
  next => contradiction

/-- Only the selected status carries an action and rank. Every other status
    requires zero padding; unknown statuses, versions and nonbytes refuse. -/
def decodeReply : List Nat → Option (Reply × Nat)
  | [1,0,0,0,0,0] => some (.halt,0)
  | [1,1,al,ah,rl,rh] =>
      if al<256 ∧ ah<256 ∧ rl<256 ∧ rh<256 then
        some (.selected (al+256*ah),rl+256*rh) else none
  | [1,2,0,0,0,0] => some (.refused,0)
  | [1,3,0,0,0,0] => some (.malformed,0)
  | _ => none

theorem selected_roundtrip (d : Spec) (s a : Nat)
    (ha : a < 65536) (hr : rank d s < 65536) :
    decodeReply (encode d s (.selected a)) = some (.selected a,rank d s) := by
  have alo : a % 256 < 256 := Nat.mod_lt _ (by decide)
  have ahi : a / 256 < 256 := by omega
  have rlo : rank d s % 256 < 256 := Nat.mod_lt _ (by decide)
  have rhi : rank d s / 256 < 256 := by omega
  have aid : a % 256 + 256 * (a / 256) = a := by omega
  have rid : rank d s % 256 + 256 * (rank d s / 256) = rank d s := by omega
  simp [encode,decodeReply,alo,ahi,rlo,rhi,aid,rid]

def FitsWire (d : Spec) : Prop :=
  (∀ p ∈ d.base.allowed, p.2 < 65536) ∧
  (∀ s ∈ region d, rank d s < 65536)

instance (d : Spec) : Decidable (FitsWire d) := by unfold FitsWire; infer_instance

def replyRank (d : Spec) (s : Nat) : Reply → Nat
  | .selected _ => rank d s
  | _ => 0

theorem typed_roundtrip {d : Spec} (hf : FitsWire d) (r : Request) :
    decodeReply (encode d r.state (typed d r)) =
      some (typed d r,replyRank d r.state (typed d r)) := by
  cases ht : typed d r with
  | halt => simp [encode,decodeReply,replyRank]
  | refused => simp [encode,decodeReply,replyRank]
  | malformed => simp [encode,decodeReply,replyRank]
  | selected a =>
    obtain ⟨_,hw,_,hp⟩ := choose_sound (selected_from_choose ht)
    exact selected_roundtrip d r.state a (hf.1 _ hp) (hf.2 _ hw)

theorem process_selected_sound {d : Spec} {raw : List Nat} {r : Request} {a k : Nat}
    (hf : FitsWire d) (hd : decode raw = some r)
    (h : decodeReply (process d raw) = some (.selected a,k)) :
    choose d r.state r.proposal = some a ∧ k = rank d r.state := by
  simp only [process,hd] at h
  cases ht : typed d r with
  | halt => simp [ht,encode,decodeReply] at h
  | refused => simp [ht,encode,decodeReply] at h
  | malformed => simp [ht,encode,decodeReply] at h
  | selected b =>
    obtain ⟨_,hw,_,hp⟩ := choose_sound (selected_from_choose ht)
    rw [ht,selected_roundtrip d r.state b (hf.1 _ hp) (hf.2 _ hw)] at h
    have eq : b = a ∧ rank d r.state = k := by simpa using h
    exact ⟨eq.1 ▸ selected_from_choose ht,eq.2.symm⟩

theorem raw_selected_all_outcomes {d : Spec} {raw : List Nat} {r : Request} {a k : Nat}
    (hf : FitsWire d) (hd : decode raw = some r)
    (h : decodeReply (process d raw) = some (.selected a,k))
    {e : PCSActionShield.Edge} (he : e ∈ d.base.edges)
    (hs : e.source = r.state) (ha : e.action = a) :
    e.target ∈ region d ∧ e.target ∈ d.base.safe ∧
      rank d e.target < k ∧ a ∉ d.base.forbidden := by
  obtain ⟨hc,hk⟩ := process_selected_sound hf hd h
  simpa [hk] using chosen_step_progresses hc he hs ha

theorem typed_octets {d : Spec} (hf : FitsWire d) (r : Request) :
    ∀ b ∈ encode d r.state (typed d r), b < 256 := by
  cases ht : typed d r with
  | halt => simp [encode]
  | refused => simp [encode]
  | malformed => simp [encode]
  | selected a =>
    obtain ⟨_,hw,_,hp⟩ := choose_sound (selected_from_choose ht)
    have ha := hf.1 _ hp
    have hr := hf.2 _ hw
    simp only [encode,List.mem_cons,List.not_mem_nil,or_false]
    intro b hb
    have : a % 256 < 256 := Nat.mod_lt _ (by decide)
    have : rank d r.state % 256 < 256 := Nat.mod_lt _ (by decide)
    omega

theorem process_octets {d : Spec} (hf : FitsWire d) (raw : List Nat) :
    ∀ b ∈ process d raw, b < 256 := by
  unfold process
  cases hd : decode raw with
  | none => simp [encode]
  | some r => exact typed_octets hf r

theorem batch_octets {d : Spec} (hf : FitsWire d) (raw : List Nat) :
    ∀ b ∈ batch d raw, b < 256 := by
  intro b hb
  obtain ⟨_,_,hb⟩ := List.mem_flatMap.mp hb
  exact process_octets hf _ b hb

/-- Main's UInt8 conversion cannot silently truncate a checked reply. -/
theorem native_octets_roundtrip {d : Spec} (hf : FitsWire d) (raw : List Nat) :
    ((batch d raw).map UInt8.ofNat).map UInt8.toNat = batch d raw := by
  have bounds := batch_octets hf raw
  generalize batch d raw = xs at bounds ⊢
  induction xs with
  | nil => rfl
  | cons b bs ih =>
    simp only [List.map_cons,List.cons.injEq]
    constructor
    · change b % 256 = b
      exact Nat.mod_eq_of_lt (bounds b (by simp))
    · exact ih (fun n hn => bounds n (List.mem_cons_of_mem b hn))

end PCSProgressCodec
