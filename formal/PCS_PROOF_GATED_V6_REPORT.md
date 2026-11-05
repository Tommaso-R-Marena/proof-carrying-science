# PCS V6 — Proof-Carrying Execution and Certified Neural Self-Modification

Lean 4.28.0, no Mathlib, no `sorry`/`admit`/`native_decide`/`unsafe`/`implemented_by`/`extern`,
no new axioms. Every theorem named below is kernel-checked. The complete axiom audit
(`PCS/V2/ProofGatedFullAudit.lean`, 556 entries) shows that only `propext`,
`Classical.choice` and `Quot.sound` occur.

All V5 modules, theorem statements and the PGSI1 / PGSI2-WIDE semantics are unchanged.
No existing `.lean` module, `PCS.lean`, `lakefile.toml` or production authority module was
modified; the only change to an existing Lean file is the regenerated audit
(`ProofGatedFullAudit.lean`, additions only).

## 0. What is new (8 modules, 2,397 lines)

| Module | Content |
|---|---|
| `PCS/V2/ProofGatedBytes.lean` | byte-level (`List UInt8`) canonical PGSI2-WIDE format, decoder, inference |
| `PCS/V2/ProofGatedCertificate.lean` | PGSC6 witness certificates, the independent checker, generator, soundness, completeness, binding rejections, verdict-only counterexample |
| `PCS/V2/ProofGatedCertCodec.lean` | canonical byte format of certificates, byte-level checker |
| `PCS/V2/ProofGatedProtocol.lean` | promotion state machine over bytes, decision log, adversarial sequences, completeness, digest-identity hypothesis |
| `PCS/V2/ProofGatedInterpreter.lean` | independent reference interpreter, fixed-width (`int64`) runtime model, 35 test vectors |
| `PCS/V2/ProofGatedDeepCertGen.lean` | deep-network certificate generator and minimiser, tight size bounds, parameterised sawtooth lower bound |
| `PCS/V2/ProofGatedV6Limits.lean` | limitations (outside-interval degradation, local vs coordinated moves, dead ends, interval mismatch) |
| `PCS/V2/ProofGatedV6EndToEnd.lean` | one composed theorem from certificate bytes to executed predictions |

Plus `scripts/proof_gated_v6_vectors.lean` (runtime fixtures and cross-checks) and the
fixtures `fixtures/proof_gated/v6_interp_vectors.tsv`, `fixtures/proof_gated/v6_certs/*`.

## 1. Priority 1 — independently checkable certificates

### 1.1 Format PGSC6 (`Cert`)

A certificate binds:

| field | meaning |
|---|---|
| `version` | must be `6` |
| `predicate` | must be `1` = "strong gate A ∧ B ∧ C" (`StrongAdmissible`) |
| `maxWidth`, `bound` | architecture limits |
| `target` | the target network (complete parameters) |
| `corpus` | the benchmark inputs |
| `lo`, `hi` | the robustness interval |
| `generation` | the expected current generation |
| `incumbent` | the **complete canonical incumbent artifact bytes** |
| `candidate` | the **complete canonical candidate artifact bytes** |
| `gainWitness` | a corpus input that becomes newly correct (A) |
| `incLoss`, `candLoss` | claimed corpus losses (A) |
| `errWitness`, `errLevel` | an input of `[lo,hi]` where the incumbent's error is `errLevel` (C) |

The predicate being certified is fixed by the predicate id and is exactly
`StrongAdmissible S o n` (V5): corpus admissibility, universal no-forgetting
`∀ x : Int, o x = t x → n x = t x`, and `∀ B, ErrBound o t lo hi B → ErrBound n t lo hi B`.

Byte format (`ProofGatedCertCodec`): the ASCII bytes of
`PGSC6|version|predicate|maxWidth|bound|generation|lo|hi|gainWitness|incLoss|candLoss|errWitness|errLevel|#corpus|corpus…|#target|target…|#inc|inc bytes…|#cand|cand bytes…`
with canonical decimals and length prefixes; the two artifacts are embedded byte for
byte. The first step of the robust chain (`cert1_text`, 225 bytes):

```
PGSC6|6|1|8|32|0|-1000000000|1000000000|-1|34|26|-1000000000|1000000001|9|-4|-3|-2|-1|0|1|2|3|4|10|0|2|1|1|-1|1|1|1|-2|-2|12|80|71|83|73|50|45|87|73|68|69|124|48|19|80|71|83|73|50|45|87|73|68|69|124|48|124|45|50|124|48|124|49
```

(`80|71|83|73|50|45|87|73|68|69|124|48` is the incumbent artifact `PGSI2-WIDE|0`.)

### 1.2 The checker and its theorems

`checkCert S g active c` (pure, total, executable):
1. header: version, predicate, configuration equal to the deployment `S`, `generation = g`,
   `incumbent = active` (byte equality);
2. both artifacts decode under `S.arch` (`decodeBytes`);
3. witness: gain witness in the corpus, wrong for `o`, right for `n`; recomputed losses
   equal the claimed ones and decrease; `noForgetting o n t`; if `lo ≤ hi`: `errWitness`
   in `[lo,hi]`, `errAt o t errWitness = errLevel`, and `checkErrBound n t lo hi errLevel`.

| theorem | statement |
|---|---|
| `checkCert_sound` | accepted ⇒ header holds and `∃ o n`, the two byte strings decode to `o`, `n`, `encodeBytes o = active`, `encodeBytes n = c.candidate`, `StrongAdmissible S o n` |
| `checkCert_complete` | `StrongAdmissible S o n` ⇒ `checkCert S g (encodeBytes o) (genCert S g o n) = true` |
| `checkCert_iff_gate` | some certificate for `(active, cand)` is accepted ⇔ both decode and the pair is strongly admissible |
| `checkCert_version_rejected`, `…_predicate_…`, `…_config_…`, `…_stale_…`, `…_substituted_…`, `…_malformed_candidate`, `checkCert_candidate_swap` | binding rejections |
| `decodeCert_encodeCert`, `decodeCert_iff`, `encodeCert_injective` | canonical certificate bytes |
| `checkCertBytes_sound`, `checkCertBytes_complete`, `checkCertBytes_malformed` | the same at byte level |

**What the checker does not repeat.** The untrusted generator searches for the
incumbent's worst-case error (`maxAbsErr` over all breakpoint probes) and its argmax;
the checker evaluates the incumbent at a single point. The corpus-preservation
sub-check of A is not executed at all, because it is implied by B. The checker still
runs the exact no-forgetting decision procedure and the candidate's bound check;
no cheaper witness for universal no-forgetting is provided (open, see §7).

### 1.3 Verdicts versus witnesses

`verdict_only_unsound`: a format that records only `verdict = true` next to bound and
decodable artifacts lets a trusting checker accept replacing the perfect network by the
zero network, which is not strongly admissible. `witness_rejects_verdict_example`: for
the same artifacts, **every** PGSC6 certificate, whatever the witness, is rejected.

## 2. Priority 2 — bytes to executed predictions

### 2.1 Byte format (`ProofGatedBytes`)

`encodeBytes m` = ASCII bytes of the canonical PGSI2-WIDE text. `decodeBytes A bs` rejects
any byte `≥ 128`, then runs the verified text decoder.

* `asciiChars_encodeChars`: canonical text is ASCII (proved, not assumed);
* `decodeBytes_encodeBytes`: roundtrip for every valid network of every width;
* `decodeBytes_iff`: `decodeBytes A bs = some m ↔ valid A m ∧ encodeBytes m = bs`. Hence
  malformed encodings, extra or missing fields, non-canonical integers (`007`, `-0`, `+1`),
  separators, whitespace, newline, BOM and high bytes, out-of-range parameters and
  over-width networks are all rejected without case analysis. Literal fixtures:
  `malformed_fixtures`, `bom_rejected`, `high_byte_rejected`;
* `encodeBytes_injective`, `decodeBytes_unique`;
* `decodeBytes_arch_mono` and `arch_mismatch_fixture`: acceptance is monotone in the
  architecture bound, and the converse fails;
* `inferBytes_encodeBytes`, `inferBytes_sound`, `inferBytes_none`.

### 2.2 State machine (`ProofGatedProtocol`)

State `⟨generation, active : Bytes⟩`; input: arbitrary certificate byte strings; `step`
decodes, checks, and on acceptance installs exactly `c.candidate`. Each step logs
`⟨generation, activeBefore, certificate, decision, activeAfter⟩`. Serving is
`serve S s x = inferBytes S.arch s.active x`.

| theorem | content |
|---|---|
| `step_decision` | the decision is exactly `checkCertBytes` |
| `step_accept_refines` | accepted ⇒ certificate bytes, checker acceptance, decoded `o ↦ n`, `StrongAdmissible`, new state `⟨g+1, encodeBytes n⟩`, serving `predict n` on every integer |
| `step_reject`, `step_malformed`, `step_config_mismatch`, `step_stale`, `step_substituted` | rejected ⇒ state unchanged |
| `run_invariant` | arbitrary sequences: active bytes always decode; universal no-forgetting relative to the initial model; all initial error bounds on `[lo,hi]` kept; `#accepted + loss ≤ initial loss`; `generation = initial + #accepted` |
| `serve_run`, `serve_noForget`, `serve_error_le` | observational consequences for what is served |
| `run_log_sound`, `run_log_chain`, `run_log_generations` | every logged decision is the checker's decision on the logged data; entries chain; final identity is the last logged one |
| `run_complete` | every admissible chain is realised by generated certificates, ending at the exact bytes of the last model |
| `wide_chain_run`, `adversarial_run` | executed fixtures (garbage, tampered and replayed certificates interleaved with genuine ones: exactly the 3 genuine ones are accepted) |

### 2.3 Host assumptions are hypotheses

`checkCertH H` identifies the incumbent by a digest `H : Bytes → D`.
`hash_identity_step`: **if** `∀ b, H b = H s.active → b = s.active` (no collision with the
active artifact), the digest step equals the byte step. `colliding_hash_breaks_gate`: with
a colliding digest, a certificate for a substituted incumbent is accepted, and the committed
candidate is not strongly admissible relative to the actual active model. No property of
SHA-256, any signature scheme or any filesystem is assumed or proved.

## 3. Priority 3 — deep-network certificates (`ProofGatedDeepCertGen`)

* `genDeepCert` (bisection; unit cells when fuel runs out) — `genDeepCert_ok`: always accepted
  by the verified checker `chainOK` and covers exactly `[L,U]`, for networks of any depth;
  `genDeepCert_isMax`: hence the exact worst-case error.
* `minimizeCert` (greedy cell merging) — `minimizeCert_ok`, `minimizeCert_length`.
* `cert_length_le`: every valid certificate has at most `U − L` points.
* `cert_length_of_full`: a valid certificate containing all interior integers has exactly
  `U − L` points.
* `sawNet k` = width-2 sawtooth with `k+1` hidden layers, fold constants `2^(k−1),…,1`
  (`saw6_eq : saw6 = sawNet 5`); `sawNet_paramCount`: `6k + 7` parameters.
  `sawNet_predict`: on `[−2^k, 2^k]` it equals `(|x|+1) mod 2`;
  `sawNet_all_kinks`: nonzero second difference at every interior integer;
  **`sawNet_cert_length`**: for every `k ≥ 1` and every target, every valid certificate on
  `[−2^k, 2^k]` has exactly `2^(k+1)` points. This proves the V5 open item for this family:
  the certificate size is exponential in depth, and the trivial upper bound is attained.
* Positive example: `dFull_gen_length` (bisection: 41 points on `[−10^6, 10^6]`),
  `dFull_gen` (after minimisation: `[−2, 0, 2, 10^6]`), `dFull_gen_checked`.
  `saw3_gen_length`: on the sawtooth, the generator returns the full enumeration (16).

The lower bound applies to this certificate language (affine cells verified by symbolic
propagation). Other evidence formats (e.g. symbolic descriptions of periodic structure)
are not ruled out.

## 4. Priority 4 — interpreter correspondence (`ProofGatedInterpreter`)

* `interpBytes`: a second evaluator that never builds a `WideNet`. It checks the
  architecture on the integer vector (`intsOK`) and folds over `w, b, o` triples with an
  accumulator and an explicit `if 0 < z then z else 0`.
  **`interpBytes_eq_inferBytes`**: for every architecture, every byte string and every
  integer, it returns exactly `inferBytes` (including `none`).
* Test vectors (`vectors`, 35): signed parameters, zero activation at the exact kink,
  negative weights, bound edges `±32`, width 8 accepted and width 9 rejected, out-of-range
  parameters, truncated triple, `007`, `-0`, `+1`, trailing pipe, empty field, space,
  newline, wrong or lower-case tag, empty input, UTF-8 BOM, high byte, NUL byte,
  inputs `±10^12`, and a permuted model. `vectors_interp` and `vectors_infer` are
  kernel-checked; `perm_agrees` proves the permuted artifact agrees on **all** integers.
  Exported: `fixtures/proof_gated/v6_interp_vectors.tsv` (hex bytes).
* Fixed-width runtimes: `predictK h` wraps every intermediate into `[−h, h)`.
  `predictK_eq_predict`: under `NoOverflow A X h`, i.e. `B·X + B < h` and
  `maxWidth·B·(B·X+B) + B < h`, it equals `predict` for every valid network and every
  `|x| ≤ X`. `int64_safe`: width ≤ 1024, `|param| ≤ 32768`, `|x| ≤ 32768` is overflow-free
  in `int64`. `int64_mismatch`: see §5.

### What an external (Python / compiled) runtime must demonstrate

A proof about Lean's `interpBytes` does not certify another program. To claim
correspondence, an external runtime `R` must establish, for the deployed architecture `A`:
1. **Decoder equivalence**: for every byte string `bs`, `R` accepts `bs` iff
   `decodeBytes A bs ≠ none`, and then uses exactly the decoded parameters. Minimum
   evidence: all 35 vectors of `v6_interp_vectors.tsv`, plus the PGSI2-WIDE negative
   fixtures; full evidence requires a proof (or a verified extraction) of this statement.
2. **Arithmetic**: either arbitrary-precision integers, or a proof that `NoOverflow A X h`
   holds for its register width `h` **and** that every served input satisfies `|x| ≤ X`
   (it must reject larger inputs). Floating point does not satisfy this without a further
   rounding analysis.
3. **Evaluation**: `R(bs, x) = predict m x` for the decoded `m`; ReLU must return exactly
   `0` at `z = 0`, and the sum order is irrelevant only for exact integers.
4. **Identity binding**: the bytes `R` executes are byte-identical to the protocol's
   `active` (the guarantees are about those bytes, not about a file name, path or digest,
   unless the digest hypothesis of §2.3 is separately justified).
5. **Configuration binding**: `R` uses the same architecture as the verifier.
Passing the vectors is evidence of correspondence on those vectors only.

## 5. Priority 5 — limits and counterexamples

| theorem | finding |
|---|---|
| `outside_unbounded` | strongly accepted on `[0, 10^9]`, yet error `N` at `x = −N` for every `N`, while the incumbent's error is `1` at every integer |
| `all_single_coordinate_moves_rejected` / `coordinated_move_accepted` | every change of a single coordinate of the parameter vector, to any integer, is rejected; a two-coordinate change is accepted (universal over all values, not only ±1 as in V5's `local_trap`) |
| `sawNet_cert_length` | exponential certificate evidence in depth |
| `dead_end`, `dead_end_escaped_by_width` | a strongly accepted step leads to a model with loss 1 from which **no** network is accepted (proof by exhaustive enumeration of the 84 valid networks plus validity); allowing width 2 removes the dead end |
| `int64_mismatch` | verification in exact integers vs `int64` execution: a strongly accepted, exactly-correct network is served with error `2^64` at `x = 2^62 ∈ [lo,hi]` |
| `interval_mismatch` | accepted on `[−4,4]`, worst error on `[−10^9,10^9]` rises from 1000000001 to 1999999996 |
| `step_config_mismatch`, `checkCert_config_rejected` | the checker refuses certificates for other configurations; the verifier and the runtime must still agree on the configuration (`arch_mismatch_fixture`) |

**Interpretation.** These are statements about a fixed finite corpus, a fixed target
network and a fixed interval. Accepted chains are mathematically non-regressing in the
three stated senses and have length at most the initial loss. Nothing here establishes
scientific truth of a model, real-world safety, or recursive improvement of an agent's
ability to find improvements (`dead_end` shows the opposite can happen).

## 6. End-to-end theorem

`ProofGatedV6EndToEnd.v6_end_to_end`: from any state whose active bytes decode to `m₀`,
for **any** list of certificate byte strings, the final active bytes are the canonical
encoding of a valid `m`. The reference interpreter on those bytes returns `predict m x`
for all `x`. Also: universal no-forgetting relative to `m₀`; every served error on
`[lo,hi]` is at most `maxAbsErr m₀`; `#accepted + loss m ≤ loss m₀`; the generation counts
acceptances; every log entry is justified by the checker; under `NoOverflow`, a
fixed-width runtime computes `predict m` exactly.
`v6_end_to_end_complete`: every admissible chain is realised.

## 7. Open obligations (not proved)

* A cheaper *witness* for universal no-forgetting; the checker re-runs the exact
  procedure, which is linear in the total number of units.
* Certificates for multi-input networks; deep-network no-forgetting.
* Lower bounds for certificate languages other than affine cells.
* Correspondence of any external runtime (obligations listed in §4).
* Storage, atomic rename, rollback protection, signatures and hash collision resistance:
  outside the model (digest identity appears only as a hypothesis).

## 8. Execution record

Commands, all run from the project root:

```
bash scripts/proof_gated_ci.sh                  # full V5 + V6 suite
bash scripts/proof_gated_package.sh             # builds dist/pcs_proof_gated_v6.tar.gz
bash scripts/proof_gated_verify_archive.sh      # re-extracts into a clean dir, rebuilds, reruns CI
```

CI result (`results/proof_gated_ci_results.json`, exit 0):
* build: 30 modules. The only warnings are 3 pre-existing unused variables in
  `ProofGatedPromotion.lean`;
* forbidden-token scan clean on all `PCS/V2/ProofGated*.lean` and the three vector scripts;
* axiom audits: 125 + 19 + 101 + 556 entries. Of the 556 full-audit entries, 258 use
  `propext, Classical.choice, Quot.sound`, 148 use `propext, Quot.sound`, 96 use
  `propext` only, and 54 use no axioms. Of the 157 new V6 entries: 103 / 33 / 12 / 9.
  The raw output is in `results/proof_gated_v6_axiom_audit.txt`;
* V5 codec vectors: 8,502 passed. V5 checker vectors: 754 passed. V5 file-based
  authority cases: all passed;
* V6 vectors: 19,199 checks. These comprise the 35 interpreter vectors, 15 certificate
  decision cases, 18,000 interpreter-vs-pipeline cross-checks on mutated byte strings and
  random networks, and 1,192 single-byte mutations of a certificate. None of the
  mutations was accepted; accepted mutations would have been re-verified against the gate.

Packaging and clean re-extraction: see `dist/ARCHIVE_VERIFICATION.json` and
`dist/pcs_proof_gated_v6.tar.gz.sha256` (written after this report is committed, so the
archive digest cannot appear inside the archive itself). Per-file SHA-256 values are in
`PROOF_GATED_SHA256SUMS` and `PROOF_GATED_MANIFEST.json`.

Note: in the uploaded tree the shell scripts were not executable. They are now committed
with mode 755, and the CI and verification scripts invoke them through `bash`.
