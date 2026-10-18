# Proof-gated recursive self-modification: v4 technical report

Date: 17 October 2026 · Toolchain: Lean 4.28.0 (pinned `lean-toolchain`), no external
Lake packages, no Mathlib.

This report covers the research assignment in `ARISTOTLE_SELF_CONTAINED_MULTILAYER_V4.md`.
Everything listed as **proved** below is a kernel-checked Lean theorem with no `sorry`,
no `admit`, no `native_decide`, no new `axiom`, no `unsafe` and no `@[implemented_by]`.
Its axiom footprint is printed by `PCS/V2/ProofGatedAudit.lean`.

---

## 0. Build commands that were run, and their results

```bash
lake build PCS.V2.ProofGatedSelfImprovement PCS.V2.ProofGatedArtifacts \
  PCS.V2.ProofGatedPromotion PCS.V2.ProofGatedInference PCS.V2.ProofGatedSymbolic \
  PCS.V2.ProofGatedMultilayer                         # original targets: exit 0
lake build PCS.V2.ProofGatedGeneric PCS.V2.ProofGatedWide PCS.V2.ProofGatedDeep \
  PCS.V2.ProofGatedCodec PCS.V2.ProofGatedV1Analysis PCS.V2.ProofGatedNetArtifacts \
  PCS.V2.ProofGatedLimits PCS.V2.ProofGatedAudit      # all 14 modules: exit 0
lake env lean PCS/V2/ProofGatedAudit.lean             # exit 0, 125 axiom reports
rg -n "sorry|admit|native_decide|implemented_by|^axiom|unsafe" PCS/V2/ProofGated*.lean
#   only hit: the prose word "sorryAx" in the audit file's doc comment
```

The only build warnings come from the **unchanged** original file
`ProofGatedPromotion.lean` (three unused `dif` binder names). The new modules build
without warnings.

**Axiom audit** (`lake env lean PCS/V2/ProofGatedAudit.lean`, 125 theorems after the
follow-up fix): every theorem depends on a subset of `propext`, `Classical.choice` and
`Quot.sound`; 9 depend on no axioms. No `sorryAx` and no `Lean.ofReduceBool` appear
anywhere. `decide +kernel` (used for literal-string fixtures) is checked by the kernel;
it is not `native_decide` and adds no axiom.

**Files changed.**
* New: `PCS/V2/ProofGatedGeneric.lean`, `ProofGatedWide.lean`, `ProofGatedDeep.lean`,
  `ProofGatedCodec.lean`, `ProofGatedV1Analysis.lean`, `ProofGatedNetArtifacts.lean`,
  `ProofGatedLimits.lean`, and this report.
* Extended: `PCS/V2/ProofGatedAudit.lean` (imports and `#print axioms` lines only).
* Follow-up fix: `PCS/V2/ProofGatedArtifacts.lean` (verified codec for `encode` /
  `parseComponents`, legacy definitions retained, new theorems appended) and
  `PCS/V2/ProofGatedInference.lean` (two theorems appended); see §1.0.
* Not modified: every other file, including all PCS authority modules, the other
  four original ProofGated modules, `lakefile.toml` and `PCS.lean`. The new modules are built by
  module name and are not part of the `PCS` default umbrella.

---

## 1. Priority A: serialization roundtrip, injectivity, inference

### 1.0 Follow-up fix: the `PGSI1` path now has an unconditional roundtrip

`PCS/V2/ProofGatedArtifacts.lean` was changed so that `encode` and `parseComponents`
use the verified renderer/parser of `ProofGatedCodec` (`renderInt`, `parseInt`,
`joinFields`, `splitFields`). **The artifact bytes are unchanged**: `PGSI1|R|w|b` /
`PGSI1|L|w|b` with canonical decimal integers. `valid`, `decode` (still re-checking
`valid m && encode m == raw`), `acceptWire`, `decode_canonical`, `decode_bounded`,
`acceptWire_sound` and the CLI `main` keep their original text and statements. The
original core-`toString` definitions are kept verbatim as `encodeLegacy`,
`parseComponentsLegacy`, `decodeLegacy` (no longer used by the gate).

Proved with **no hypotheses** (axioms: `propext`, `Classical.choice`, `Quot.sound`):

```lean
-- PCS.V2.ProofGatedArtifacts
theorem parseComponents_encode (m : Neuron) : parseComponents (encode m) = some m
theorem decode_encode_of_bounded (m : Neuron)
    (h : valid m = true) : decode (encode m) = some m          -- the requested statement
theorem encode_injective {m₁ m₂ : Neuron} (he : encode m₁ = encode m₂) : m₁ = m₂
theorem decode_eq_some_iff (raw : String) (m : Neuron) :
    decode raw = some m ↔ valid m = true ∧ encode m = raw
theorem decode_eq_none_of_invalid (m : Neuron) (h : valid m = false) :
    decode (encode m) = none
-- PCS.V2.ProofGatedInference
theorem infer_encode (m : Neuron) (h : valid m = true) (x : Int) :
    infer (encode m) x = some (predict m x)
theorem infer_eq_some_iff (raw : String) (x y : Int) :
    infer raw x = some y ↔ ∃ m, valid m = true ∧ encode m = raw ∧ predict m x = y
```

Kernel-checked fixtures (`decide +kernel`): `encode_examples` (including
`encode ⟨false, -7, -1⟩ = "PGSI1|L|-7|-1"`), `decode_acceptance_examples`, and
`decode_rejection_examples` (`+1`, `-0`, `01`, `33`, `-33`, unknown activation, trailing
`|`, leading space, wrong version tag, empty text are all rejected).

Byte compatibility with the legacy encoder (`ProofGatedV1Analysis`):

```lean
theorem encode_eq_encodeLegacy_of_nonneg (m : Neuron) (hw : 0 ≤ m.weight) (hb : 0 ≤ m.bias) :
    encode m = encodeLegacy m                                   -- unconditional
theorem encode_eq_encodeLegacy_of_append_spec
    (happ : ∀ s : String, String.Internal.append "-" s = "-" ++ s) (m : Neuron) :
    encode m = encodeLegacy m
theorem decode_encodeLegacy_of_append_spec
    (happ : ∀ s : String, String.Internal.append "-" s = "-" ++ s) (m : Neuron)
    (h : valid m = true) : decode (encodeLegacy m) = some m
```

So for artifacts written by the old encoder, acceptance by the new decoder needs only the
runtime behaviour of the opaque append; the earlier assumption about core `toInt?` is no
longer needed anywhere. As an informal runtime check (not a proof), `#eval` confirmed
`encode m == encodeLegacy m` and `decode (encodeLegacy m) == some m` for all 650
combinations of weight in `[-32, 32]`, bias in `{-32, -1, 0, 7, 32}` and both
activations.

Sections 1.1–1.2 below describe the **legacy** definitions; read `encode`, `decode`,
`parseComponents` there as `encodeLegacy`, `decodeLegacy`, `parseComponentsLegacy`
(the Lean sources use these names; `parseComponents_encode` in `ProofGatedV1Analysis`
is now `parseComponentsLegacy_encodeLegacy`, and `infer_encode_of_core` was removed
because `infer_encode` above supersedes it).

### 1.1 Finding: the requested statement about the *original* `encode` is not derivable

The requested theorem

```lean
theorem decode_encode_of_bounded (m : Neuron) (h : valid m = true) :
    decode (encode m) = some m
```

refers to the unmodified `PCS.V2.ProofGatedArtifacts.encode`, which renders integers
with core `toString`. In Lean 4.28:

```lean
theorem toString_negSucc_def (n : Nat) :            -- ProofGatedCodec, proved by rfl
    toString (Int.negSucc n) = String.Internal.append "-" (toString (n + 1))
```

and `String.Internal.append` is declared `opaque` (it is implemented natively by
`lean_string_append`). The kernel never unfolds an opaque constant, and no library
theorem constrains this one. So **nothing about the characters of `toString (-1 : Int)`
can be derived from the definitions**, and the requested statement for any neuron with
a negative parameter cannot be proved as stated. This is a property of the
specification artifact (its choice of core printing function), not of the neural
model. We did not add an axiom to get around it.

A second, independent gap is that core `String.toInt?` is built on the `Std.Iter`
iterator framework over `String.Slice`. Kernel reduction gets stuck on it (even
`"27".toInt? = some 27` is not closed by `decide +kernel`), and the library has no
lemma relating `Slice.chars` to `String.toList`.

### 1.2 What we proved about the original format (`ProofGatedV1Analysis.lean`)

Unconditional (no hypotheses):

```lean
-- Lean core's legacy String.splitOn with separator "|" equals the verified list-level
-- splitter, for EVERY string, with any Unicode content:
theorem splitOn_pipe (s : String) :
    s.splitOn "|" = (splitFields s.toList).map String.ofList
theorem encode_splitOn (m : Neuron) (hw : '|' ∉ (toString m.weight).toList)
    (hb : '|' ∉ (toString m.bias).toList) :
    (encode m).splitOn "|" =
      ["PGSI1", String.ofList (actChars m), toString m.weight, toString m.bias]
theorem encode_injective_nonneg {m₁ m₂ : Neuron}
    (hw₁ : 0 ≤ m₁.weight) (hb₁ : 0 ≤ m₁.bias) (hw₂ : 0 ≤ m₂.weight) (hb₂ : 0 ≤ m₂.bias)
    (he : encode m₁ = encode m₂) : m₁ = m₂
theorem decode_sound_unconditional {raw : String} {m : Neuron}
    (h : decode raw = some m) : encode m = raw ∧ valid m = true
```

`splitOn_pipe` is a general theorem about core's `String.splitOnAux`, proved by
induction over UTF-8 byte positions. Its helper lemmas cover `utf8GetAux`, the two
`Pos.Raw.extract` workers and `utf8ByteSize` of `String.ofList`.
`decode_sound_unconditional` records that **soundness** of the original decoder does not
depend on the gap: `decode` re-checks canonicity, so it fails closed whatever the opaque
primitive does. Only **completeness** (the roundtrip) depends on it.

Under explicit, ordinary hypotheses:

```lean
def CoreIntContract : Prop :=
  ∀ z : Int, -32 ≤ z → z ≤ 32 → '|' ∉ (toString z).toList ∧ (toString z).toInt? = some z

theorem decode_encode_of_bounded_of_core (hcore : CoreIntContract) (m : Neuron)
    (h : valid m = true) : decode (encode m) = some m          -- the target statement
theorem encode_injective_of_bounded_of_core (hcore : CoreIntContract) {m₁ m₂ : Neuron}
    (h₁ : valid m₁ = true) (h₂ : valid m₂ = true) (he : encode m₁ = encode m₂) : m₁ = m₂
theorem infer_encode_of_core (hcore : CoreIntContract) (m : Neuron) (h : valid m = true)
    (x : Int) : PCS.V2.ProofGatedInference.infer (encode m) x = some (predict m x)
theorem coreIntContract_of
    (happ : ∀ s : String, String.Internal.append "-" s = "-" ++ s)
    (hparse : ∀ z : Int, -32 ≤ z → z ≤ 32 → (String.ofList (renderInt z)).toInt? = some z) :
    CoreIntContract
theorem decode_encode_of_bounded_nonneg
    (hparse : ∀ z : Int, 0 ≤ z → z ≤ 32 → (String.ofList (renderInt z)).toInt? = some z)
    (m : Neuron) (h : valid m = true) (hw : 0 ≤ m.weight) (hb : 0 ≤ m.bias) :
    decode (encode m) = some m
```

The remaining obligations for the original format are therefore exactly:
(i) `happ`, the runtime behaviour of the opaque append on the prefix `"-"`; this is a
compiler/runtime trust assumption and cannot be proved inside Lean. (ii) `hparse`, a
true statement about core `toInt?` on canonical decimal strings; it needs a formal
theory of `String.Slice` iterators that the Lean 4.28 library does not yet provide. For
nonnegative parameters only (ii) is needed.

### 1.3 A fully verified replacement codec, `PGSI2` (`ProofGatedCodec.lean`)

These are transparent `List Char` functions. The renderer for naturals is **literally**
core `Nat.toDigits 10`.

```lean
theorem parseNat_renderNat (n : Nat) : parseNat (renderNat n) = some n
theorem parseInt_renderInt (z : Int) : parseInt (renderInt z) = some z   -- all Int
theorem parseInt_eq_some_iff (l : List Char) (z : Int) :
    parseInt l = some z ↔ renderInt z = l              -- accepts EXACTLY canonical text
theorem renderInt_injective {a b : Int} (h : renderInt a = renderInt b) : a = b
theorem splitFields_joinFields (fs : List (List Char)) (hne : fs ≠ [])
    (hfree : ∀ f ∈ fs, '|' ∉ f) : splitFields (joinFields fs) = fs
theorem joinFields_splitFields (l : List Char) : joinFields (splitFields l) = l
theorem decodeInts_encodeInts (tag : List Char) (htag : '|' ∉ tag) (zs : List Int) :
    decodeInts tag (encodeInts tag zs) = some zs
theorem decodeInts_canonical {tag l : List Char} {zs : List Int}
    (h : decodeInts tag l = some zs) : encodeInts tag zs = l
theorem toString_ofNat_toList (n : Nat) :
    (toString (Int.ofNat n)).toList = renderInt (Int.ofNat n)       -- unconditional
theorem toString_toList_of_append_spec
    (happ : ∀ s : String, String.Internal.append "-" s = "-" ++ s) (z : Int) :
    (toString z).toList = renderInt z
```

Rejection of non-canonical text follows from `parseInt_eq_some_iff` in general. As
literal fixtures, `noncanonical_rejected` checks that `"-0"`, `"007"`, `"+5"`, `""`,
`"1_000"`, `"-"`, `" 5"` and `"--5"` are all rejected (by `decide +kernel`).

---

## 2. Priority B: beyond the two-hidden-neuron network

### 2.1 A generic gate (`ProofGatedGeneric.lean`)

A `GateSpec M` packages `predict : M → Int → Int`, `target`, a finite `corpus` and a
decidable `valid : M → Bool`, for **any** model type `M`. The following are proved once
for every `M`:

```lean
theorem accept_iff_admissible (a b : M) : accept S a b = true ↔ admissible S a b
--   admissible := valid a ∧ valid b ∧ (∀ x ∈ corpus, correct a x → correct b x) ∧
--                 (∃ x ∈ corpus, ¬ correct a x ∧ correct b x) ∧ loss b < loss a
theorem accept_trans  (hab : accept S a b = true) (hbc : accept S b c = true) :
    accept S a c = true
theorem accept_irrefl (a : M) : accept S a a = false
theorem loss_eq_zero_iff (m : M) : loss S m = 0 ↔ ∀ x ∈ S.corpus, correct S m x
theorem perfect_valid_always_accepted (a b : M) (ha : S.valid a = true)
    (hb : S.valid b = true) (hperfect : ∀ x ∈ S.corpus, correct S b x)
    (himperfect : ∃ x ∈ S.corpus, ¬ correct S a x) : accept S a b = true
theorem trace_length_bound (h : CertifiedTrace S n a b) : n + loss S b ≤ loss S a
theorem no_long_trace (a b : M) (n : Nat) (hn : loss S a < n) : ¬ CertifiedTrace S n a b
theorem trace_valid, trace_preserves, trace_strict_gain
-- arbitrary adaptive / adversarial schedule  proposer : Nat → M → M
theorem runSched_count_bound (proposer : Nat → M → M) (k i : Nat) (m : M) :
    countSched S proposer i k m + loss S (runSched S proposer i k m) ≤ loss S m
theorem runSched_preserves, runSched_valid, runSched_loss_nonincrease,
        runSched_frozen_of_perfect, gatedStep_reject
theorem runSched_certified (proposer : Nat → M → M) (k i : Nat) (m : M) :
    CertifiedTrace S (countSched S proposer i k m) m (runSched S proposer i k m)
```

The executable gate is both sound and complete for its specification
(`accept_iff_admissible`). A history-dependent proposer is covered too: once the initial
state and the proposer are fixed, the whole history is determined by the step index,
so it is an instance of `Nat → M → M`.

**Regression bridges** (the old gates are instances, proved for all inputs):
`neuron_accept_eq : ProofGatedSelfImprovement.accept a b = accept neuronSpec a b`, and
`tiny_accept_eq : ProofGatedMultilayer.accept a b = accept tinySpec a b`.

### 2.2 Width-`n` networks (`ProofGatedWide.lean`)

`WideNet` has a list of hidden units `⟨w, b, out⟩` of arbitrary length and computes
`Σ out·relu(w·x+b) + outBias` exactly over `Int`. The versioned bound `Arch` fixes
`maxWidth` and the parameter magnitude `bound`.

The following structure transforms preserve the function **on every integer input**:

```lean
theorem predict_perm {m m' : WideNet} (h : m.hidden.Perm m'.hidden)
    (hb : m.outBias = m'.outBias) (x : Int) : predict m x = predict m' x
theorem predict_insert_dead (pre post : List HiddenUnit) (ob w b x : Int) :
    predict ⟨pre ++ ⟨w, b, 0⟩ :: post, ob⟩ x = predict ⟨pre ++ post, ob⟩ x
theorem predict_prune_dead (m : WideNet) (x : Int) :
    predict ⟨m.hidden.filter isLive, m.outBias⟩ x = predict m x
theorem predict_merge (pre post) (ob w b o₁ o₂ x : Int) :
    predict ⟨pre ++ ⟨w, b, o₁⟩ :: ⟨w, b, o₂⟩ :: post, ob⟩ x =
      predict ⟨pre ++ ⟨w, b, o₁ + o₂⟩ :: post, ob⟩ x
theorem predict_rescale (pre post) (ob w b o k : Int) (hk : 0 ≤ k) (x : Int) :
    predict ⟨pre ++ ⟨k * w, k * b, o⟩ :: post, ob⟩ x =
      predict ⟨pre ++ ⟨w, b, k * o⟩ :: post, ob⟩ x
```

The gate is invariant under these transforms (the congruence lemmas are generic):

```lean
theorem accept_congr_candidate (a : M) {m m' : M}
    (h : ∀ x ∈ S.corpus, S.predict m x = S.predict m' x)
    (hv : S.valid m = S.valid m') : accept S a m = accept S a m'
theorem accept_congr_incumbent ...                       -- same for the incumbent
theorem accept_perm_invariant ... (h : m.hidden.Perm m'.hidden) (hb : ...) :
    accept (wideSpec A target corpus) a m = accept (wideSpec A target corpus) a m'
```

Exact embeddings of the earlier models:
`predict_ofTiny` (all `x`) and `accept_ofTiny`. The wide gate on embedded two-unit nets
makes **exactly** the old gate's decisions. `predict_ofNeuron` embeds a ReLU *or
linear* neuron as a width-≤2 network, using `z = relu z − relu (−z)`.

**Checked witness that grows the architecture** (target
`relu(2x+1)+relu(−x+1)−2·relu(x−2)`, corpus `[−4,…,4]`, `Arch ⟨8, 32⟩`):
`wide_three_generations : CertifiedTrace spec3 3 gen0 gen3`, going from 0 to 1, 2 and 3
hidden units, with losses `34 → 21 → 6 → 0` (`wide_losses`). `gen3_exact` proves that
`gen3` equals the target on **all** of `Int`, and `gen3_terminal` that nothing is
accepted after it.

Blocked fixtures:
* `regressive_blocked`: loss 1 < 6, but it breaks the correct case `x = −4`.
* `outOfRange_blocked`: semantically identical to `gen3` on all inputs, but has a
  parameter 100.
* `overWidth_blocked`: perfect, but has 9 units when the maximum is 8.

Positive transform fixture: `permuted_gen3_accepted`.

### 2.3 Arbitrary depth (`ProofGatedDeep.lean`)

`DeepNet` has any number of ReLU layers of any widths and an affine read-out. The
evaluator is total. `valid` enforces consistent shapes, a depth bound, a width bound
and a parameter bound.

```lean
theorem predict_ofWide (m : WideNet) (x : Int) :
    predict (ofWide m) x = PCS.V2.ProofGatedWide.predict m x
theorem predict_deepen (Ls : List (List DNeuron)) (L : List DNeuron) (r : DNeuron) (x : Int) :
    predict ⟨Ls ++ [L, idLayer L.length], r⟩ x = predict ⟨Ls ++ [L], r⟩ x
theorem predict_deepen_ofWide (m : WideNet) (x : Int) : ... -- every WideNet has an exact depth-2 twin
```

`predict_deepen` is a depth-increasing self-modification that preserves the function on
every input. It relies on the fact that post-ReLU activations are nonnegative.

Checked chain on a genuinely two-hidden-layer network for `relu(|x| − 2)`:
`deep_two_generations : CertifiedTrace specD 2 dZero dFull`, with losses `6 → 3 → 0`.
`dFull_exact` holds for all `x`. Blocked fixtures: `dIllShaped_blocked` (computes the
target exactly but has inconsistent shapes) and `dTooDeep_blocked` (four layers when the
maximum is 3).

---

## 3. Priority C: from artifact to decision to commit to inference (`ProofGatedNetArtifacts.lean`)

Wire format: `PGSI2-WIDE|outBias|w₁|b₁|o₁|…`. The following are proved for every
`Arch`, target and corpus, and for networks of every admissible width.

```lean
theorem decode_encode (A : Arch) (m : WideNet) (h : valid A m = true) :
    decode A (encode m) = some m
theorem decode_iff (A : Arch) (raw : String) (m : WideNet) :
    decode A raw = some m ↔ valid A m = true ∧ encode m = raw
theorem encode_injective {m₁ m₂ : WideNet} (h : encode m₁ = encode m₂) : m₁ = m₂
theorem infer_encode (A : Arch) (m : WideNet) (h : valid A m = true) (x : Int) :
    infer A (encode m) x = some (predict m x)
theorem acceptWire_iff (c : Config) (oldRaw newRaw : String) :
    acceptWire c oldRaw newRaw = true ↔
      ∃ o n, encode o = oldRaw ∧ encode n = newRaw ∧ admissible c.spec o n
theorem acceptWire_encode (c : Config) (o n : WideNet) (ho : valid c.arch o = true)
    (hn : valid c.arch n = true) : acceptWire c (encode o) (encode n) = accept c.spec o n
theorem commit_refines {c : Config} {s s' : State} {p : Proposal}
    (h : tryCommit c s p = some s') :
    ∃ old cand : WideNet,
      encode old = s.active ∧ encode cand = s'.active ∧
      decode c.arch s.active = some old ∧ decode c.arch s'.active = some cand ∧
      admissible c.spec old cand ∧ s'.generation = s.generation + 1 ∧
      p.expectedGeneration = s.generation ∧ p.expectedActive = s.active ∧
      (∀ x : Int, infer c.arch s'.active x = some (predict cand x)) ∧
      (∀ x ∈ c.corpus, infer c.arch s.active x = some (c.target x) →
        infer c.arch s'.active x = some (c.target x))
theorem commit_complete (c : Config) (s : State) (old cand : WideNet)
    (hs : s.active = encode old) (hadm : admissible c.spec old cand) :
    tryCommit c s ⟨s.generation, s.active, encode cand⟩ =
      some ⟨s.generation + 1, encode cand⟩
theorem runCommits_invariant (c : Config) (ps : List Proposal) (s : State) (m₀ : WideNet)
    (h₀ : decode c.arch s.active = some m₀) :
    ∃ m, decode c.arch (runCommits c s ps).active = some m ∧
      s.generation ≤ (runCommits c s ps).generation ∧
      ((runCommits c s ps).generation - s.generation) + loss c.spec m ≤ loss c.spec m₀ ∧
      (∀ x ∈ c.corpus, correct c.spec m₀ x → correct c.spec m x)
```

`commit_refines` is the requested binding. The committed text is the canonical encoding
of exactly one valid network (by `encode_injective`). That network is the one the
checker certified, and it is the one whose predictions `infer` serves on every integer.
`decode_iff` shows that every field of the accepted artifact is covered: nothing in the
text is ignored, and the decoder adds nothing. `runCommits_invariant` covers arbitrary
proposal lists, including stale, forged and replayed ones.

Fixtures:
* `gen3_wire : encode gen3 = "PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2"`.
* `three_commits`: three string-level commits, derived from the model certificates via
  `commit_complete` without evaluating any strings.
* `served_after_three_commits`: correct on every `x`.
* `replay_rejected`: a stale replay is rejected.
* `boundary_fixtures`: weight 32 and −32 accepted; 33 and −33 rejected; `007`, `-0`, an
  incomplete unit, the wrong version tag and an empty trailing field all rejected.

**Formalized here vs. still open (host assumptions).** The state machine is a pure
mathematical object that stores exact text. File-system atomicity and immutability,
race freedom, SHA-256 collision resistance, signatures, anti-rollback anchoring,
executable authenticity, and the faithfulness of a Python/GPU runtime that serves the
model are **not** proved. They do not appear as axioms anywhere. Any deployment
statement would need them as explicit hypotheses.

---

## 4. Priority D: limits and counterexamples (`ProofGatedLimits.lean`)

```lean
-- every infinite gated run, under ANY proposer sequence, is eventually constant
theorem gated_run_stabilizes (P : Nat → M → M) (m : M) :
    ∃ N, ∀ k, N ≤ k → runSched S P 0 k m = runSched S P 0 N m
-- corpus blindness, universally, for width-n networks
theorem blind_extension_accepted (A : Arch) (target : Int → Int) (corpus : List Int)
    (a b : WideNet) (c k : Int) (hcorp : ∀ x ∈ corpus, x ≤ c)
    (hacc : accept (wideSpec A target corpus) a b = true)
    (hvalid : valid A (addUnit b ⟨1, -c, k⟩) = true) :
    accept (wideSpec A target corpus) a (addUnit b ⟨1, -c, k⟩) = true ∧
    ∀ x, c < x → predict (addUnit b ⟨1, -c, k⟩) x = predict b x + k * (x - c)
theorem multilayer_ood_regression :
    accept spec3 gen2 oodCandidate = true ∧ loss spec3 oodCandidate = 0 ∧
    (predict gen2 20 - target3 20).natAbs = 36 ∧
    (predict oodCandidate 20 - target3 20).natAbs = 480
theorem gate_cannot_separate :
    accept spec3 gen2 gen3 = true ∧ accept spec3 gen2 oodCandidate = true ∧
    (∀ x, predict gen3 x = target3 x) ∧ predict oodCandidate 20 ≠ target3 20
theorem local_trap :
    loss spec3 trapM = 6 ∧ (∀ c ∈ neighbors trapM, accept spec3 trapM c = false) ∧
    accept spec3 trapM gen3 = true ∧ loss spec3 gen3 = 0
theorem local_proposer_frozen (P : Nat → WideNet → WideNet)
    (hloc : ∀ i, P i trapM ∈ neighbors trapM) (k : Nat) :
    runSched spec3 P 0 k trapM = trapM
```

How to read these results:
* **Finite improvement.** At most `loss initial` modifications are ever accepted
  (`runSched_count_bound`, `trace_length_bound`, `runCommits_invariant`), and every
  infinite run stabilizes. Under a bounded natural-valued loss there is no everlasting
  self-improvement.
* **Out-of-corpus regression exists for the multilayer model too.** An accepted,
  corpus-perfect update of a multi-unit network raises the error on the *same* target
  at the held-out input 20 from 36 to 480. A version that is exact on all of `Int` is
  accepted by the identical check. `blind_extension_accepted` shows this is not a
  quirk of one example. For any accepted step on a corpus bounded by `c`, every
  architecture-valid blind extension is also accepted and changes held-out predictions
  by an arbitrary in-range multiple of `x − c`.
* **Frontier trap.** The preservation requirement can trap a local proposer.
  `trapM` (which equals `gen2` plus a dead unit) has all 20 `±1` single-parameter edits
  rejected: any edit that wakes the dead unit breaks a previously correct case. Yet a
  three-parameter edit to the perfect `gen3` is accepted. Any proposer limited to local
  edits stays at `trapM` forever. (`perfect_valid_always_accepted` shows the gate itself
  never blocks the optimum. The trap comes from proposer locality combined with the
  frontier constraint.)

### Why a certificate about a fixed benchmark does not imply general improvement

Every acceptance theorem above concerns one fixed, finite corpus, one fixed target
function, and one fixed natural-valued error. Three results bound what follows:
`accept_congr_candidate` (the gate depends only on corpus values and validity),
`blind_extension_accepted` (held-out behaviour is unconstrained) and
`gated_run_stabilizes` (progress is finite). Together they show the certificates carry
**no** information about inputs outside the corpus, other targets, reasoning ability,
scientific correctness, or the ability to invent future improvements. A fixed-policy
preservation theorem, such as `runSched_preserves`, says that the *gate* never loses a
corpus point. It does not say that a proposer becomes better at proposing, and nothing
here supports the claim that self-modification "accelerates". We make no claim about
general intelligence.

---

## 5. Remaining proof obligations and unsupported claims

1. The original `PGSI1` roundtrip for negative parameters depends on the opaque
   `String.Internal.append` (assumption `happ`, a runtime trust assumption) and on core
   `String.toInt?` on canonical strings (assumption `hparse`, an open library-level
   proof). The `PGSI2` codec has neither dependency and is fully proved.
2. A codec for `DeepNet` artifacts has not been written. The refinement chain of §3 is
   proved for `WideNet`. The same pattern (`toInts`/`ofInts` and `ProofGatedCodec`)
   applies, but extending it is future work.
3. Deep-network transforms: identity-layer insertion is proved. Permutation invariance
   of a hidden layer inside a deep network (which requires permuting the next layer's
   weight columns) is not formalized.
4. Host and deployment properties (§3) are out of scope and not assumed.
5. All concrete witnesses are small, deliberately constructed integer models. They
   show that the theorems are non-vacuous; they are not evidence of performance at
   scale.

## Addendum (2026-10-17): integration replay and all-integer no-forgetting checker

See `PCS_PROOF_GATED_V4_INTEGRATION.md` for the file manifest with Git blob SHA-1s, the
one-command replay `scripts/proof_gated_ci.sh` and the generated codec vectors in
`fixtures/proof_gated/`. It also describes the new module `PCS/V2/ProofGatedNoForget.lean`:
an exact decision procedure, proved sound and complete with counterexample extraction, for
"the candidate loses no integer on which the incumbent was correct". It covers
one-input, arbitrary-width integer ReLU networks and is checked over all of \(\mathbb{Z}\).
