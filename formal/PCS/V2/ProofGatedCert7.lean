import PCS.V2.ProofGatedCertCodec
import PCS.V2.ProofGatedSweepCert

/-!
# PGSC7: certificates with a sweep witness for no-forgetting and the error bound

PGSC7 is a **new wire format with a new version tag**; PGSC6 (`ProofGatedCertificate`,
`ProofGatedCertCodec`) is unchanged and still accepted by its own checker.

A PGSC7 certificate (`Cert7`) is a PGSC6 record (`base`, whose `version` field must be `7`)
together with a sweep witness `order` (`ProofGatedSweepCert.NFCert`). Its checker
`checkCert7` differs from `checkCert` in requirement B and C:

* **B (no-forgetting on every integer)** and **C (candidate error ≤ `errLevel` on
  `[lo,hi]`)** are decided together by the evaluation-free sweep `checkBoth` on the
  witness. V6 re-ran the exact `noForgetting` search (≥ `9N + 3` network-pair evaluations)
  and `checkErrBound` (a probe set of size ≥ `3N`, each a network evaluation);
* A (corpus gain witness and losses) and the incumbent's level witness are as in PGSC6.

Results:
* `checkCert7_sound` / `checkCert7_complete` / `checkCert7_iff_gate`;
* `checker_substitution_equiv`: for every configuration, generation, active artifact and
  candidate, PGSC7 admits a certificate iff PGSC6 does. Replacing the checker therefore does
  not change the set of admitted transitions;
* `decodeCert7_iff`: canonical byte format `PGSC7|…`, accepted exactly on canonical
  encodings; PGSC6 bytes are never PGSC7 bytes (`pgsc6_not_pgsc7`), and conversely.
-/

namespace PCS.V2.ProofGatedCert7

open PCS.V2.ProofGatedCodec
open PCS.V2.ProofGatedGeneric
open PCS.V2.ProofGatedWide
open PCS.V2.ProofGatedNoForget
open PCS.V2.ProofGatedRobust
open PCS.V2.ProofGatedStrongGate
open PCS.V2.ProofGatedBytes
open PCS.V2.ProofGatedCertificate
open PCS.V2.ProofGatedCertCodec
open PCS.V2.ProofGatedSweepCert

def cert7Version : Nat := 7

structure Cert7 where
  base : Cert
  order : List TU
  deriving Repr, DecidableEq

def HeaderOK7 (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert7) : Prop :=
  c.base.version = cert7Version ∧ c.base.predicate = predStrongABC ∧ configMatches S c.base ∧
    c.base.generation = g ∧ c.base.incumbent = active

instance (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert7) :
    Decidable (HeaderOK7 S g active c) := by
  unfold HeaderOK7; infer_instance

/-- Witness conditions: A as in PGSC6, the incumbent's level witness, and the sweep. -/
def WitnessOK7 (S : StrongSpec) (c : Cert7) (o n : WideNet) : Prop :=
  c.base.gainWitness ∈ S.corpus ∧
  predict o c.base.gainWitness ≠ predict S.target c.base.gainWitness ∧
  predict n c.base.gainWitness = predict S.target c.base.gainWitness ∧
  loss S.corpusSpec o = c.base.incLoss ∧ loss S.corpusSpec n = c.base.candLoss ∧
  c.base.candLoss < c.base.incLoss ∧
  (S.lo ≤ S.hi →
    S.lo ≤ c.base.errWitness ∧ c.base.errWitness ≤ S.hi ∧
    errAt o S.target c.base.errWitness = c.base.errLevel) ∧
  checkBoth o n S.target S.lo S.hi c.base.errLevel ⟨c.order⟩ = true

instance (S : StrongSpec) (c : Cert7) (o n : WideNet) : Decidable (WitnessOK7 S c o n) := by
  unfold WitnessOK7; infer_instance

/-- **The PGSC7 checker.** -/
def checkCert7 (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert7) : Bool :=
  decide (HeaderOK7 S g active c) &&
    match decodeBytes S.arch c.base.incumbent, decodeBytes S.arch c.base.candidate with
    | some o, some n => decide (WitnessOK7 S c o n)
    | _, _ => false

theorem witnessOK7_sound {S : StrongSpec} {c : Cert7} {o n : WideNet}
    (hvo : valid S.arch o = true) (hvn : valid S.arch n = true) (h : WitnessOK7 S c o n) :
    StrongAdmissible S o n := by
  obtain ⟨hg, hgo, hgn, hlo, hln, hlt, hC, hboth⟩ := h
  obtain ⟨hB, hE⟩ := checkBoth_sound hboth
  refine ⟨⟨hvo, hvn, fun x _ hx => hB x hx, ⟨c.base.gainWitness, hg, hgo, hgn⟩, by omega⟩, hB, ?_⟩
  intro B hBo x hx1 hx2
  have hLU : S.lo ≤ S.hi := by omega
  obtain ⟨hw1, hw2, hwe⟩ := hC hLU
  have hlev : c.base.errLevel ≤ B := hwe ▸ hBo c.base.errWitness hw1 hw2
  exact Nat.le_trans (hE x hx1 hx2) hlev

/-- **Soundness of PGSC7.** -/
theorem checkCert7_sound {S : StrongSpec} {g : Nat} {active : Bytes} {c : Cert7}
    (h : checkCert7 S g active c = true) :
    HeaderOK7 S g active c ∧
    ∃ o n, decodeBytes S.arch active = some o ∧ decodeBytes S.arch c.base.candidate = some n ∧
      encodeBytes o = active ∧ encodeBytes n = c.base.candidate ∧ StrongAdmissible S o n := by
  unfold checkCert7 at h
  simp only [Bool.and_eq_true, decide_eq_true_eq] at h
  obtain ⟨hH, h⟩ := h
  refine ⟨hH, ?_⟩
  cases ho : decodeBytes S.arch c.base.incumbent with
  | none => simp [ho] at h
  | some o =>
    cases hn : decodeBytes S.arch c.base.candidate with
    | none => simp [ho, hn] at h
    | some n =>
      simp only [ho, hn, decide_eq_true_eq] at h
      have hinc : c.base.incumbent = active := hH.2.2.2.2
      refine ⟨o, n, hinc ▸ ho, rfl, ?_, decodeBytes_canonical hn,
        witnessOK7_sound (decodeBytes_valid ho) (decodeBytes_valid hn) h⟩
      rw [← hinc]; exact decodeBytes_canonical ho

/-- The (untrusted) PGSC7 generator. -/
def genCert7 (S : StrongSpec) (g : Nat) (o n : WideNet) : Cert7 :=
  ⟨{ genCert S g o n with version := cert7Version }, (genNF o n S.target).order⟩

/-- **Completeness of PGSC7.** -/
theorem checkCert7_complete (S : StrongSpec) (g : Nat) (o n : WideNet)
    (h : StrongAdmissible S o n) :
    checkCert7 S g (encodeBytes o) (genCert7 S g o n) = true := by
  obtain ⟨⟨hvo, hvn, _, hgain, hloss⟩, hB, hC⟩ := h
  have hvo' : valid S.arch o = true := hvo
  have hvn' : valid S.arch n = true := hvn
  unfold checkCert7
  simp only [Bool.and_eq_true, decide_eq_true_eq]
  refine ⟨⟨rfl, rfl, ⟨rfl, rfl, rfl, rfl, rfl, rfl⟩, rfl, rfl⟩, ?_⟩
  simp only [genCert7, genCert, decodeBytes_encodeBytes _ _ hvo', decodeBytes_encodeBytes _ _ hvn',
    decide_eq_true_eq]
  obtain ⟨hg1, hg2, hg3⟩ := findGain_spec S o n hgain
  refine ⟨hg1, hg2, hg3, rfl, rfl, hloss, ?_, ?_⟩
  · intro hLU
    obtain ⟨h1, h2, h3⟩ := findErrArgmax_spec S o hLU
    exact ⟨h1, h2, h3⟩
  · apply checkBoth_complete _ _ _ _ _ _ hB
    intro x hx1 hx2
    exact hC _ ((maxAbsErr_le_iff o S.target S.lo S.hi _).mp (Nat.le_refl _)) x hx1 hx2

/-- **Checker/gate agreement for PGSC7.** -/
theorem checkCert7_iff_gate (S : StrongSpec) (g : Nat) (active cand : Bytes) :
    (∃ c, checkCert7 S g active c = true ∧ c.base.candidate = cand) ↔
      ∃ o n, decodeBytes S.arch active = some o ∧ decodeBytes S.arch cand = some n ∧
        StrongAdmissible S o n := by
  constructor
  · rintro ⟨c, hc, rfl⟩
    obtain ⟨_, o, n, ho, hn, -, -, hadm⟩ := checkCert7_sound hc
    exact ⟨o, n, ho, hn, hadm⟩
  · rintro ⟨o, n, ho, hn, hadm⟩
    refine ⟨genCert7 S g o n, ?_, decodeBytes_canonical hn⟩
    rw [← decodeBytes_canonical ho]
    exact checkCert7_complete S g o n hadm

/-- **Checker substitution preserves the admitted transitions**: PGSC7 admits a
certificate for `(active ↦ cand)` iff PGSC6 does. -/
theorem checker_substitution_equiv (S : StrongSpec) (g : Nat) (active cand : Bytes) :
    (∃ c, checkCert7 S g active c = true ∧ c.base.candidate = cand) ↔
      (∃ c, checkCert S g active c = true ∧ c.candidate = cand) := by
  rw [checkCert7_iff_gate, checkCert_iff_gate]

/-! ## Binding rejections -/

theorem checkCert7_header {S : StrongSpec} {g : Nat} {active : Bytes} {c : Cert7}
    (h : ¬ HeaderOK7 S g active c) : checkCert7 S g active c = false := by
  simp [checkCert7, h]

theorem checkCert7_stale_rejected (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert7)
    (h : c.base.generation ≠ g) : checkCert7 S g active c = false :=
  checkCert7_header fun hH => h hH.2.2.2.1

theorem checkCert7_substituted_rejected (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert7)
    (h : c.base.incumbent ≠ active) : checkCert7 S g active c = false :=
  checkCert7_header fun hH => h hH.2.2.2.2

theorem checkCert7_config_rejected (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert7)
    (h : ¬ configMatches S c.base) : checkCert7 S g active c = false :=
  checkCert7_header fun hH => h hH.2.2.1

/-- A PGSC6 record (version `6`) is never accepted by the PGSC7 checker. -/
theorem checkCert7_version6_rejected (S : StrongSpec) (g : Nat) (active : Bytes) (c : Cert7)
    (h : c.base.version = certVersion) : checkCert7 S g active c = false :=
  checkCert7_header fun hH => by
    have h1 := hH.1; rw [h] at h1; exact absurd h1 (by decide)

/-! ## Canonical byte format `PGSC7|…` -/

def cert7Tag : List Char := "PGSC7".toList

theorem cert7Tag_pipe_free : '|' ∉ cert7Tag := by decide

theorem cert7Tag_ascii : AsciiChars cert7Tag := by
  intro c hc; revert c; decide

def tuInts (v : TU) : List Int := [v.u.w, v.u.b, v.u.out, v.cF, v.cG]

def orderInts (l : List TU) : List Int := l.flatMap tuInts

def tusOfInts : List Int → Option (List TU)
  | [] => some []
  | w :: b :: o :: f :: g :: rest => (tusOfInts rest).map (fun l => ⟨⟨w, b, o⟩, f, g⟩ :: l)
  | _ => none

theorem tusOfInts_orderInts (l : List TU) : tusOfInts (orderInts l) = some l := by
  induction l with
  | nil => rfl
  | cons v vs ih => simp [orderInts, tuInts, tusOfInts] at ih ⊢; simp [ih]

def cert7ToInts (c : Cert7) : List Int := block (orderInts c.order) ++ certToInts c.base

def parseCert7 (zs : List Int) : Option Cert7 := do
  let (oi, rest) ← takeBlock zs
  let order ← tusOfInts oi
  let base ← parseCert rest
  some ⟨base, order⟩

theorem parseCert7_cert7ToInts (c : Cert7) : parseCert7 (cert7ToInts c) = some c := by
  simp [parseCert7, cert7ToInts, takeBlock_block, tusOfInts_orderInts, parseCert_certToInts]

def encodeCert7 (c : Cert7) : Bytes := (encodeInts cert7Tag (cert7ToInts c)).map charToByte

def parseCert7Bytes (bs : Bytes) : Option Cert7 :=
  if bs.all isAsciiByte then (decodeInts cert7Tag (bs.map byteToChar)).bind parseCert7 else none

/-- **The PGSC7 decoder**: parse, then require the canonical encoding. -/
def decodeCert7 (bs : Bytes) : Option Cert7 :=
  match parseCert7Bytes bs with
  | some c => if encodeCert7 c = bs then some c else none
  | none => none

theorem decodeCert7_encodeCert7 (c : Cert7) : decodeCert7 (encodeCert7 c) = some c := by
  have ha := asciiChars_encodeInts cert7Tag cert7Tag_ascii (cert7ToInts c)
  have hp : parseCert7Bytes (encodeCert7 c) = some c := by
    unfold parseCert7Bytes encodeCert7
    rw [if_pos (all_ascii_map_charToByte _ ha), map_byteToChar_charToByte _ ha,
      decodeInts_encodeInts cert7Tag cert7Tag_pipe_free, Option.bind_some, parseCert7_cert7ToInts]
  simp [decodeCert7, hp]

theorem decodeCert7_iff (bs : Bytes) (c : Cert7) : decodeCert7 bs = some c ↔ encodeCert7 c = bs := by
  constructor
  · intro h
    unfold decodeCert7 at h
    cases hp : parseCert7Bytes bs with
    | none => simp [hp] at h
    | some c' =>
      by_cases he : encodeCert7 c' = bs
      · simp [hp, he] at h; subst h; exact he
      · simp [hp, he] at h
  · rintro rfl; exact decodeCert7_encodeCert7 c

theorem encodeCert7_injective {c₁ c₂ : Cert7} (h : encodeCert7 c₁ = encodeCert7 c₂) : c₁ = c₂ := by
  have := decodeCert7_encodeCert7 c₁
  rw [h, decodeCert7_encodeCert7] at this
  exact (Option.some.inj this).symm

/-- The first five bytes of every PGSC6 / PGSC7 encoding are the tag. -/
theorem encodeCert_prefix (c : Cert) : (encodeCert c).take 6 = ascii "PGSC6|" := by
  simp only [encodeCert, encodeCertChars, encodeInts, certTag]
  rfl

theorem encodeCert7_prefix (c : Cert7) : (encodeCert7 c).take 6 = ascii "PGSC7|" := by
  simp only [encodeCert7, encodeInts, cert7Tag]
  rfl

/-- **Version separation**: no byte string is both a PGSC6 and a PGSC7 certificate. -/
theorem pgsc6_not_pgsc7 (c : Cert) (c' : Cert7) : encodeCert c ≠ encodeCert7 c' := by
  intro h
  have h1 := encodeCert_prefix c
  rw [h, encodeCert7_prefix] at h1
  exact absurd h1 (by decide)

theorem decodeCert7_of_pgsc6 (c : Cert) : decodeCert7 (encodeCert c) = none := by
  cases h : decodeCert7 (encodeCert c) with
  | none => rfl
  | some c' => exact absurd ((decodeCert7_iff _ c').mp h).symm (pgsc6_not_pgsc7 c c')

theorem decodeCert_of_pgsc7 (c : Cert7) : decodeCert (encodeCert7 c) = none := by
  cases h : decodeCert (encodeCert7 c) with
  | none => rfl
  | some c' => exact absurd ((decodeCert_iff _ c').mp h) (pgsc6_not_pgsc7 c' c)

/-- Byte-level PGSC7 checker. -/
def checkCert7Bytes (S : StrongSpec) (g : Nat) (active : Bytes) (cb : Bytes) : Bool :=
  match decodeCert7 cb with
  | some c => checkCert7 S g active c
  | none => false

theorem checkCert7Bytes_complete (S : StrongSpec) (g : Nat) (o n : WideNet)
    (h : StrongAdmissible S o n) :
    checkCert7Bytes S g (encodeBytes o) (encodeCert7 (genCert7 S g o n)) = true := by
  simp only [checkCert7Bytes, decodeCert7_encodeCert7]
  exact checkCert7_complete S g o n h

/-! ## Fixtures -/

/-- The PGSC7 certificate for the first step `gen0 ↦ r1` of the robust chain on
`[-10^9, 10^9]`. -/
def cert7_1 : Cert7 := genCert7 specWide 0 gen0 r1

theorem cert7_1_accepted : checkCert7 specWide 0 (encodeBytes gen0) cert7_1 = true := by
  decide +kernel

theorem cert7_1_bytes_accepted :
    checkCert7Bytes specWide 0 (encodeBytes gen0) (encodeCert7 cert7_1) = true := by
  simp only [checkCert7Bytes, decodeCert7_encodeCert7]; exact cert7_1_accepted

/-- The PGSC7 witness for this step has 4 tagged units (the one unit of `r1` and the three
units of the target `gen3`; `gen0` has none). -/
theorem cert7_1_order_length : cert7_1.order.length = 4 := by decide +kernel

/-- A PGSC7 certificate with a forged (reversed) sweep witness is rejected. -/
theorem cert7_1_forged_order_rejected :
    checkCert7 specWide 0 (encodeBytes gen0) { cert7_1 with order := cert7_1.order.reverse } =
      false := by
  decide +kernel

/-- A PGSC7 certificate with an understated error level is rejected by the sweep. -/
theorem cert7_1_forged_level_rejected :
    checkCert7 specWide 0 (encodeBytes gen0)
      { cert7_1 with base := { cert7_1.base with errLevel := 5 } } = false := by
  decide +kernel

/-- The PGSC6 certificate bytes for the same step are not PGSC7 bytes. -/
theorem cert1_not_pgsc7 : decodeCert7 (encodeCert cert1) = none := decodeCert7_of_pgsc6 cert1

end PCS.V2.ProofGatedCert7
