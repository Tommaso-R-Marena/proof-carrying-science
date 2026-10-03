# PCS v0.6/v2 frontier formalization report — trusted-computing-base reduction

Scope: shrink the trusted computing base (TCB) *below* the already-integrated v0.6/v2
package/archive/canonicalization/binding/normalized-decision/assurance chain, and push every
reduction into the Lean-authoritative acceptance path and into the strongest end-to-end
theorem.

* Task baseline: `main` at `507bc458eb5f2c6c1abab9bd42bc3d6713319aa1`.
* History of this working copy: `b1ebed0` (snapshot of the baseline plus the first frontier
  pass) → `8b0b474` … `d080a74` (this pass) → the commit that adds this report (`HEAD`).
  `git log b1ebed0..HEAD` lists every change of this pass.
* Gate: `./scripts/verify_lean.sh` (kernel library + authority executable, placeholder and
  forbidden-declaration audit) and `./scripts/verify_lean_real.sh` (Mathlib real-analysis
  bridge). Both pass.

The four categories below are kept strictly separate. Nothing in "tested" is claimed as
proved, and every remaining assumption is visible in a theorem type.

---

## 0. Headline: what changed in the strongest theorem

Before (baseline flagship `PCS.V2.Flagship.pcs_accept_implies_scientific_assurance` and
`PCS.V2.Archive.pcs_raw_archive_assurance`), the hypotheses were:

| # | Hypothesis | Kind |
|---|---|---|
| 1 | `Ed25519ImplCorrect O.ed25519 Spec` | implementation = spec |
| 2 | `NoForgery Spec T.pk signed` | cryptographic hardness |
| 3 | `CaptureSound O.capture describes` | environment-capture meaning |
| 4 | `ReplayFaithful O.exec holds` | every replay PASS means its predicate |
| 5 | `ZipDecoderFaithful zip ZipSemantics` (raw archives) | ZIP decoder |
| — | SHA-256 = FIPS 180-4 | KAT-validated only (TCB item, not a hypothesis) |
| — | workflow oracle `O.workflow` | naked Boolean, no meaning |

After (this repository), for the Lean-authoritative path:

```lean
theorem PCS.V2.Frontier.pcs_frontier_archive_acceptance_sound
    {t : AuthorityTranscript} {T : TrustAnchor} {signed : List UInt8 → Prop}
    (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)          -- the ONLY hypothesis
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithTranscript t T raw = some (inp, r)) :
    ∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
      HighAssurance t T (verifiedContracts t T signed hB) inp r
```

`HighAssurance` contains: the full generic `ScientificAssurance` (structural assurance,
canonical control records, exact signed member set, digests, per-claim scoped `Assures`),
authenticity against the key holder's signing record, FIPS 180-4 SHA-256 digests of every
member and artifact, the semantic content of every passing built-in evidence item
(`reaction_balance`, `unit_compatible`, `csv_disjoint`, `pkpd_contract`,
`pkpd_reference_match`), `WorkflowDescribes` for every signed static-workflow claim, and
the verified environment facts `EnvFacts`.

| Baseline hypothesis | Status now (authoritative path) |
|---|---|
| 1 `Ed25519ImplCorrect` | **removed** — the authority runs the Lean verifier (`authority_ed25519ImplCorrect`); what remains is that this Lean verifier is RFC 8032 (open, §4) |
| 2 `NoForgery` | **kept**, stated for the Lean verifier; plus an exact forgery-extraction theorem `pcs_unsigned_acceptance_yields_forgery` |
| 3 `CaptureSound` | **removed** for the verified meaning `EnvFacts` (`authority_capture_sound`, `verifiedContracts`); facts outside `EnvFacts` are simply not concluded |
| 4 `ReplayFaithful` | **removed** for the five verified built-ins (`builtinExecWith_faithful`); for other kinds the conclusion is only "the transcript reported PASS" (no assumption) |
| 5 `ZipDecoderFaithful` | **removed** for canonical STORED archives decoded by Lean (`leanZip_faithful`); legacy archives are explicitly labelled less-assured |
| SHA-256 spec | **proved** `sha256_eq_fips1804` against an independent bit-level FIPS 180-4 spec |
| workflow oracle | **given meaning** `WorkflowDescribes`; the only workflow input not checked by Lean is the normalized static analysis (`FreshSource`) |

In addition, the PK/PD reference match now has a **real-valued** meaning
(`PCSReal.PKPD.pcs_pkpd_reference_match_real`, no hypothesis): a PASS means every committed
prediction row is within the committed tolerance of the real analytic model
`C(t) = (Dose/V)·exp(−(CL/V)·t)` and, when declared, `E = E0 + Emax·C/(EC50+C)`.

---

## 1. PROVED IN LEAN

All theorems below compile with no `sorry`/`admit`, no project axiom, no `unsafe`,
`implemented_by`, `extern` or `native_decide`. `#print axioms` (in `PCS/V2/Audit.lean`,
111 theorems, and `formal/real/PCSReal/Audit.lean`, 6 theorems) reports only
`propext`, `Classical.choice`, `Quot.sound` (or a subset).

### 1.1 SHA-256 = independent FIPS 180-4 specification (Phase 1 — closed)
* `PCS.V2.FIPS1804Spec` — independent specification over `List Bool` (message bits) and
  `BitVec 32`: `ROTR`, `SHR`, `Ch`, `Maj`, `Σ0/Σ1`, `σ0/σ1`, modular addition as `BitVec`
  addition, bit-level padding `1 ‖ 0^k ‖ ⟨ℓ⟩₆₄`, block parsing by index arithmetic, `W_t`
  and round recurrences, chaining recurrence, 256-bit output. Constants `K`, `H(0)` are
  **derived** from the first 64/8 primes as integer cube/square-root fractional parts.
  It imports nothing from the implementation.
* `FIPS1804Spec.K_roots`, `H0_roots` — the derived constants are the FIPS tables;
  `padK_spec`, `padK_minimal` — `k` is the least non-negative solution of
  `ℓ + 1 + k ≡ 448 (mod 512)`.
* `PCS.V2.SHA256Spec.sha256_eq_spec : ∀ m, SHA256.sha256 m = FIPS1804Spec.sha256 m` and
  `sha256_eq_fips1804 (m) (hLen : m.length < 2^61)` (the requested form; the length bound is
  not needed by the proof), `sha256Hex_eq_spec`. Component lemmas: `rotr_toBitVec`,
  `ch_toBitVec`, `maj_toBitVec`, `bsig0/1_toBitVec`, `ssig0/1_toBitVec`, `K_table`,
  `H0_table`, `messageBits_pad`, `chunks_eq_map`, `words_eq_map`, `schedule_eq_W`,
  `rounds_toVars`, `compress_toHV`, `chain_toHV`, `digestBits_toHV`.

### 1.2 Verified replay for `unit_compatible` (Phase 2 — closed)
`PCS.V2.Units`: declarative grammar/dimension relations `ExpDenotes`, `TermDenotes`,
`ProductDenotes`, `ExprDenotes`, `UnitCompatible`; executable `parseUnit`,
`unitCompatibleB`. `parseUnit_sound`, `parseUnit_complete`, `parseUnit_iff`,
`exprDenotes_unique` (semantic uniqueness), `unitCompatibleB_iff`
(`unitCompatibleB a b = true ↔ UnitCompatible a b`), `unitRun_sound` (replay of the exact
`ReplayRequest`). Separator splitting is itself verified (`PCS.V2.TextSplit`:
`splitAt_sound`, `splitAt_complete`, `splitBy_unique`).

### 1.3 Verified replay for `csv_disjoint`, strict CSV subset (Phase 2 — closed)
`PCS.V2.Csv`: declarative table semantics `CsvTable` (valid UTF-8, no `"`/NUL, LF lines
with optional single CR, non-empty header, distinct header names, rectangular rows, field
limit 131072) and `CsvDisjoint`. `parseCsv_sound`, `parseCsv_complete`, `parseCsv_iff`,
`csvTable_unique`, `csvDisjointB_iff`, `csvRun_sound`.

### 1.4 Verified PK/PD replay — exact rationals + certified intervals (Phase 7 — new in this pass)
Kernel (`PCS.V2.PKPDCheck`, no Mathlib, linked into the authority):
* strict decimals `decimalQ` (`-?[0-9]+(.[0-9]+)?([eE][+-]?[0-9]+)?`, `|exp| ≤ 400`) read
  as exact rationals; a whitespace-tolerant fail-closed JSON reader (`parseJsonDoc`,
  duplicate keys, leading zeros and raw control characters rejected);
* units with exact rational SI scales (`unitInfo`, dimension from the verified
  `parseUnit`, `unitInfo_sound`);
* declarative contract `QtyDenotes`, `UnitDenotes`, `PDContract`, `ModelContract`;
  `quantity_sound`, `decodePD_sound`, `decodeModel_sound`;
* certified enclosure `expEncl` (argument halving, 30-term Taylor polynomial with remainder
  `|y|^n (n+1)/(n!·n)`, repeated squaring with 256-bit outward dyadic rounding);
* robust tolerance test `CloseEncl` (Python `_decimal_isclose` for every point of an
  interval), `rowB_sound`;
* `pkpdContractRun_sound : … PASS → PkpdContractHolds req` and
  `pkpdMatchRun_sound : … PASS → PkpdMatchHolds req`.

Real-analysis bridge (`formal/real/PCSReal/PKPD.lean`, Mathlib, proof-only):
* `expEncl_sound : expEncl x = some (lo, hi) → 0 ≤ lo ∧ lo ≤ Real.exp x ∧ Real.exp x ≤ hi`
  (via `Real.exp_bound`, `squareN_sound`, `roundDown_le`, `le_roundUp`);
* `closeEncl_real` — the endpoint test implies `isclose` for every real point between;
* `effect_mono` — the direct-Emax effect is monotone in the concentration;
* `rowHolds_real`, `pkpdMatchHolds_real : PkpdMatchHolds req → PkpdMatchReal req`, where
  `PkpdMatchReal` states, for every row of the committed strict-CSV prediction table,
  `|c − C(t)| ≤ max(abs_tol, rel_tol·max(|c|,|C(t)|))` with
  `C(t) = (Dose/V)·exp(−(CL/V)·t·ts)/cs` over ℝ, and the same for the effect
  `E(C(t))` when a PD block is declared;
* `pcs_pkpd_reference_match_real` — **no hypothesis**: for every package accepted by the
  Lean authority, every passing `pkpd_reference_match` item satisfies `PkpdMatchReal`;
  `pcs_canonical_archive_pkpd_real` — the same from raw canonical archive bytes.

### 1.5 Proof-carrying evidence kernel (Phase 8)
`PCS.V2.Checkers`: `CertifiedChecker` (`handles`, `run`, `Holds`, `sound`), dispatcher
`dispatch`, `dispatch_faithful` (only the fallback's faithfulness remains, and only for
requests no certified checker handles). `builtinCheckers` = `reaction_balance`,
`unit_compatible`, `csv_disjoint`, `pkpd_contract`, `pkpd_reference_match`;
`builtinExecWith_faithful`, `builtinHolds_semantics`, `builtinExecWith_pass_semantics`.
The authority's executor is `builtinExecWith (transcriptExecutor t)`
(`Authority.transcriptOracles`): for these five kinds the transcript's PASS bit is never
consulted. Adding a kind = appending a checker; no theorem changes.

### 1.6 Workflow semantics (Phase 3 — narrowed)
`PCS.V2.Workflow`: `WorkflowDescribes fa cert` (every signed static-workflow node with a
`StaticContract` — `static_only = true`, `user_code_executed = false`, human
confirmation, inference id, source path/kind, `exact_resolved_set`/`claimed_subset`,
source-artifact inclusion, claimed inputs/outputs, rediscovered resolved references,
`operation = static_<kind>_workflow` — is matched by a normalized analysis record bound
to a committed artifact). `workflowCheckB_sound`, `workflowDescribes_semantics`. The
authority's workflow oracle is the Lean check conjoined with the production Boolean
(`authority_workflow_describes`); `pcs_workflow_acceptance_sound` lifts any front-end
meaning `A` of the analysis records to `WorkflowSemantics A`.

### 1.7 Environment facts (Phase 4 — narrowed)
`PCS.V2.EnvFacts`: `EnvFacts inv capture` — bound source records, exact `==` pins at the
start of a logical requirement line, `--hash=sha256:<64 hex>` pins, `.python-version` /
`runtime.txt` interpreter versions, digest-pinned `FROM … @sha256:<64 hex>` bases.
`envFactsB_sound`. The authority's capture is the transcript capture only if
`envFactsB` accepts it, otherwise `null` (`authority_capture_sound`, `authority_env_facts`).

### 1.8 Canonical ZIP (Phase 5 — closed for the canonical subset)
`PCS.V2.Zip`: `encodeZip` (local headers, central directory, EOCD, field by field),
`CanonicalZip raw entries` (raw is exactly the encoding, names strictly sorted, fields in
range), `decodeZip` (parse central directory, re-encode, compare), `decodeZip_sound`,
`leanZip_faithful : ZipDecoderFaithful decodeZip CanonicalZip`,
`canonicalZip_names_nodup`. `PCS.V2.CanonicalArchive`: `acceptArchiveWithTranscript`
(compiled authority `--zip` mode), `pcs_canonical_archive_builtin_sound`,
`pcs_canonical_archive_acceptance_sound`, `acceptArchiveWithTranscript_refines`,
`pcs_authority_archive_binary_sound`, `pcs_authority_archive_binary_builtin_sound`.

### 1.9 Flagship layers (Phase 9)
* `HighAssurance.pcs_verified_builtin_acceptance_sound` — **no hypothesis**
  (`VerifiedBuiltinAssurance`: structural, per-claim `Assures`, transcript binding, the
  five built-in semantics, `WorkflowDescribes`, `EnvFacts`, exact artifact binding).
* `HighAssurance.pcs_high_assurance_acceptance_sound` — `AuthorityContracts` only.
* `Frontier.pcs_frontier_acceptance_sound`, `pcs_frontier_archive_acceptance_sound`,
  `pcs_frontier_authority_binary_sound`, `pcs_frontier_environment` — **only
  `NoForgery`** (new in this pass).
* `Frontier.pcs_unsigned_acceptance_yields_forgery` — **no hypothesis**: acceptance of a
  package whose package or certificate envelope the key holder did not sign yields an
  explicit pair `(m, s)` with `Ed25519.verify T.pk m s = true ∧ ¬ signed m` (the delivered
  signature on the unsigned envelope) — the exact reduction "unauthorized PCS acceptance →
  forgery against the Lean RFC 8032 verifier" (new in this pass).
* `PCSReal.PKPD.pcs_pkpd_reference_match_real` (§1.4).

All baseline theorems listed in the task (`acceptPCSWithTranscript_implies_acceptPCS`,
`gatedProduction_refinesLean`, `pcs_accept_implies_scientific_assurance`,
`pcs_archive_accept_implies_scientific_assurance`, `pcs_raw_archive_assurance`,
`production_raw_archive_assurance`, `production_accept_implies_scientific_assurance`, the
`reaction_balance` replay theorems) are unchanged and still audited.

---

## 2. EXECUTABLY / DIFFERENTIALLY TESTED (evidence, not proof)

* Lean `#guard` vectors: 91 in `formal/PCS/V2/` — SHA-256/SHA-512/Ed25519 KATs and
  negative vectors (`Vectors`), chemistry (`ChemistryVectors`), units/CSV/dispatcher
  (`BuiltinVectors`), PK/PD decimals, unit scales, `exp` enclosure tightness and contract
  vectors (`PKPDVectors`, new).
* `tests/test_frontier_tcb.py` — regressions for counterexamples 5–17; strict-CSV vs
  `csv.DictReader` agreement inside the subset; Python↔Lean differential fuzzing of
  units, CSV, workflow, environment facts and the canonical ZIP decoder through
  `formal/tools/LeanBuiltinCheck.lean`; raw-byte Lean verification of the canonical golden
  ZIP and legacy/strict behaviour of non-canonical ZIPs.
* `tests/test_pkpd_high_assurance.py` (new) — regressions for counterexamples 18–20;
  Python↔Lean differential agreement of strict decimals (≈420 strings), of the contract
  check (≈90 mutated models incl. duplicate keys, leading zeros, BOM, control characters)
  and of the certified-interval reference match vs the production `Decimal(50)` replay
  (≈80 cases, both outcomes exercised, perturbations away from the tolerance boundary).
* `tests/test_formal_v2_differential.py`, `tests/test_formal_v2_regressions.py`,
  `tests/test_lean_authority_v06.py` — golden-package acceptance by the compiled
  authority, adversarial mutations, transcript binding.
* All three golden examples (`pkpd-supported`, `pkpd-falsified`, `environment-bound`) are
  accepted by the compiled authority in raw-archive mode, with the PK/PD outcomes now
  computed by Lean (the falsified case is `FAIL` in Lean as in production).
* Full Python suite: 504 passed (§7).

---

## 3. EXPLICIT ASSUMPTIONS / TCB (remaining)

Visible in theorem types:
1. **`NoForgery PCS.V2.Ed25519.verify T.pk signed`** — Ed25519 unforgeability (EUF-CMA)
   for the trust anchor, for the Lean verifier. A hardness assumption; not provable in
   Lean. Its exact contrapositive is proved (`pcs_unsigned_acceptance_yields_forgery`).
2. **Workflow front end** — the meaning `A` of the normalized analysis records
   `t.workflowAnalysis` (hypothesis `hA` of `pcs_workflow_acceptance_sound`). Without it,
   the theorems still give `WorkflowDescribes` relative to the records.
3. For evidence kinds **other than the five verified built-ins** (external validators,
   provenance records), the conclusion is only that the transcript reported the outcome;
   a stronger meaning needs `ReplayFaithful` for them (generic flagship).
4. For **legacy (non-canonical) archives**, `ZipDecoderFaithful` for the Python decoder
   (generic `pcs_raw_archive_assurance`); such receipts are labelled
   `python-materialized-legacy-zip`, and `require_canonical_archive=True` rejects them.
5. For the **environment capture outside `EnvFacts`** (hermeticity summary, replay plan,
   other ecosystems, `unresolved`), any meaning beyond "equals the transcript capture"
   needs `CaptureSound` (`pcs_high_assurance_acceptance_sound` with a user `describes`).

Not in theorem types, i.e. outside the formal model (operational TCB):
6. Lean 4.28.0 kernel and compiler, Lean runtime (GMP-backed `Nat`/`Int`), the C toolchain
   building `pcs-lean-authority`; Mathlib for the proof-only real bridge.
7. The Python driver: it computes the observation transcript (workflow analysis,
   environment capture, non-built-in replay outcomes) and hands bytes to the authority; the
   authority checks the bytes itself, and the transcript is bound to the certificate hash.
8. **Ed25519 implementation = RFC 8032**: the Lean verifier is a transcription validated
   by vectors (open, §4). Python `cryptography`/OpenSSL agreement
   (`Sha256ProductionAgrees`-style completeness) is not claimed.
9. Interpretation boundary: computational replay does not establish empirical, biological,
   clinical or regulatory adequacy; the PK/PD theorem is about the declared analytic model.

### 3.1 Before/after TCB inventory

| Item | Before (baseline) | After |
|---|---|---|
| SHA-256 implementation vs FIPS 180-4 | KAT-validated | **proved** (`sha256_eq_fips1804`) |
| `reaction_balance` replay | proved | proved |
| `unit_compatible` replay | `ReplayFaithful` | **proved** + run by authority |
| `csv_disjoint` replay | `ReplayFaithful` (DictReader) | **proved** (strict subset) + run by authority |
| `pkpd_contract` replay | `ReplayFaithful` (float) | **proved** (exact rationals) + run by authority |
| `pkpd_reference_match` replay | `ReplayFaithful` (Decimal/float) | **proved**, real-valued meaning via certified `exp` enclosure + run by authority |
| external validators | `ReplayFaithful` | unchanged (no claim made) |
| workflow oracle | Boolean, no meaning | `WorkflowDescribes` proved; front-end analysis remains |
| environment capture | `CaptureSound` | `EnvFacts` proved for pins/hashes/interpreters/digest bases; rest unconcluded |
| raw ZIP | `ZipDecoderFaithful` | **proved** for canonical STORED archives decoded by the compiled authority |
| Ed25519 impl correctness | `Ed25519ImplCorrect` (or `rfl` vs itself) | hypothesis removed for the authority; RFC 8032 equivalence open |
| Ed25519 unforgeability | `NoForgery` | `NoForgery` (sole hypothesis) + exact forgery extraction |

### 3.2 `ExternalContracts` fields
* `ed25519Spec`, `ed25519ImplCorrect` — **removed** on the authoritative path (spec fixed to
  the Lean verifier, `contractsWithLeanEd25519`).
* `signed`, `noForgery` — **kept** (only hypothesis of the frontier flagship).
* `describes`, `captureSound` — **specialized** to `VerifiedCapture` and discharged by
  `authority_capture_sound` (`verifiedContracts`).
* `holds`, `replayFaithful` — **specialized** to `BuiltinHolds` and discharged by
  `builtinExecWith_faithful (replayFaithful_reported _)`.
* raw-archive `ZipDecoderFaithful` — **discharged** by `leanZip_faithful` for the canonical
  mode.

---

## 4. OPEN (smallest remaining statements)

1. **Ed25519 = independent RFC 8032 specification (Phase 6).** Needed:
   `∀ pk m s, PCS.V2.Ed25519.verify pk m s = RFC8032Spec.verify pk m s` where
   `RFC8032Spec` is stated over `ZMod (2^255 − 19)` with the affine twisted-Edwards group
   law. Sub-goals: (a) primality of `2^255 − 19` and of `L` (Pratt/Lucas certificates), and
   non-squareness of `d` (completeness of the addition law); (b) extended-coordinate
   `add` represents affine addition when `Z ≠ 0`; (c) the 256-step double-and-add loop
   computes `[n]P`; (d) `fpow`/`finv` compute powers/inverses in the field; (e) `decode`
   implements the RFC 8032 §5.1.3 square-root recovery (`sqrtM1² = −1`, Euler criterion);
   (f) `encode` is affine normalization. **SHA-512** is a further explicit dependency:
   `PCS.V2.SHA512.sha512 = FIPS180_4.SHA512` is open (the SHA-256 proof in
   `SHA256Spec` is the template). Not attempted to completion in this pass.
2. **Workflow front end.** A Lean static analyser for a literal-reference source subset
   with `analyze bytes = some f → A f`; today the normalized `FreshSource` records are
   produced by Python (`workflow_replay_v06.py`).
3. **Environment capture beyond `EnvFacts`.** `renv.lock`, TOML/JSON lockfiles, the
   hermeticity summary and replay plan: `captureB_sound : captureB inv v = true →
   EnvironmentDescribes inv v` for each format.
4. **Strict decimal / JSON reader correctness.** `decimalQ` and `parseJsonDoc` are
   executable specifications; a declarative grammar with `decimalQ_sound/complete` and a
   JSON-text grammar for `parseJsonDoc` would remove them from the "definition is the
   meaning" boundary.
5. **External validators.** `ReplayFaithful` for `external_formal_proof`,
   `external_*_validation`, `provenance_record` (e.g. an independently checkable proof
   artifact as a new `CertifiedChecker`).
6. **DEFLATE archives.** Only canonical STORED archives are Lean-decoded; a verified
   DEFLATE decoder would extend `leanZip_faithful`.
7. **Binary64 agreement at extremes.** Not a soundness gap (fail-closed), see §5 item 21.

---

## 5. Counterexamples discovered (all preserved as regression tests)

1–4: see `formal/PCS_FULL_FORMALIZATION_REPORT.md` §F (integers as floats, malleable
base64, Unicode digits in formulas, boolean coefficients).

First frontier pass (`tests/test_frontier_tcb.py`):
5. **Unit with trailing newline** — `_TERM.match(...)` with `$` accepted `"m\n"` as `m`.
   Repaired: `fullmatch`.
6. **Unicode-digit unit exponent** — `\d` accepted `m^\u0662`. Repaired: ASCII `[0-9]`.
7. **Scale overflow** — float overflow in the diagnostic SI scale turned dimensionally equal
   units into FAIL. Repaired: scale is diagnostic only, overflow-safe.
8. **Scale underflow** — same with underflow. Repaired likewise.
9. **Duplicate CSV header** — `csv.DictReader` silently used the last column. Repaired:
   strict CSV subset rejects.
10. **Short CSV row** — `DictReader` filled `None`, so a missing key became a value.
    Repaired: rectangular rows required.
11. **CSV quoting** — quote removal made `"1"` and `1` collide; embedded newlines inside
    keys. Repaired: `"` outside the subset.
12. **Lone CR** — `DictReader` treated a bare CR as a line end. Repaired: rejected.
13. **Workflow `null` reference** matched an artifact named `None`. Repaired.
14. **Workflow string confidence** `"0.98"` accepted. Repaired.
15. **Wildcard/range pins** (`==1.*`, `==1.0,<2`, `===`) treated as exact. Repaired.
16. **Short container digest** `@sha256:abc` treated as digest-pinned. Repaired.
17. **Empty `--hash=sha256:`** treated as a hash pin. Repaired.

This pass (`tests/test_pkpd_high_assurance.py`):
18. **Lenient tolerance spellings** — `float(spec["rel_tol"])` accepted `" 1e-9"`, `"1_0"`,
    `"inf"`, `"nan"`. Repaired: `replay_v06._strict_tolerance` (integer, or strict decimal
    text; binary floats only via the direct API).
19. **Lenient prediction cells** — `Decimal(row[...])` accepted `" 0.5"`, `"+0.5"`, `".5"`,
    `"0_5"`, `"NaN"`/`"Infinity"`, so a cell's meaning depended on Python's `Decimal`
    grammar. Repaired: `pkpd.strict_decimal_text` (same grammar as Lean `decimalQ`).
20. **Prediction CSV dialect** — the PK/PD replay used `csv.DictReader` (quote removal,
    last-wins duplicate headers, `None` for short rows), i.e. counterexamples 9–12 were
    still reachable through `pkpd_reference_match`. Repaired: the strict CSV subset
    (`parse_strict_csv` / Lean `parseCsv`) is used.
21. **Binary64 vs exact semantics (documented divergence, fail-closed)** — model values
    outside the binary64 range (e.g. a dose of `1e-330`, or values whose float product
    overflows) are FAIL in production but PASS under the exact-rational semantics. The
    certificate then records FAIL while Lean derives PASS, so the authority rejects the
    package; no unsound acceptance results. Similarly, exactly at a tolerance boundary
    the Decimal(50) replay and the certified interval may differ; again the package is
    rejected, never wrongly accepted.

Attacks that **held** in this pass (both sides reject): duplicate JSON keys in the model,
JSON leading zeros, raw control characters in JSON strings, UTF-8 BOM, trailing bytes,
missing PD fields, wrong dimensions, zero/negative strictly-positive quantities, boolean
values, CRLF prediction tables (accepted by both), negative times, empty tables.

---

## 6. Production changes and input-surface narrowing

Production modified: **yes**.
* `pcs/adapters/pkpd.py` — strict CSV subset for prediction tables, strict decimal grammar
  for cells (`strict_decimal_text`), no `csv.DictReader`.
* `pcs/replay_v06.py` — strict tolerance parsing (`_strict_tolerance`).
* `formal/PCS/V2/Checkers.lean`, `Authority.lean` — the compiled authority now replays
  `pkpd_contract` and `pkpd_reference_match` itself (previously transcript-trusted).
* (First frontier pass, already in `b1ebed0`: strict units/CSV in `pcs/checks/`, workflow
  analysis and environment capture handed to Lean, canonical STORED ZIP with `--zip`
  raw-byte authority mode and `require_canonical_archive`.)

Accepted surface intentionally narrowed (fail-closed):
* PK/PD prediction cells and tolerances: only `-?[0-9]+(.[0-9]+)?([eE][+-]?[0-9]{1,4})?`
  with `|exponent| ≤ 400` (tolerances may also be integers).
* PK/PD prediction tables: strict CSV subset (no quotes, no NUL, LF/CRLF, distinct
  headers, rectangular).
* PK/PD model JSON on the authoritative path: only the escapes `\" \\ \b \t \n \f \r
  \u00XX` in strings (other valid JSON escapes make the Lean contract FAIL and hence the
  package rejected).

Lean files changed/added in this pass: `PCS/V2/PKPDCheck.lean` (new), `PKPDVectors.lean`
(new), `Frontier.lean` (new), `Checkers.lean`, `Authority.lean`, `HighAssurance.lean`
(docs), `Zip.lean` (proof repair), `Audit.lean`, `PCS.lean`, `tools/LeanBuiltinCheck.lean`;
`formal/real/PCSReal.lean`, `formal/real/PCSReal/PKPD.lean`, `formal/real/PCSReal/Audit.lean`
(new); root `lakefile.toml`/`lake-manifest.json` (Mathlib bridge library `PCSReal`
requiring the PCS kernel by path). Scripts: `scripts/verify_lean_real.sh` (new).
Tests: `tests/test_pkpd_high_assurance.py` (new).

---

## 7. Metrics, audits and results

| Metric | Value |
|---|---|
| Lean files, kernel (`formal/PCS/**`) | 62 (46 in `formal/PCS/V2/`) |
| Top-level declarations in `formal/PCS/V2/` | 1232 |
| Theorems/lemmas in `formal/PCS/**` | 561 (495 in `V2`) |
| Real bridge (`formal/real/PCSReal/PKPD.lean`) | 17 theorems |
| `#print axioms` audited | 111 (kernel) + 6 (bridge); only `propext`, `Classical.choice`, `Quot.sound` |
| `sorry` / `admit` / project `axiom` / `unsafe` / `implemented_by` / `extern` / `native_decide` | 0 / 0 / 0 / 0 / 0 / 0 / 0 |
| Lean `#guard` vectors (`V2`) | 91 |

Build/test results at the final commit:
* `./scripts/verify_lean.sh` — PASS (kernel library + `pcs-lean-authority`, audits).
* `lake build PCS` (in `formal/`) — PASS.
* `lake env lean PCS/V2/Audit.lean` — PASS, 111 axiom reports, none beyond the standard three.
* `./scripts/verify_lean_real.sh` (`lake build PCSReal` at the repository root) — PASS.
* Full Python suite (`PYTHONPATH=. pytest -q`, includes the Python↔Lean differential
  suites, `tests/test_frontier_tcb.py` and `tests/test_pkpd_high_assurance.py`) —
  **504 passed**, 0 failed, 0 skipped (the compiled authority and `lake` were available, so
  no Lean-dependent test was skipped).
