# PCS proof-gated V4: integration manifest and replay (response to the 2026-10-17 audit)

## 1. The archive you inspected was stale. This project tree is the final export.

This project tree contains the corrected `PGSI1` codec migration. You can check it directly:

* `PCS/V2/ProofGatedArtifacts.lean` defines `encode` with `ProofGatedCodec.renderInt` and
  `joinFields`, and `parseComponents` with `splitFields` and `parseInt`. `decode` is built
  on these. The original definitions are kept as `encodeLegacy`, `parseComponentsLegacy`
  and `decodeLegacy`. They are not used by `decode`, `acceptWire` or `main`.
* `decode_encode_of_bounded (m) (h : valid m = true) : decode (encode m) = some m` has no
  other hypotheses.
* `PCS/V2/ProofGatedAudit.lean` contains **125** `#print axioms` entries.
* `PCS/V2/ProofGatedV1Analysis.lean` refers to the legacy names
  (`parseComponentsLegacy_encodeLegacy`, `encode_eq_encodeLegacy_of_nonneg`,
  `encode_eq_encodeLegacy_of_append_spec`, `decode_encodeLegacy_of_append_spec`).

Git blob SHA-1s from `git hash-object`. The seven research files you listed match your
table exactly. The files that changed in the final follow-up have new identifiers.

| File | Bytes | Git blob SHA-1 | Status vs. your archive |
|---|---:|---|---|
| `PCS/V2/ProofGatedGeneric.lean` | 15176 | `c1b7ca7a8c0ce585bb15d41d2cc8146267e26298` | identical |
| `PCS/V2/ProofGatedWide.lean` | 17512 | `445996b49892ba1ff72250c29051bda4798d3040` | identical |
| `PCS/V2/ProofGatedDeep.lean` | 9269 | `07db8fe1754c7d8b06903e80d98cf0b4a8922813` | identical |
| `PCS/V2/ProofGatedCodec.lean` | 16378 | `9e92029a84d6d14fdd1d9342cb039191bf300cf4` | identical |
| `PCS/V2/ProofGatedNetArtifacts.lean` | 16409 | `21f6af46db0937bf247cc4f292d73ee98f300284` | identical |
| `PCS/V2/ProofGatedLimits.lean` | 11337 | `62cd9896ce41e982e04ba0fc1707e5edfafc437c` | identical |
| `PCS/V2/ProofGatedV1Analysis.lean` | 21615 | `7ca4a9310f155480bc0bd4f8b0e79ca758670440` | **changed** (legacy names) |
| `PCS/V2/ProofGatedArtifacts.lean` | 9685 | `5332de68e13b2c43b9653d610bed442c19e70ac6` | **changed** (codec migration) |
| `PCS/V2/ProofGatedInference.lean` | 3063 | `d190fb6ee6d73290e36f307184a1aaf4cfdf6db1` | **changed** (+`infer_encode`, `infer_eq_some_iff`) |
| `PCS/V2/ProofGatedAudit.lean` | 8689 | `be735108f2497c784590241c3761b30f45c6bbaf` | **changed** (125 entries) |
| `PCS/V2/ProofGatedSelfImprovement.lean` | 8867 | `4388f794c5633affd0e23b3e0aa7aad3b4d88cd6` | unchanged by V4 |
| `PCS/V2/ProofGatedSymbolic.lean` | 1419 | `495c730fede01038be24b99c9fb9f89d26a252fe` | unchanged by V4 |
| `PCS/V2/ProofGatedPromotion.lean` | 3278 | `37c095be03230b77514f9469ff56d3da87da3347` | unchanged by V4 |
| `PCS/V2/ProofGatedMultilayer.lean` | 8145 | `75a6e6e799533d1ba2ab75f13b62590bb291f746` | unchanged by V4 |

New in this session (described in §3 and §4):

| File | Purpose |
|---|---|
| `PCS/V2/ProofGatedNoForget.lean` | all-integer no-forgetting checker with soundness and counterexample extraction |
| `PCS/V2/ProofGatedNoForgetAudit.lean` | 19-entry axiom audit for the module above |
| `scripts/proof_gated_vectors.lean` | test-vector generator and replayer (`PGSI1` and `PGSI2-WIDE`) |
| `scripts/proof_gated_ci.sh` | one-command replay: build, token scan, axiom audit, vectors, file-authority tests |
| `ci/proof-gated-v4.yml` | GitHub Actions template (copy to `.github/workflows/`; it assumes the `formal/` layout) |
| `fixtures/proof_gated/` | the generated vectors (52 files) |

`PCS.lean`, `lakefile.toml`, `lean-toolchain`, `lake-manifest.json` and all non-`ProofGated`
modules were left unchanged. The new modules are built by naming them explicitly. They are
not added to the `PCS` umbrella. Add them there if you want them in the default target.

**Semantics migration note.** The `ProofGatedArtifacts.lean` change replaces the code the
`PGSI1` authority executes. It is not cosmetic. The bytes of every valid artifact are
unchanged, which the vectors below check at runtime and `ProofGatedV1Analysis` proves (see
§2). Even so, it should go in as an explicit, separately reviewed commit, as you suggest.

## 2. What was re-run here (Lean 4.28.0, project toolchain)

`./scripts/proof_gated_ci.sh` exits 0. It runs these steps:

1. `lake build` of all 14 `ProofGated*` modules plus both audit files. This succeeds. The
   only warnings are three unused variables in the unchanged `ProofGatedPromotion.lean`.
2. A scan of `PCS/V2/ProofGated*.lean` and the vector script for `sorry`, `admit`,
   `native_decide`, `unsafe`, `implemented_by`, `extern` and `axiom` declarations. Nothing is
   found.
3. The axiom audit. `ProofGatedAudit.lean` has 125 entries and `ProofGatedNoForgetAudit.lean`
   has 19. The union of axioms used is `{propext, Classical.choice, Quot.sound}`, with no
   `sorryAx`, `Lean.ofReduceBool` or `Lean.trustCompiler`.
4. The codec vectors, with 8,502 checks passing (details below).
5. The file-based `PGSI1` authority (`lake env lean --run PCS/V2/ProofGatedArtifacts.lean old new`):
   * 3 accepting pairs return `ACCEPT` with exit 0;
   * 3 rejecting pairs return `REJECT:invalid_artifact_or_update` with exit 1. These are a
     regression, a no-op and a loss increase;
   * a missing file and a directory argument return `REJECT:read_failure` with exit 2;
   * one argument and zero arguments return `REJECT:bad_arity` with exit 2;
   * an empty file, a trailing newline and a UTF-8 BOM each return a reject with exit 1;
   * a symlink to a valid artifact is **accepted**. The reader follows symlinks, and the
     decision is about the bytes it read. This is the boundary already documented in the
     module header (no symlink or TOCTOU safety).

Details of the vector checks (`fixtures/proof_gated/`):
* `pgsi1_canonical.tsv` lists all \(2 \times 65 \times 65 = 8{,}450\) canonical artifacts for
  `R`/`L` and \((w,b) \in [-32,32]^2\). Each line has the form `act<TAB>w<TAB>b<TAB>wire`. The
  boundary weights \(-32\) and \(32\) are included. The replay regenerates the table and
  compares it byte for byte. For each artifact it checks `decode (encode m) = some m`, and it
  runs the **legacy** `encodeLegacy`/`decodeLegacy` and checks equal bytes and equal
  decoding. This legacy comparison is a runtime test of compiled code. It does **not**
  discharge the opaque `String.Internal.append` assumption, which stays a separate, explicit
  hypothesis in `ProofGatedV1Analysis`
  (`happ : ∀ s, String.Internal.append "-" s = "-" ++ s` in the `*_of_append_spec` theorems).
* `pgsi1_negative/neg_*.txt` holds 28 vectors that must be rejected by both the new decoder
  and the legacy decoder: `33`/`-33` out of range, `-0`, `00`, `01`, `-01`, `+1`, embedded
  spaces, a trailing `|`, a leading `|`, a missing field, an empty field, the activations
  `X`, `r` and `RR`, the wrong tags `PGSI2` and `pgsi1`, a trailing `\n`, `--1`, `1-`, `0x1`,
  `1.0` and the empty file. There is one file per vector, so exact bytes are preserved.
* `pgsi1_pairs/` holds the accept and reject file pairs above.
* `pgsi2_wide_canonical.txt` holds 8 `PGSI2-WIDE` roundtrip fixtures, from the empty network
  up to the boundary network `⟨[⟨-32,32,-32⟩,⟨32,-32,32⟩],0⟩`. Each is checked for exact
  encoding and `decode arch3` roundtrip.
* `pgsi2_wide_negative/` holds 10 must-reject `PGSI2-WIDE` vectors, including an over-width
  network.

I tested that the replay catches changes: after a negative vector was overwritten with a
valid artifact, the check failed with exit 1.

**Items in your list that this tree cannot carry out.** It has no Python code and no
production CAS or loader. That affects items 5 (Python `wire_bytes`) and 6 (two-generation
CAS promotion and the sealed-inference loader). For item 5, compare your Python
`wire_bytes(act, w, b)` against column 4 of `pgsi1_canonical.tsv`. Columns 1–3 give the
expected decoding, so the same table also gives the decoding direction. For item 6, the
`pgsi1_pairs/` files are the exact new-codec bytes to feed into the existing promotions.

## 3. New formal result: exact all-integer no-forgetting checker (`ProofGatedNoForget`)

This is the "ideal next formal result" from your assessment, done in Lean for
one-input exact integer ReLU networks of **any width and any parameter size**
(`WideNet`, \(x \mapsto \sum_u o_u\,\mathrm{relu}(w_u x + b_u) + c\)). The incumbent `a`,
the candidate `m` and the target `t` are all such networks. The candidate *forgets* at
\(x \in \mathbb{Z}\) when \(a(x) = t(x)\) and \(m(x) \ne t(x)\).

**How the checker works.**
* A unit \(o\,\mathrm{relu}(wx+b)\) with \(w \ne 0\) has zero second difference
  \(h(y-1)+h(y+1) = 2h(y)\) at every integer \(y \notin \{q-1, q, q+1\}\), where
  \(q = \lfloor -b/w \rfloor\) (`relu_secondDiff_of_not_kink`). The proof writes
  \(-b = wq + r\) with \(0 \le r < |w|\) and shows that \(w(y-1)+b\), \(wy+b\) and
  \(w(y+1)+b\) all have the same sign.
* A function with zero second difference strictly inside \([lo, hi]\) is affine on
  \([lo, hi]\) (`affine_of_secondDiff`).
* On one affine piece, the incumbent's error \(F\) is either identically zero, in which
  case a forgetting point lies at the anchor \(c\) or at \(c+1\), or it has at most one
  integer zero. That zero is computed exactly by integer division (`rootFrom`,
  `forget_on_piece`).
* The candidate inputs are the anchors \(0\) and all kink points \(k\), together with
  \(k-1\), \(k+1\) and the roots read off at the anchors \(k-1\) and \(k\). Their number is
  linear in the total number of hidden units. The checker `findForgetting` returns the first
  candidate input that is forgotten.

**Theorems.** All are kernel-checked and depend on no hypotheses beyond the stated ones.

```lean
theorem findForgetting_sound (a m t : WideNet) (x : Int)
    (h : findForgetting a m t = some x) :
    predict a x = predict t x ∧ predict m x ≠ predict t x
theorem noForgetting_sound (a m t : WideNet) (h : noForgetting a m t = true) :
    ∀ x : Int, predict a x = predict t x → predict m x = predict t x
theorem noForgetting_iff (a m t : WideNet) :
    noForgetting a m t = true ↔
      ∀ x : Int, predict a x = predict t x → predict m x = predict t x
theorem findForgetting_complete (a m t : WideNet)
    (h : ∃ x, predict a x = predict t x ∧ predict m x ≠ predict t x) :
    ∃ x, findForgetting a m t = some x
theorem acceptNF_sound ... : admissible (wideSpec A (predict t) corpus) a m ∧
      ∀ x : Int, predict a x = predict t x → predict m x = predict t x
theorem nfTrace_preserves (h : NFTrace A t corpus n a b) :
    ∀ x : Int, predict a x = predict t x → predict b x = predict t x
theorem nfTrace_loss (h : NFTrace A t corpus n a b) :
    loss (wideSpec A (predict t) corpus) b + n ≤ loss (wideSpec A (predict t) corpus) a
```

Together these give an exact decision procedure for "no correct integer is lost", over
**all** of \(\mathbb{Z}\) rather than a finite corpus. A counterexample is extracted whenever
one exists. Along any chain accepted by `acceptNF`, the set of integers handled correctly can
only grow, and the chain length is bounded by the starting corpus loss.

**Checked fixtures** (by `decide`; these use no axioms):
* `blindForget` is the perfect `gen3` plus a unit `⟨-1,-10,5⟩` that is active only for
  \(x \le -10\). The corpus gate accepts it (`blindForget_corpus_accepted`). The checker
  returns the forgotten input \(-12\) (`blindForget_caught`), and `acceptNF` rejects the
  step.
* The exact step `gen2 ↦ gen3` and the full growth chain `gen0 → gen1 → gen2 → gen3` pass
  `acceptNF` (`growth_chain`).
* **Limitation** (`ood_not_forgetting`): `oodCandidate` from `ProofGatedLimits` is wrong at
  \(x=20\), but it forgets nothing relative to `gen2`, so `acceptNF` accepts it. No-forgetting
  is a non-regression guarantee. It is not a generalisation guarantee: the integers a
  candidate gets right can grow without the candidate getting closer to the target elsewhere.

**Scope.** The checker covers one input, one hidden layer, and a target given as such a
network. It does not cover `DeepNet`. In depth \(\ge 2\) the bend points of later layers are
not determined unit by unit, so a different region enumeration would be needed. It also does
not cover non-network targets.

## 4. Separating what is proved from what is not

Proved (kernel-checked, axioms within `{propext, Classical.choice, Quot.sound}`): the
statements in `ProofGatedAudit.lean` (125) and `ProofGatedNoForgetAudit.lean` (19).

Tested, not proved: byte equality of the new and legacy `PGSI1` encoders on the 8,450
artifacts, and legacy decoding of the new bytes. These run compiled code that goes through
the opaque `String.Internal.append`. The CLI exit-code behaviour is also tested only.

Not addressed and outside the formal model: OS-level file integrity, symlink and TOCTOU
safety, process isolation, an independent production loader for `PGSI2-WIDE`, and any claim
about generalisation, real-world correctness, or accelerating or recursive intelligence.
Certified gains on a finite corpus, and even all-integer no-forgetting, do not imply any of
these.
