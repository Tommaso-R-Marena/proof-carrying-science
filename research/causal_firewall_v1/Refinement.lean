import Policy

/-! Exact byte effects and causal public-sink noninterference. The controller is
arbitrary but shares initial memory/functions; the secret enters only through a
tracked read. Timing, termination/status channels, host code and logs are external. -/
set_option autoImplicit false
namespace PCSCausalFirewall
open PCSLLMFirewall

abbrev Bytes := List UInt8
structure Intent where
  action : Action
  payload : Bytes
  deriving DecidableEq, Repr
structure World where
  state : State
  publicData : Bytes
  privateData : Bytes
  deriving DecidableEq, Repr
inductive Effect where
  | none | privateWrite (payload : Bytes) | publicWrite (payload : Bytes)
  deriving DecidableEq, Repr
structure Result where
  next : State
  effect : Effect
  observation : Bytes
  deriving DecidableEq, Repr

def effectFor (i : Intent) : Effect :=
  match i.action with
  | .writePrivate => .privateWrite i.payload
  | .publish | .finish => .publicWrite i.payload
  | _ => .none
def observationFor (w : World) (a : Action) : Bytes :=
  match a with
  | .readPublic => w.publicData
  | .readPrivate => w.privateData
  | _ => []
def execute (w : World) (i : Intent) : Option Result :=
  (step w.state i.action).map (fun t => ⟨t,effectFor i,observationFor w i.action⟩)
def publicEvents : Effect → List Bytes
  | .publicWrite b => [b]
  | _ => []
def resultEvents : Option Result → List Bytes
  | some r => publicEvents r.effect
  | none => []
def nextWorld (w : World) : Option Result → World
  | some r => { w with state := r.next }
  | none => w

theorem execute_refines {w : World} {i : Intent} {r : Result}
    (h : execute w i = some r) :
    step w.state i.action = some r.next ∧ r.effect = effectFor i ∧
      r.observation = observationFor w i.action := by
  unfold execute at h
  cases hs : step w.state i.action with
  | none => simp [hs] at h
  | some t => simp [hs] at h; cases h; exact ⟨rfl,rfl,rfl⟩

theorem execute_forbidden {w : World} {i : Intent} {r : Result}
    (h : execute w i = some r) : forbidden i.action = false :=
  step_forbidden (execute_refines h).1

theorem execute_budget {w : World} {i : Intent} {r : Result}
    (h : execute w i = some r) : r.next.remaining + cost i.action = w.state.remaining :=
  step_budget (execute_refines h).1

theorem execute_exact_private {w : World} {i : Intent} {r : Result}
    (h : execute w i = some r) (ha : i.action = .writePrivate) :
    r.effect = .privateWrite i.payload := by
  rw [(execute_refines h).2.1]; simp [effectFor,ha]

theorem execute_exact_public {w : World} {i : Intent} {r : Result} {b : Bytes}
    (h : execute w i = some r) (he : r.effect = .publicWrite b) :
    b = i.payload ∧ (i.action = .publish ∨ i.action = .finish) := by
  rw [(execute_refines h).2.1] at he
  cases ha : i.action <;> simp [effectFor,ha] at he ⊢ <;> exact he.symm

theorem execute_private_read {w : World} {i : Intent} {r : Result}
    (h : execute w i = some r) (ha : i.action = .readPrivate) :
    r.next.tainted = true ∧ r.observation = w.privateData ∧ r.effect = .none := by
  have hs := (execute_refines h).1
  rw [ha] at hs
  exact ⟨step_private hs,by rw [(execute_refines h).2.2]; simp [observationFor,ha],
    by rw [(execute_refines h).2.1]; simp [effectFor,ha]⟩

theorem execute_tainted_no_public {w : World} {i : Intent}
    (ht : w.state.tainted = true) : resultEvents (execute w i) = [] := by
  cases h : execute w i with
  | none => rfl
  | some r =>
    have hn := step_no_public (execute_refines h).1 ht
    rw [resultEvents,(execute_refines h).2.1]
    cases ha : i.action <;> simp [ha,publicSink] at hn <;> simp [effectFor,ha,publicEvents]

theorem execute_taint_persists {w : World} {i : Intent}
    (ht : w.state.tainted = true) : (nextWorld w (execute w i)).state.tainted = true := by
  cases h : execute w i with
  | none => exact ht
  | some r => exact step_taint (execute_refines h).1 ht

theorem execute_secret_independent (s : State) (p h₁ h₂ : Bytes) (i : Intent)
    (ha : i.action ≠ .readPrivate) :
    execute ⟨s,p,h₁⟩ i = execute ⟨s,p,h₂⟩ i := by
  unfold execute
  congr 1
  funext t
  congr 1
  cases he : i.action <;> simp [he] at ha <;> simp [observationFor]

structure Controller (Memory : Type) where
  choose : Memory → Intent
  advance : Memory → Option Result → Memory

def drive {M : Type} (c : Controller M) : Nat → World → M → List Bytes
  | 0, _, _ => []
  | n+1, w, m =>
      let r := execute w (c.choose m)
      resultEvents r ++ drive c n (nextWorld w r) (c.advance m r)

theorem drive_tainted_empty {M : Type} (c : Controller M) (n : Nat) (w : World) (m : M)
    (ht : w.state.tainted = true) : drive c n w m = [] := by
  induction n generalizing w m with
  | zero => rfl
  | succ n ih =>
    simp only [drive,execute_tainted_no_public ht,List.nil_append]
    exact ih _ _ (execute_taint_persists ht)

theorem causal_public_noninterference {M : Type} (c : Controller M) (n : Nat)
    (s : State) (p h₁ h₂ : Bytes) (m : M) :
    drive c n ⟨s,p,h₁⟩ m = drive c n ⟨s,p,h₂⟩ m := by
  induction n generalizing s m with
  | zero => rfl
  | succ n ih =>
    by_cases ha : (c.choose m).action = .readPrivate
    · cases hs : step s (c.choose m).action with
      | none =>
        simp only [drive,execute,hs,Option.map_none,resultEvents,nextWorld,List.nil_append]
        exact ih s _
      | some t =>
        have ht : t.tainted = true := step_private (by simpa [ha] using hs)
        have he : effectFor (c.choose m) = .none := by simp [effectFor,ha]
        simp only [drive,execute,hs,Option.map_some,resultEvents,he,publicEvents,
          nextWorld,List.nil_append]
        rw [drive_tainted_empty c n _ _ ht,drive_tainted_empty c n _ _ ht]
    · have he := execute_secret_independent s p h₁ h₂ (c.choose m) ha
      simp only [drive]
      rw [he]
      cases hr : execute ⟨s,p,h₂⟩ (c.choose m) with
      | none => simp only [nextWorld]; exact congrArg (fun t => resultEvents none ++ t) (ih s _)
      | some r => simp only [nextWorld]; exact congrArg (fun t => resultEvents (some r) ++ t) (ih r.next _)

def runEffects : World → List Intent → Option (State × List Effect)
  | w, [] => some (w.state,[])
  | w, i :: rest => do
      let r ← execute w i
      let (s,es) ← runEffects {w with state := r.next} rest
      pure (s,r.effect :: es)

theorem runEffects_refines {w : World} {is : List Intent} {s : State} {es : List Effect}
    (h : runEffects w is = some (s,es)) : History w.state (is.map Intent.action) s := by
  induction is generalizing w es with
  | nil => simp only [runEffects,Option.some.injEq,Prod.mk.injEq] at h; rw [← h.1]; exact .nil _
  | cons i is ih =>
    cases hr : execute w i with
    | none => simp [runEffects,hr] at h
    | some r =>
      cases ht : runEffects {w with state := r.next} is with
      | none => simp [runEffects,hr,ht] at h
      | some pair =>
        obtain ⟨t,tail⟩ := pair
        simp [runEffects,hr,ht] at h
        obtain ⟨rfl,rfl⟩ := h
        exact .cons (execute_refines hr).1 (ih ht)

def leakyInitialController : Controller Bytes :=
  ⟨fun m => ⟨.publish,m⟩,fun m _ => m⟩
theorem untracked_initial_memory_counterexample :
    drive leakyInitialController 1 ⟨initial,[],[]⟩ [65] ≠
      drive leakyInitialController 1 ⟨initial,[],[]⟩ [66] := by decide

theorem private_feedback_can_distinguish_secrets :
    execute ⟨initial,[],[65]⟩ ⟨.readPrivate,[]⟩ ≠
      execute ⟨initial,[],[66]⟩ ⟨.readPrivate,[]⟩ := by decide

def field (b : Bytes) : Bytes :=
  UInt8.ofNat (b.length % 256) :: UInt8.ofNat (b.length / 256) :: b
def takeField : Bytes → Option (Bytes × Bytes)
  | lo :: hi :: rest =>
      let n := lo.toNat + 256 * hi.toNat
      if n ≤ 1024 ∧ n ≤ rest.length then some (rest.take n,rest.drop n) else none
  | _ => none

theorem field_roundtrip (b suffix : Bytes) (hb : b.length ≤ 1024) :
    takeField (field b ++ suffix) = some (b,suffix) := by
  have hl : b.length % 256 < 256 := Nat.mod_lt _ (by decide)
  have hh : b.length / 256 < 256 := by omega
  have hn : b.length % 256 + 256 * (b.length / 256) = b.length := Nat.mod_add_div _ _
  simp only [field,List.cons_append,takeField,UInt8.toNat_ofNat_of_lt' hl,
    UInt8.toNat_ofNat_of_lt' hh,hn]
  simp [hb,List.length_append]

def encodeRequest (w : World) (i : Intent) : Bytes :=
  2 :: (encode w.state i.action ++ field i.payload ++ field w.publicData ++ field w.privateData)
def decodeRequest : Bytes → Option (World × Intent)
  | 2 :: v :: g :: b :: t :: a :: rest => do
      let (s,action) ← decode [v,g,b,t,a]
      let (payload,rest) ← takeField rest
      let (publicData,rest) ← takeField rest
      let (privateData,rest) ← takeField rest
      if rest = [] then some (⟨s,publicData,privateData⟩,⟨action,payload⟩) else none
  | _ => none

theorem request_roundtrip (w : World) (i : Intent) (hv : Valid w.state)
    (hi : i.payload.length ≤ 1024) (hp : w.publicData.length ≤ 1024)
    (hh : w.privateData.length ≤ 1024) :
    decodeRequest (encodeRequest w i) = some (w,i) := by
  rcases w with ⟨s,p,h⟩
  rcases i with ⟨a,payload⟩
  have hd := decode_encode s a hv
  cases s with
  | mk generation remaining tainted =>
    simp only [encodeRequest,encode,List.cons_append,List.nil_append,decodeRequest]
    change (do
      let (s,act) ← decode (encode ⟨generation,remaining,tainted⟩ a)
      let (pl,rest) ← takeField (field payload ++ field p ++ field h)
      let (pu,rest) ← takeField rest
      let (pr,rest) ← takeField rest
      if rest = [] then some (World.mk s pu pr,Intent.mk act pl) else none) = _
    simp only [hd,List.append_assoc]
    rw [field_roundtrip payload (field p ++ field h) hi]
    have last := field_roundtrip h [] hh
    simp only [List.append_nil] at last
    simp [field_roundtrip p (field h) hp,last]

def effectTag : Effect → UInt8
  | .none => 0 | .privateWrite _ => 1 | .publicWrite _ => 2
def effectPayload : Effect → Bytes
  | .none => [] | .privateWrite b | .publicWrite b => b
def encodeResult (a : Action) (r : Result) : Bytes :=
  [2,1,UInt8.ofNat r.next.generation,UInt8.ofNat r.next.remaining,
    if r.next.tainted then 1 else 0,actionByte a,effectTag r.effect] ++
    field (effectPayload r.effect) ++ field r.observation
def denied (w : World) (i : Intent) : Bytes :=
  [2,0,UInt8.ofNat w.state.generation,UInt8.ofNat w.state.remaining,
    if w.state.tainted then 1 else 0,actionByte i.action,0,0,0,0,0]
def process (raw : Bytes) : Bytes :=
  match decodeRequest raw with
  | none => [2,2,0,0,0,0,0,0,0,0,0]
  | some (w,i) => match execute w i with
      | none => denied w i
      | some r => encodeResult i.action r

theorem malformed_request_refuses (raw : Bytes) (h : decodeRequest raw = none) :
    process raw = [2,2,0,0,0,0,0,0,0,0,0] := by simp [process,h]

theorem wire_effect_sound (raw : Bytes) (h : (process raw).getD 1 2 = 1) :
    ∃ w i r, decodeRequest raw = some (w,i) ∧ execute w i = some r ∧
      process raw = encodeResult i.action r := by
  cases hd : decodeRequest raw with
  | none => simp [process,hd] at h
  | some pair =>
    obtain ⟨w,i⟩ := pair
    cases he : execute w i with
    | none => simp [process,hd,he,denied] at h
    | some r => exact ⟨w,i,r,rfl,he,by simp [process,hd,he]⟩

theorem wire_public_payload_bound (raw : Bytes) (h : (process raw).getD 1 2 = 1)
    (hp : (process raw).getD 6 0 = 2) :
    ∃ w i r, decodeRequest raw = some (w,i) ∧ execute w i = some r ∧
      r.effect = .publicWrite i.payload ∧ w.state.tainted = false := by
  obtain ⟨w,i,r,hd,he,hr⟩ := wire_effect_sound raw h
  rw [hr] at hp
  have hh : effectTag r.effect = 2 := by simpa [encodeResult] using hp
  cases hef : r.effect with
  | none => simp [hef,effectTag] at hh
  | privateWrite b => simp [hef,effectTag] at hh
  | publicWrite b =>
    obtain ⟨hb,ha⟩ := execute_exact_public he hef
    refine ⟨w,i,r,hd,he,?_,?_⟩
    · simpa [hb] using hef
    · rcases (step_facts (execute_refines he).1).2.2.2.2.1 with hn | ht
      · rcases ha with ha | ha <;> simp [ha,publicSink] at hn
      · exact ht

end PCSCausalFirewall
