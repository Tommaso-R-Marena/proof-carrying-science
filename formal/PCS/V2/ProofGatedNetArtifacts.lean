import PCS.V2.ProofGatedCodec
import PCS.V2.ProofGatedWide

/-!
# Versioned canonical artifacts, promotion and inference for width-`n` networks

Wire format (`PGSI2-WIDE`), one exact string per model:

  `PGSI2-WIDE|outBias|w₁|b₁|o₁|w₂|b₂|o₂|…`

with every integer in the verified canonical decimal form of `ProofGatedCodec`.

Refinement chain proved here, for **every** architecture bound, target and corpus:

1. *serialized model* ↔ *mathematical parameters*:
   `decode_encode` (roundtrip for every valid network of any width),
   `decode_iff` (the decoder accepts a string **iff** it is the canonical encoding of
   a valid network), `encode_injective`;
2. *parameters* ↔ *evaluation*: `infer_encode` (`∀ x : Int`);
3. *checker decision*: `acceptWire_encode` (on canonical artifacts the wire gate makes
   exactly the model gate's decision) and `acceptWire_iff`;
4. *exact-identity generation commit*: `commit_refines` binds the committed text to the
   same decoded network whose predictions are subsequently served, and
   `commit_complete` shows every admissible canonical proposal against the current
   generation does commit;
5. *arbitrary commit sequences*: `runCommits_invariant` — for any list of proposals
   (stale, forged, adversarial or genuine), the number of successful commits plus the
   final loss is bounded by the initial loss, and every initially correct corpus
   prediction is still served correctly.

Out of scope (ordinary host assumptions, *not* proved): file-system atomicity, hash
collision resistance, signatures, rollback protection, and the faithfulness of any
external runtime that executes the served model.
-/

namespace PCS.V2.ProofGatedNetArtifacts

open PCS.V2.ProofGatedCodec
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedGeneric

def tag : List Char := "PGSI2-WIDE".toList

theorem tag_pipe_free : '|' ∉ tag := by decide +kernel

def toInts (m : WideNet) : List Int :=
  m.outBias :: m.hidden.flatMap fun u => [u.w, u.b, u.out]

def unitsOfInts : List Int → Option (List HiddenUnit)
  | [] => some []
  | w :: b :: o :: rest => (unitsOfInts rest).map (⟨w, b, o⟩ :: ·)
  | _ => none

def ofInts : List Int → Option WideNet
  | [] => none
  | ob :: rest => (unitsOfInts rest).map fun hs => ⟨hs, ob⟩

theorem unitsOfInts_flatMap (hs : List HiddenUnit) :
    unitsOfInts (hs.flatMap fun u => [u.w, u.b, u.out]) = some hs := by
  induction hs with
  | nil => rfl
  | cons u us ih => simp [unitsOfInts, ih]

theorem ofInts_toInts (m : WideNet) : ofInts (toInts m) = some m := by
  simp [toInts, ofInts, unitsOfInts_flatMap]

theorem unitsOfInts_inv {zs : List Int} {hs : List HiddenUnit}
    (h : unitsOfInts zs = some hs) : hs.flatMap (fun u => [u.w, u.b, u.out]) = zs := by
  induction zs using unitsOfInts.induct generalizing hs with
  | case1 => simp [unitsOfInts] at h; subst h; rfl
  | case2 w b o rest ih =>
      simp only [unitsOfInts] at h
      cases hr : unitsOfInts rest with
      | none => simp [hr] at h
      | some us =>
          simp [hr] at h
          subst h
          simp [ih hr]
  | case3 zs h1 h2 =>
      cases zs with
      | nil => exact absurd rfl h1
      | cons a t =>
          cases t with
          | nil => simp [unitsOfInts] at h
          | cons b t =>
              cases t with
              | nil => simp [unitsOfInts] at h
              | cons c t => exact absurd rfl (h2 a b c t)

theorem toInts_of_ofInts {zs : List Int} {m : WideNet} (h : ofInts zs = some m) :
    toInts m = zs := by
  cases zs with
  | nil => simp [ofInts] at h
  | cons ob rest =>
      simp only [ofInts] at h
      cases hr : unitsOfInts rest with
      | none => simp [hr] at h
      | some hs =>
          simp [hr] at h
          subst h
          simp [toInts, unitsOfInts_inv hr]

/-! ## Codec -/

def encodeChars (m : WideNet) : List Char := encodeInts tag (toInts m)

def encode (m : WideNet) : String := String.ofList (encodeChars m)

/-- Architecture-agnostic parse (no validity check). -/
def parseModel (raw : String) : Option WideNet := (decodeInts tag raw.toList).bind ofInts

/-- The authoritative decoder: parse, then enforce the versioned architecture bound. -/
def decode (A : Arch) (raw : String) : Option WideNet :=
  match parseModel raw with
  | some m => if valid A m then some m else none
  | none => none

theorem parseModel_encode (m : WideNet) : parseModel (encode m) = some m := by
  simp [parseModel, encode, encodeChars, String.toList_ofList,
    decodeInts_encodeInts tag tag_pipe_free, ofInts_toInts]

theorem parseModel_canonical {raw : String} {m : WideNet} (h : parseModel raw = some m) :
    encode m = raw := by
  unfold parseModel at h
  cases hd : decodeInts tag raw.toList with
  | none => simp [hd] at h
  | some zs =>
      simp only [hd, Option.bind_some] at h
      have h1 := decodeInts_canonical hd
      rw [← toInts_of_ofInts h] at h1
      unfold encode encodeChars
      rw [h1, String.ofList_toList]

/-- **Roundtrip for every valid network of every admissible width.** -/
theorem decode_encode (A : Arch) (m : WideNet) (h : valid A m = true) :
    decode A (encode m) = some m := by
  simp [decode, parseModel_encode, h]

/-- **Exact acceptance characterisation** of the decoder. -/
theorem decode_iff (A : Arch) (raw : String) (m : WideNet) :
    decode A raw = some m ↔ valid A m = true ∧ encode m = raw := by
  constructor
  · intro h
    unfold decode at h
    cases hp : parseModel raw with
    | none => simp [hp] at h
    | some m' =>
        by_cases hv : valid A m' = true
        · simp [hp, hv] at h
          subst h
          exact ⟨hv, parseModel_canonical hp⟩
        · simp [hp, hv] at h
  · rintro ⟨hv, rfl⟩
    exact decode_encode A m hv

theorem decode_canonical {A : Arch} {raw : String} {m : WideNet}
    (h : decode A raw = some m) : encode m = raw := ((decode_iff A raw m).mp h).2

theorem decode_valid {A : Arch} {raw : String} {m : WideNet}
    (h : decode A raw = some m) : valid A m = true := ((decode_iff A raw m).mp h).1

/-- `encode` is injective on **all** networks (validity is not needed). -/
theorem encode_injective {m₁ m₂ : WideNet} (h : encode m₁ = encode m₂) : m₁ = m₂ := by
  have h1 := parseModel_encode m₁
  rw [h, parseModel_encode] at h1
  exact (Option.some.inj h1).symm

/-- Any string that is not the canonical encoding of a valid network is rejected. -/
theorem decode_rejects (A : Arch) (raw : String)
    (h : ∀ m, valid A m = true → encode m ≠ raw) : decode A raw = none := by
  cases hd : decode A raw with
  | none => rfl
  | some m =>
      obtain ⟨hv, he⟩ := (decode_iff A raw m).mp hd
      exact absurd he (h m hv)

/-! ## Inference -/

def infer (A : Arch) (raw : String) (x : Int) : Option Int :=
  (decode A raw).map fun m => predict m x

theorem infer_encode (A : Arch) (m : WideNet) (h : valid A m = true) (x : Int) :
    infer A (encode m) x = some (predict m x) := by
  simp [infer, decode_encode A m h]

theorem infer_sound {A : Arch} {raw : String} {x y : Int} (h : infer A raw x = some y) :
    ∃ m, valid A m = true ∧ encode m = raw ∧ predict m x = y := by
  unfold infer at h
  cases hd : decode A raw with
  | none => simp [hd] at h
  | some m =>
      simp [hd] at h
      exact ⟨m, decode_valid hd, decode_canonical hd, h⟩

/-- Inference is invariant under semantics-preserving re-encodings: two valid artifacts
whose networks compute the same function serve the same predictions. -/
theorem infer_congr {A : Arch} {m m' : WideNet} (hv : valid A m = true)
    (hv' : valid A m' = true) (h : ∀ x, predict m x = predict m' x) (x : Int) :
    infer A (encode m) x = infer A (encode m') x := by
  rw [infer_encode A m hv, infer_encode A m' hv', h]

/-! ## Wire gate -/

structure Config where
  arch : Arch
  target : Int → Int
  corpus : List Int

def Config.spec (c : Config) : GateSpec WideNet := wideSpec c.arch c.target c.corpus

def acceptWire (c : Config) (oldRaw newRaw : String) : Bool :=
  match decode c.arch oldRaw, decode c.arch newRaw with
  | some o, some n => accept c.spec o n
  | _, _ => false

theorem acceptWire_iff (c : Config) (oldRaw newRaw : String) :
    acceptWire c oldRaw newRaw = true ↔
      ∃ o n, encode o = oldRaw ∧ encode n = newRaw ∧ admissible c.spec o n := by
  constructor
  · intro h
    unfold acceptWire at h
    cases ho : decode c.arch oldRaw with
    | none => simp [ho] at h
    | some o =>
        cases hn : decode c.arch newRaw with
        | none => simp [ho, hn] at h
        | some n =>
            simp only [ho, hn] at h
            exact ⟨o, n, decode_canonical ho, decode_canonical hn, accept_sound h⟩
  · rintro ⟨o, n, rfl, rfl, hadm⟩
    have hvo : valid c.arch o = true := hadm.1
    have hvn : valid c.arch n = true := hadm.2.1
    simp [acceptWire, decode_encode _ _ hvo, decode_encode _ _ hvn, accept_complete hadm]

/-- On canonical artifacts of valid networks the wire gate **is** the model gate. -/
theorem acceptWire_encode (c : Config) (o n : WideNet) (ho : valid c.arch o = true)
    (hn : valid c.arch n = true) :
    acceptWire c (encode o) (encode n) = accept c.spec o n := by
  simp [acceptWire, decode_encode _ _ ho, decode_encode _ _ hn]

/-! ## Exact-identity compare-and-swap promotion -/

structure State where
  generation : Nat
  active : String
  deriving Repr, DecidableEq

structure Proposal where
  expectedGeneration : Nat
  expectedActive : String
  candidate : String
  deriving Repr, DecidableEq

def tryCommit (c : Config) (s : State) (p : Proposal) : Option State :=
  if p.expectedGeneration = s.generation ∧ p.expectedActive = s.active ∧
      acceptWire c s.active p.candidate = true then
    some ⟨s.generation + 1, p.candidate⟩
  else none

/-- **End-to-end refinement of a successful commit**: the old and new active texts are
the canonical encodings of valid networks `old`, `cand`; the step is admissible; the
generation advanced by one; the new artifact serves exactly `predict cand` on every
integer; and every corpus point served correctly before is served correctly after. -/
theorem commit_refines {c : Config} {s s' : State} {p : Proposal}
    (h : tryCommit c s p = some s') :
    ∃ old cand : WideNet,
      encode old = s.active ∧ encode cand = s'.active ∧
      decode c.arch s.active = some old ∧ decode c.arch s'.active = some cand ∧
      admissible c.spec old cand ∧
      s'.generation = s.generation + 1 ∧
      p.expectedGeneration = s.generation ∧ p.expectedActive = s.active ∧
      (∀ x : Int, infer c.arch s'.active x = some (predict cand x)) ∧
      (∀ x ∈ c.corpus, infer c.arch s.active x = some (c.target x) →
        infer c.arch s'.active x = some (c.target x)) := by
  unfold tryCommit at h
  by_cases hc : p.expectedGeneration = s.generation ∧ p.expectedActive = s.active ∧
      acceptWire c s.active p.candidate = true
  · rw [if_pos hc] at h
    cases h
    obtain ⟨hg, ha, hw⟩ := hc
    obtain ⟨old, cand, ho, hn, hadm⟩ := (acceptWire_iff c _ _).mp hw
    have hvo : valid c.arch old = true := hadm.1
    have hvn : valid c.arch cand = true := hadm.2.1
    refine ⟨old, cand, ho, hn, ho ▸ decode_encode _ _ hvo, hn ▸ decode_encode _ _ hvn,
      hadm, rfl, hg, ha, ?_, ?_⟩
    · intro x
      show infer c.arch p.candidate x = _
      rw [← hn]; exact infer_encode _ _ hvn x
    · intro x hx hold
      show infer c.arch p.candidate x = _
      rw [← ho, infer_encode _ _ hvo] at hold
      have hcorr : correct c.spec old x := Option.some.inj hold
      have := hadm.2.2.1 x hx hcorr
      rw [← hn, infer_encode _ _ hvn]
      exact congrArg some this
  · rw [if_neg hc] at h; cases h

/-- **Commit completeness**: an admissible canonical proposal made against the current
generation and active text is always committed. -/
theorem commit_complete (c : Config) (s : State) (old cand : WideNet)
    (hs : s.active = encode old) (hadm : admissible c.spec old cand) :
    tryCommit c s ⟨s.generation, s.active, encode cand⟩ =
      some ⟨s.generation + 1, encode cand⟩ := by
  have hw : acceptWire c s.active (encode cand) = true :=
    (acceptWire_iff c _ _).mpr ⟨old, cand, hs.symm, rfl, hadm⟩
  simp [tryCommit, hw]

theorem stale_generation_rejected (c : Config) (s : State) (p : Proposal)
    (h : p.expectedGeneration ≠ s.generation) : tryCommit c s p = none := by
  simp [tryCommit, h]

theorem substituted_active_rejected (c : Config) (s : State) (p : Proposal)
    (h : p.expectedActive ≠ s.active) : tryCommit c s p = none := by
  simp [tryCommit, h]

def gatedCommit (c : Config) (s : State) (p : Proposal) : State := (tryCommit c s p).getD s

def runCommits (c : Config) : State → List Proposal → State
  | s, [] => s
  | s, p :: ps => runCommits c (gatedCommit c s p) ps

/-- **Arbitrary commit sequences** (any proposals: stale, forged, adversarial or
genuine). Starting from a decodable active artifact, the final active artifact decodes
to a network `m` that keeps every originally correct corpus prediction, and the number
of successful commits (= generations gained) plus `loss m` is at most the initial loss. -/
theorem runCommits_invariant (c : Config) (ps : List Proposal) (s : State) (m₀ : WideNet)
    (h₀ : decode c.arch s.active = some m₀) :
    ∃ m, decode c.arch (runCommits c s ps).active = some m ∧
      s.generation ≤ (runCommits c s ps).generation ∧
      ((runCommits c s ps).generation - s.generation) + loss c.spec m ≤ loss c.spec m₀ ∧
      (∀ x ∈ c.corpus, correct c.spec m₀ x → correct c.spec m x) := by
  induction ps generalizing s m₀ with
  | nil => exact ⟨m₀, h₀, Nat.le_refl _, by simp [runCommits], fun _ _ h => h⟩
  | cons p ps ih =>
      simp only [runCommits]
      cases hc : tryCommit c s p with
      | none =>
          have : gatedCommit c s p = s := by simp [gatedCommit, hc]
          rw [this]
          exact ih s m₀ h₀
      | some s' =>
          have hg : gatedCommit c s p = s' := by simp [gatedCommit, hc]
          rw [hg]
          obtain ⟨old, cand, _, _, hdo, hdn, hadm, hgen, _⟩ := commit_refines hc
          rw [h₀] at hdo
          cases hdo
          obtain ⟨m, hm, hle, hbound, hpres⟩ := ih s' cand hdn
          refine ⟨m, hm, by omega, ?_, fun x hx hcx => hpres x hx (hadm.2.2.1 x hx hcx)⟩
          have := hadm.2.2.2.2
          omega

/-! ## Executable fixtures -/

/-- The concrete text of the perfect three-unit network. -/
theorem gen3_wire : encode gen3 = "PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2" := by decide +kernel

def cfg3 : Config := ⟨arch3, target3, corpus9⟩

theorem cfg3_spec : cfg3.spec = spec3 := rfl

/-- Three successive *string-level* commits growing the network 0 → 1 → 2 → 3 units,
derived from the model-level certificates via `commit_complete` (no string evaluation). -/
theorem three_commits :
    runCommits cfg3 ⟨0, encode gen0⟩
      [⟨0, encode gen0, encode gen1⟩, ⟨1, encode gen1, encode gen2⟩,
       ⟨2, encode gen2, encode gen3⟩] = ⟨3, encode gen3⟩ := by
  have a1 := commit_complete cfg3 ⟨0, encode gen0⟩ gen0 gen1 rfl (accept_sound wide_step1)
  have a2 := commit_complete cfg3 ⟨1, encode gen1⟩ gen1 gen2 rfl (accept_sound wide_step2)
  have a3 := commit_complete cfg3 ⟨2, encode gen2⟩ gen2 gen3 rfl (accept_sound wide_step3)
  simp only [runCommits, gatedCommit]
  rw [a1]; simp only [Option.getD_some]
  rw [a2]; simp only [Option.getD_some]
  rw [a3]; simp only [Option.getD_some]

theorem served_after_three_commits (x : Int) :
    infer arch3 (encode gen3) x = some (target3 x) := by
  rw [infer_encode arch3 gen3 (by decide), gen3_exact]

/-- A stale replay of the first proposal after the chain is rejected. -/
theorem replay_rejected :
    tryCommit cfg3 ⟨3, encode gen3⟩ ⟨0, encode gen0, encode gen1⟩ = none :=
  stale_generation_rejected _ _ _ (by decide)

/-- Boundary behaviour of the decoder on literal wire strings. -/
theorem boundary_fixtures :
    (decode arch3 "PGSI2-WIDE|32|-32|32|-32").isSome = true ∧
    decode arch3 "PGSI2-WIDE|33" = none ∧
    decode arch3 "PGSI2-WIDE|0|-33|0|0" = none ∧
    decode arch3 "PGSI2-WIDE|007" = none ∧
    decode arch3 "PGSI2-WIDE|-0" = none ∧
    decode arch3 "PGSI2-WIDE|0|1|2" = none ∧
    decode arch3 "PGSI1-WIDE|0" = none ∧
    decode arch3 "PGSI2-WIDE|0|" = none := by
  decide +kernel

end PCS.V2.ProofGatedNetArtifacts
