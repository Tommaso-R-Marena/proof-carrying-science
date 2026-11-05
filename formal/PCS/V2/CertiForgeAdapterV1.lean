import PCS.V2.TranslationV3Json
import PCS.V2.ReceiptThreatModelV3

/-!
# PCS ⇄ CertiForge adapter contract v1 (`pcs-certiforge-equivalence-v1`)

A minimal, versioned formal contract for receiving an independently checked
**program-equivalence certificate** from CertiForge without importing CertiForge.

* An *untrusted optimizer* proposes replacing program `P` by program `Q`.
* An *independent CertiForge checker* (identified by an approved checker id and holding a key
  registered for this adapter) attests `P ≡ Q` under the semantics defined **here**
  (`pcs-slbv-v1`: pure straight-line bit-vector programs).
* PCS accepts a scoped claim only through `decideCF`.

## Semantics in scope

`pcs-slbv-v1` — pure, total, straight-line SSA programs over `BitVec w`: constants and the binary
operations `+ - * &&& ||| ^^^ <<< >>>` (shift amounts are the second operand's value; shifting by
`≥ w` yields `0`, as in Lean's `BitVec`).  There is no memory, no I/O, no division, no undefined
behaviour and no native execution.  Claims about any other semantics (`effectful`, `native`,
`undefinedBehavior`, `other`) are **rejected as unsupported** (`unsupported_semantics_rejected`);
PCS does not pretend to understand them.

## Results

* `ProgEquiv` is an equivalence relation; extensional properties transfer along it
  (`progEquiv_property_transfer`), and so along any certified chain of optimizations
  (`chain_equiv`, `certified_chain_property_transfer`).
* Non-extensional properties (e.g. instruction count) do **not** transfer (`cost_not_invariant`):
  an "improvement" is a separate claim, never part of the equivalence guarantee.
* `decideCF` has two accepting outcomes with different strength:
  - `CERTIFIED_EQUIVALENCE_PCS_CHECKED` — PCS itself decided equivalence by exhaustive evaluation
    (small input spaces); **unconditionally sound** (`decideCF_pcsChecked_sound`);
  - `CERTIFIED_EQUIVALENCE_ATTESTED` — accepted on CertiForge checker receipts through the
    stateful ledger protocol; sound **only under the explicit assumption** that fewer than the
    quorum of active checker keys are dishonest (`decideCF_attested_sound`).  We do **not** assume
    CertiForge's Rust verifier refines this Lean semantics; that is what the honesty assumption
    stands for.
* A concrete counterexample input supplied by anyone overrides every receipt
  (`counterexample_overrides_receipts`): a dishonest checker cannot make PCS accept a refuted pair.
* The improvement claim never influences the equivalence decision (`decideCF_ignores_improvement`);
  the instruction-count metric is re-computed by PCS (`improvementVerified`).
-/

set_option autoImplicit false

namespace PCS.V2.CertiForge

open PCS.V2.Json PCS.V2.Semantic PCS.V2.Semantic.Ledger PCS.V2.Semantic.V3

/-! ## Programs and semantics -/

inductive BVOp where
  | add | sub | mul | and | or | xor | shl | lshr
  deriving Repr, DecidableEq, Inhabited

def BVOp.apply {w : Nat} : BVOp → BitVec w → BitVec w → BitVec w
  | .add, x, y => x + y
  | .sub, x, y => x - y
  | .mul, x, y => x * y
  | .and, x, y => x &&& y
  | .or, x, y => x ||| y
  | .xor, x, y => x ^^^ y
  | .shl, x, y => x <<< y.toNat
  | .lshr, x, y => x >>> y.toNat

/-- SSA instruction: its result is appended to the register file. -/
inductive SLInstr where
  | const (v : Nat)
  | bin (op : BVOp) (a b : Nat)
  deriving Repr, DecidableEq, Inhabited

/-- A straight-line program: registers `0 … arity-1` are the inputs. -/
structure SLProg where
  width : Nat
  arity : Nat
  body : List SLInstr
  outputs : List Nat
  deriving Repr, DecidableEq, Inhabited

def SLInstr.eval {w : Nat} (regs : List (BitVec w)) : SLInstr → BitVec w
  | .const v => BitVec.ofNat w v
  | .bin op a b => op.apply (regs.getD a 0) (regs.getD b 0)

def runBody {w : Nat} : List (BitVec w) → List SLInstr → List (BitVec w)
  | regs, [] => regs
  | regs, i :: is => runBody (regs ++ [i.eval regs]) is

/-- Denotation of a program at width `w`. -/
def evalW (w : Nat) (P : SLProg) (ins : List (BitVec w)) : List (BitVec w) :=
  P.outputs.map (fun o => (runBody ins P.body).getD o 0)

/-- Every operand refers to an already-defined register; outputs are defined. -/
def SLProg.wellFormedB (P : SLProg) : Bool :=
  (P.body.zipIdx.all fun (i, k) => match i with
    | .const _ => true
    | .bin _ a b => decide (a < P.arity + k) && decide (b < P.arity + k)) &&
  P.outputs.all (fun o => decide (o < P.arity + P.body.length))

/-- **Program equivalence** under `pcs-slbv-v1`. -/
def ProgEquiv (P Q : SLProg) : Prop :=
  P.width = Q.width ∧ P.arity = Q.arity ∧ P.outputs.length = Q.outputs.length ∧
    ∀ ins : List (BitVec P.width), ins.length = P.arity → evalW P.width P ins = evalW P.width Q ins

theorem ProgEquiv.refl (P : SLProg) : ProgEquiv P P := ⟨rfl, rfl, rfl, fun _ _ => rfl⟩

theorem ProgEquiv.symm {P Q : SLProg} (h : ProgEquiv P Q) : ProgEquiv Q P := by
  obtain ⟨hw, ha, ho, he⟩ := h
  obtain ⟨wP, aP, bP, oP⟩ := P
  obtain ⟨wQ, aQ, bQ, oQ⟩ := Q
  simp only at hw ha ho he
  subst hw ha
  exact ⟨rfl, rfl, ho.symm, fun ins hl => (he ins hl).symm⟩

theorem ProgEquiv.trans {P Q R : SLProg} (h₁ : ProgEquiv P Q) (h₂ : ProgEquiv Q R) :
    ProgEquiv P R := by
  obtain ⟨hw, ha, ho, he⟩ := h₁
  obtain ⟨hw', ha', ho', he'⟩ := h₂
  obtain ⟨wP, aP, bP, oP⟩ := P
  obtain ⟨wQ, aQ, bQ, oQ⟩ := Q
  simp only at hw ha ho he hw' ha' ho' he' ⊢
  subst hw ha
  exact ⟨hw', ha', ho.trans ho', fun ins hl => (he ins hl).trans (he' ins hl)⟩

/-- An **extensional property**: a property of the input/output function at the program's width
    and arity. -/
def Extensional := (w : Nat) → (arity : Nat) → (List (BitVec w) → List (BitVec w)) → Prop

def Satisfies (φ : Extensional) (P : SLProg) : Prop :=
  φ P.width P.arity (fun ins => if ins.length = P.arity then evalW P.width P ins else [])

/-- **`progEquiv_property_transfer`**: equivalent programs satisfy the same extensional
    properties. -/
theorem progEquiv_property_transfer {P Q : SLProg} (h : ProgEquiv P Q) (φ : Extensional)
    (hP : Satisfies φ P) : Satisfies φ Q := by
  obtain ⟨hw, ha, _, he⟩ := h
  obtain ⟨wP, aP, bP, oP⟩ := P
  obtain ⟨wQ, aQ, bQ, oQ⟩ := Q
  simp only at hw ha he
  subst hw ha
  unfold Satisfies at hP ⊢
  have hf : (fun ins : List (BitVec wP) => if ins.length = aP then evalW wP ⟨wP, aP, bP, oP⟩ ins else []) =
      (fun ins => if ins.length = aP then evalW wP ⟨wP, aP, bQ, oQ⟩ ins else []) := by
    funext ins
    split
    · exact he ins (by assumption)
    · rfl
  rw [hf] at hP
  exact hP

/-- A chain of programs, each step equivalent to the next. -/
def ChainEquiv : List SLProg → Prop
  | [] | [_] => True
  | P :: Q :: rest => ProgEquiv P Q ∧ ChainEquiv (Q :: rest)

/-- **`chain_equiv`**: a sequence of individually equivalent optimization steps composes. -/
theorem chain_equiv : ∀ (P : SLProg) (rest : List SLProg), ChainEquiv (P :: rest) →
    ProgEquiv P ((P :: rest).getLast (List.cons_ne_nil _ _))
  | P, [], _ => ProgEquiv.refl P
  | P, Q :: rest, ⟨h, hr⟩ => by
    have := chain_equiv Q rest hr
    simpa [List.getLast_cons] using h.trans this

/-- Instruction count — a **non-extensional** metric. -/
def SLProg.cost (P : SLProg) : Nat := P.body.length

/-- **`cost_not_invariant`**: equivalence does not preserve cost, so an optimization
    "improvement" is never implied by (or part of) the equivalence guarantee. -/
theorem cost_not_invariant :
    ∃ P Q : SLProg, ProgEquiv P Q ∧ P.cost ≠ Q.cost := by
  refine ⟨⟨8, 1, [.const 0, .bin .add 0 1], [2]⟩, ⟨8, 1, [], [0]⟩, ⟨rfl, rfl, rfl, ?_⟩, by decide⟩
  intro ins hl
  match ins, hl with
  | [x], _ => simp [evalW, runBody, SLInstr.eval, BVOp.apply]

/-! ## PCS's own decision procedure for small input spaces -/

def allBV (w : Nat) : List (BitVec w) := (List.range (2 ^ w)).map (BitVec.ofNat w)

theorem mem_allBV {w : Nat} (x : BitVec w) : x ∈ allBV w := by
  unfold allBV
  refine List.mem_map.mpr ⟨x.toNat, List.mem_range.mpr x.isLt, ?_⟩
  simp

def allInputs (w : Nat) : Nat → List (List (BitVec w))
  | 0 => [[]]
  | n + 1 => (allBV w).flatMap (fun v => (allInputs w n).map (v :: ·))

theorem mem_allInputs {w : Nat} : ∀ (n : Nat) (ins : List (BitVec w)), ins.length = n →
    ins ∈ allInputs w n
  | 0, [], _ => by simp [allInputs]
  | n + 1, x :: xs, hl => by
    simp only [List.length_cons, Nat.add_right_cancel_iff] at hl
    unfold allInputs
    exact List.mem_flatMap.mpr ⟨x, mem_allBV x, List.mem_map.mpr ⟨xs, mem_allInputs n xs hl, rfl⟩⟩

/-- Exhaustive equivalence check (only when `width * arity ≤ bound`). -/
def exhaustiveEquivB (bound : Nat) (P Q : SLProg) : Option Bool :=
  if P.width = Q.width ∧ P.arity = Q.arity ∧ P.outputs.length = Q.outputs.length ∧
      P.width * P.arity ≤ bound then
    some ((allInputs P.width P.arity).all (fun ins => evalW P.width P ins == evalW P.width Q ins))
  else none

/-- **Soundness of PCS's own check.** -/
theorem exhaustiveEquivB_sound {bound : Nat} {P Q : SLProg}
    (h : exhaustiveEquivB bound P Q = some true) : ProgEquiv P Q := by
  unfold exhaustiveEquivB at h
  split at h
  · rename_i hc
    obtain ⟨hw, ha, ho, -⟩ := hc
    simp only [Option.some.injEq, List.all_eq_true, beq_iff_eq] at h
    exact ⟨hw, ha, ho, fun ins hl => h ins (mem_allInputs _ ins hl)⟩
  · cases h

/-- A refuting input: both programs well-shaped, outputs differ. -/
def refutesB (P Q : SLProg) (ins : List Nat) : Bool :=
  decide (P.width = Q.width) && decide (ins.length = P.arity) &&
    (evalW P.width P (ins.map (BitVec.ofNat P.width)) != evalW P.width Q (ins.map (BitVec.ofNat P.width)))

theorem refutesB_sound {P Q : SLProg} {ins : List Nat} (h : refutesB P Q ins = true) :
    ¬ ProgEquiv P Q := by
  rintro ⟨-, -, -, he⟩
  simp only [refutesB, Bool.and_eq_true, decide_eq_true_eq, bne_iff_ne, ne_eq] at h
  exact h.2 (he _ (by simpa using h.1.2))

/-! ## The adapter claim, its statement and the decision -/

/-- Semantics a claim is made under.  Only `pureStraightLineBV` is supported. -/
inductive ProgramSemantics where
  | pureStraightLineBV
  | effectful (tag : String)
  | native (tag : String)
  | undefinedBehavior (tag : String)
  | other (tag : String)
  deriving Repr, DecidableEq, Inhabited

/-- An optimization-improvement claim (kept separate from equivalence). -/
structure ImprovementClaim where
  metric : String
  before : Nat
  after : Nat
  deriving Repr, DecidableEq, Inhabited

/-- A CertiForge equivalence claim as submitted to PCS. -/
structure CFClaim where
  semantics : ProgramSemantics
  source : SLProg
  target : SLProg
  /-- identity of the CertiForge checker whose verdict the receipts attest -/
  checker : String
  /-- an input vector anyone may supply as a refutation attempt -/
  counterexample : Option (List Nat)
  improvement : Option ImprovementClaim
  receipts : List ReceiptEnvelope
  deriving Repr, Inhabited

/-- Adapter configuration: an `AuthorityV3` whose `.proof`-role keys are the CertiForge checker
    keys (a separate configuration from the Lean authority's), approved checker ids and the
    exhaustive-check bound. -/
structure CFAuthority where
  auth : AuthorityV3
  checkers : List String
  exhaustiveBound : Nat

def CFAuthority.quorum (A : CFAuthority) : Nat := max 1 A.auth.proofQuorum

def encOp : BVOp → JVal
  | .add => .str "add" | .sub => .str "sub" | .mul => .str "mul" | .and => .str "and"
  | .or => .str "or" | .xor => .str "xor" | .shl => .str "shl" | .lshr => .str "lshr"

def encInstr : SLInstr → JVal
  | .const v => .obj [("const", encNat v)]
  | .bin op a b => .obj [("a", encNat a), ("b", encNat b), ("op", encOp op)]

def encProg (P : SLProg) : JVal :=
  .obj [("arity", encNat P.arity), ("body", .arr (P.body.map encInstr)),
    ("outputs", .arr (P.outputs.map encNat)), ("width", encNat P.width)]

/-- What a CertiForge checker receipt must attest. -/
def cfStatement (A : CFAuthority) (c : CFClaim) : JVal :=
  .obj [("checker", .str c.checker), ("context", encContext A.auth),
    ("purpose", .str "certiforge-program-equivalence-v1"), ("semantics", .str "pcs-slbv-v1"),
    ("source", encProg c.source), ("target", encProg c.target)]

/-- Domain separation from the Lean authority's kernel-check records. -/
theorem cfStatement_ne_proofStatement (A : CFAuthority) (c : CFClaim) (A' : AuthorityV3)
    (cand : Candidate) (axs : List String) : cfStatement A c ≠ proofStatement A' cand axs := by
  intro h
  simp only [cfStatement, proofStatement, JVal.obj.injEq, List.cons.injEq, Prod.mk.injEq] at h
  exact absurd h.1.1 (by decide)

/-- Receipt phase: every envelope is a `.proof`-role envelope of an active, unrevoked checker
    key attesting exactly `cfStatement`, fresh in the ledger; distinct issuers meet the quorum. -/
def cfReceiptPhase (A : CFAuthority) (now : Nat) (S : LedgerV3) (c : CFClaim) :
    Except ReceiptFailure (List String) :=
  match acceptAllV3 (policy A.auth S now) (fun _ => cfStatement A c) S.genesis ⟨S.consumed⟩ c.receipts with
  | .error f => .error f
  | .ok ns =>
    if A.quorum ≤ (issuersOf .proof c.receipts).length then .ok ns
    else .error (.quorumNotMet .proof (issuersOf .proof c.receipts).length A.quorum)

inductive CFOutcome where
  | certifiedPCSChecked
  | certifiedAttested
  | refuted
  | unsupportedSemantics
  | malformedProgram
  | unapprovedChecker
  | receiptRejected (f : ReceiptFailure)
  | invalidAuthority
  deriving Repr, DecidableEq, Inhabited

def CFOutcome.name : CFOutcome → String
  | .certifiedPCSChecked => "CERTIFIED_EQUIVALENCE_PCS_CHECKED"
  | .certifiedAttested => "CERTIFIED_EQUIVALENCE_ATTESTED"
  | .refuted => "REFUTED"
  | .unsupportedSemantics => "UNSUPPORTED_SEMANTICS"
  | .malformedProgram => "MALFORMED_PROGRAM"
  | .unapprovedChecker => "UNAPPROVED_CHECKER"
  | .receiptRejected _ => "RECEIPT_REJECTED"
  | .invalidAuthority => "INVALID_AUTHORITY"

/-- **The adapter decision.** -/
def decideCF (A : CFAuthority) (now : Nat) (S : LedgerV3) (c : CFClaim) : CFOutcome :=
  if !A.auth.wellFormedB then .invalidAuthority
  else if c.semantics ≠ .pureStraightLineBV then .unsupportedSemantics
  else if !(c.source.wellFormedB && c.target.wellFormedB) then .malformedProgram
  else if (c.counterexample.map (refutesB c.source c.target)).getD false then .refuted
  else match exhaustiveEquivB A.exhaustiveBound c.source c.target with
    | some true => .certifiedPCSChecked
    | some false => .refuted
    | none =>
      if !(decide (c.source.width = c.target.width) && decide (c.source.arity = c.target.arity) &&
          decide (c.source.outputs.length = c.target.outputs.length)) then .refuted
      else if !A.checkers.contains c.checker then .unapprovedChecker
      else match cfReceiptPhase A now S c with
        | .error f => .receiptRejected f
        | .ok _ => .certifiedAttested

/-- Nonces consumed by the decision (only for attested certification). -/
def stepCF (A : CFAuthority) (now : Nat) (S : LedgerV3) (c : CFClaim) : CFOutcome × LedgerV3 :=
  let o := decideCF A now S c
  (o, if o = .certifiedAttested then { S with consumed := c.receipts.map (·.nonce) ++ S.consumed }
      else S)

/-! ## Soundness -/

theorem unsupported_semantics_rejected {A : CFAuthority} {now : Nat} {S : LedgerV3} {c : CFClaim}
    (hwf : A.auth.wellFormedB = true) (h : c.semantics ≠ .pureStraightLineBV) :
    decideCF A now S c = .unsupportedSemantics := by
  unfold decideCF; simp [hwf, h]

/-- **`decideCF_pcsChecked_sound`** (unconditional). -/
theorem decideCF_pcsChecked_sound {A : CFAuthority} {now : Nat} {S : LedgerV3} {c : CFClaim}
    (h : decideCF A now S c = .certifiedPCSChecked) :
    c.semantics = .pureStraightLineBV ∧ ProgEquiv c.source c.target := by
  unfold decideCF at h
  split at h; · cases h
  split at h; · cases h
  rename_i hsem
  split at h; · cases h
  split at h; · cases h
  split at h
  · rename_i he
    exact ⟨Classical.not_not.mp hsem, exhaustiveEquivB_sound he⟩
  · cases h
  · split at h; · cases h
    split at h; · cases h
    split at h <;> cases h

theorem decideCF_attested_receipts {A : CFAuthority} {now : Nat} {S : LedgerV3} {c : CFClaim}
    (h : decideCF A now S c = .certifiedAttested) :
    c.semantics = .pureStraightLineBV ∧ c.source.wellFormedB = true ∧ c.target.wellFormedB = true ∧
    c.checker ∈ A.checkers ∧
    (∀ e ∈ c.receipts, S.genesis ≤ e.issuedAt ∧
      EnvOK (policy A.auth S now) e.role (cfStatement A c) e ∧ e.nonce ∉ S.consumed) ∧
    (c.receipts.map (·.nonce)).Nodup ∧ A.quorum ≤ (issuersOf .proof c.receipts).length := by
  unfold decideCF at h
  split at h; · cases h
  split at h; · cases h
  rename_i hsem
  split at h; · cases h
  rename_i hwfp
  split at h; · cases h
  split at h
  · cases h
  · cases h
  · split at h; · cases h
    split at h; · cases h
    rename_i hchk
    split at h; · cases h
    rename_i ns hrp
    unfold cfReceiptPhase at hrp
    split at hrp
    · cases hrp
    rename_i ns' hacc
    split at hrp
    · rename_i hq
      obtain ⟨hall, hnd, -⟩ := acceptAllV3_ok_iff.mp hacc
      have hw : (c.source.wellFormedB && c.target.wellFormedB) = true := by simpa using hwfp
      have hc : c.checker ∈ A.checkers := by simpa using hchk
      rw [Bool.and_eq_true] at hw
      exact ⟨Classical.not_not.mp hsem, hw.1, hw.2, hc, hall, hnd, hq⟩
    · cases hrp

/-- What CertiForge checker receipts assert, and the trust assumption about it: in world `W`, a
    true `cfStatement` means the two programs are equivalent under `pcs-slbv-v1`.  (A checker
    that is honest but whose verifier has a bug violates this — exactly what the assumption
    names.) -/
def CFStatementsMeanEquivalence (W : ReceiptWorld) (A : CFAuthority) : Prop :=
  ∀ c : CFClaim, W.Holds .proof (cfStatement A c) → ProgEquiv c.source c.target

/-- **`decideCF_attested_sound`**: an attested certification implies equivalence provided fewer
    than the quorum of active checker keys are dishonest and checker statements mean what they
    say.  No refinement proof of CertiForge's verifier is assumed beyond this. -/
theorem decideCF_attested_sound {A : CFAuthority} {now : Nat} {S : LedgerV3} {c : CFClaim}
    (h : decideCF A now S c = .certifiedAttested) (W : ReceiptWorld)
    (hq : DishonestBelow W A.auth now .proof A.quorum) (hmean : CFStatementsMeanEquivalence W A) :
    ProgEquiv c.source c.target := by
  obtain ⟨-, -, -, -, hall, -, hlen⟩ := decideCF_attested_receipts h
  apply hmean c
  apply Classical.byContradiction
  intro hno
  have hdis : ∀ k ∈ issuersOf .proof c.receipts,
      k ∈ activeKeys A.auth now .proof ∧ ¬ KeyHonest W A.auth.verify k := by
    intro k hk
    obtain ⟨e, he, hr, hi⟩ := mem_issuersOf.mp hk
    obtain ⟨-, ok, -⟩ := hall e he
    refine ⟨?_, fun hh => hno ?_⟩
    · have := ok.key; rw [ok.roleEq] at this; rw [← hi]; rw [hr] at this; exact this
    · have := hh e (by rw [← hi]; exact ok.signature)
      rw [ok.statement, hr] at this
      exact this
  have := hq (issuersOf .proof c.receipts) (dedup_nodup _) hdis
  omega

/-- **`counterexample_overrides_receipts`**: a supplied refuting input prevents every
    certification, whatever receipts accompany the claim. -/
theorem counterexample_overrides_receipts {A : CFAuthority} {now : Nat} {S : LedgerV3}
    {c : CFClaim} {ins : List Nat} (hce : c.counterexample = some ins)
    (hr : refutesB c.source c.target ins = true) :
    decideCF A now S c ≠ .certifiedAttested ∧ decideCF A now S c ≠ .certifiedPCSChecked := by
  have hne := refutesB_sound hr
  refine ⟨fun h => ?_, fun h => hne (decideCF_pcsChecked_sound h).2⟩
  unfold decideCF at h
  split at h; · cases h
  split at h; · cases h
  split at h; · cases h
  split at h; · cases h
  rename_i hcx
  rw [hce] at hcx
  simp [hr] at hcx

/-- **`decideCF_ignores_improvement`**: the improvement claim never influences the decision. -/
theorem decideCF_ignores_improvement (A : CFAuthority) (now : Nat) (S : LedgerV3) (c : CFClaim)
    (imp : Option ImprovementClaim) :
    decideCF A now S { c with improvement := imp } = decideCF A now S c := by
  simp only [decideCF, cfReceiptPhase, cfStatement]

/-- The improvement claim is reported separately; PCS verifies only the instruction-count
    metric, by recomputation. -/
def improvementVerified (c : CFClaim) : Bool :=
  match c.improvement with
  | some ⟨"instruction_count", b, a⟩ => b == c.source.cost && a == c.target.cost && decide (a < b)
  | _ => false

/-- **`certified_chain_property_transfer`**: if every step of an optimization chain is certified
    (by PCS's own check, or attested under the honesty assumptions), an extensional property of
    the first program holds for the last. -/
theorem certified_chain_property_transfer (P : SLProg) (rest : List SLProg)
    (hchain : ChainEquiv (P :: rest)) (φ : Extensional) (hP : Satisfies φ P) :
    Satisfies φ ((P :: rest).getLast (List.cons_ne_nil _ _)) :=
  progEquiv_property_transfer (chain_equiv P rest hchain) φ hP

end PCS.V2.CertiForge

namespace PCS.V2.CertiForge.Examples

open PCS.V2.Semantic.V3 PCS.V2.Semantic.Ledger

/-- `x * 2` at width 4. -/
def mulTwo : SLProg := ⟨4, 1, [.const 2, .bin .mul 0 1], [2]⟩
/-- `x <<< 1` at width 4. -/
def shlOne : SLProg := ⟨4, 1, [.const 1, .bin .shl 0 1], [2]⟩
/-- `x + 1` at width 4 (not equivalent to `x * 2`). -/
def addOne : SLProg := ⟨4, 1, [.const 1, .bin .add 0 1], [2]⟩

/-- An adapter configuration with no checker keys and exhaustive bound 8. -/
def exAuthority : CFAuthority :=
  { auth := { registry := ⟨[], []⟩, context := ⟨"certiforge-fixture-scope", "-", "-"⟩, keys := [],
              revoked := [], verify := fun _ _ _ => false, allowedAxioms := [],
              requireElaboration := false, requireProof := true, confirmationQuorum := 1,
              elaborationQuorum := 0, proofQuorum := 1 },
    checkers := ["certiforge-checker-v1"], exhaustiveBound := 8 }

def exClaim (P Q : SLProg) (sem : ProgramSemantics := .pureStraightLineBV) : CFClaim :=
  ⟨sem, P, Q, "certiforge-checker-v1", none, some ⟨"instruction_count", 2, 2⟩, []⟩

/-- PCS itself certifies `x * 2 ≡ x <<< 1` at width 4 by exhaustive evaluation. -/
theorem mulTwo_shlOne_pcs_checked :
    decideCF exAuthority 0 ⟨[], [], 0⟩ (exClaim mulTwo shlOne) = .certifiedPCSChecked := by decide

/-- …and the equivalence is a theorem. -/
theorem mulTwo_equiv_shlOne : ProgEquiv mulTwo shlOne :=
  (decideCF_pcsChecked_sound mulTwo_shlOne_pcs_checked).2

/-- `x * 2` vs `x + 1` is refuted by PCS, whatever any checker says. -/
theorem mulTwo_addOne_refuted :
    decideCF exAuthority 0 ⟨[], [], 0⟩ (exClaim mulTwo addOne) = .refuted := by decide

/-- A claim under effectful semantics is rejected as unsupported. -/
theorem effectful_claim_unsupported :
    decideCF exAuthority 0 ⟨[], [], 0⟩ (exClaim mulTwo shlOne (.effectful "io")) =
      .unsupportedSemantics := by decide

/-- An "improvement" claim of 2 → 2 instructions is not verified (no improvement). -/
theorem no_improvement_claimed_correctly : improvementVerified (exClaim mulTwo shlOne) = false := by
  decide

end PCS.V2.CertiForge.Examples
