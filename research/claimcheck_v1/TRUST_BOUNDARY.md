# ClaimCheck v1 trust-boundary audit

Status: research sidecar. Nothing here has, grants or changes PCS v0.6 production authority. No
file outside `research/claimcheck_v1/` is modified. The production `pcs-lean-authority` executable
is not involved; ClaimCheck uses the Lean 4.28.0 **kernel** directly through per-claim theorems.

## 1. What is established, and by what

| Statement | Established by | Depends on |
| --- | --- | --- |
| `run src claim = outcome` for the exact data bytes and typed claim in an obligation file | Lean 4.28.0 kernel, `decide +kernel` inside `pcs_batch`, then the proved lemma `run_of_runAll` | Lean kernel and its GMP arithmetic; the three standard axioms `propext`, `Classical.choice`, `Quot.sound` (reported by `#print axioms` for every claim theorem and enforced by the runner and the replayer) |
| Batching does not change meaning: `runAll src cs = cs.map (run src)` | Proved in `ClaimCheck.lean` (`runAll_eq_map`), kernel-checked with every obligation file | as above |
| The rational test used for SD, SEM and correlation equals the real-number statement `lo ≤ s·√q ≤ hi` | Proved with Mathlib in `formal/real/ClaimCheckReal.lean` (`sqrtInInterval_iff`, `within_sqrt_iff`) | Mathlib v4.28.0; proof-only, not needed to check a claim |
| A `consistent` verdict for a rational statistic means `|value·scale − reported| ≤ half unit of the last printed digit` | `within_rat_iff` (Mathlib) | as above |
| The executable sum, mean and sum of squares are the textbook ones; the signed-root form of r equals `Sxy/(√Sxx·√Syy)` | `sumQ_eq_sum`, `meanQ_eq`, `ssQ_eq`, `pearson_signed_sqrt` (Mathlib) | as above |
| The quote is in the source at the recorded offsets; the number is printed there as a whole token; the unit, column, group, statistic-wording and scope checks passed | Deterministic Python (`grounding.py`), re-checked in part by `replay_independent.py` (offsets, literal) | Python implementation; these are syntactic checks |
| The obligation file is exactly "reviewed checker + this data file + these claims + these expected outcomes" | `replay_independent.py` re-renders it from the receipts with its own renderer and compares bytes and digests; the website re-renders it a third time in JavaScript | the reviewer obtaining the checker digest independently of the bundle |

## 2. What is explicitly not established

* **Custody.** That the file is the data the authors analysed, complete and unaltered. A manifest
  digest only pins bytes someone supplied.
* **Meaning.** That the sentence means the typed reading. Every receipt says
  `semantic_reading: UNREVIEWED`. The source checks are lexical; they cannot tell that "nestling age
  at sampling" is a different variable from a column called `chick_age`.
* **Science.** Sampling, measurement validity, exclusions, whether the statistic supports a
  comparison or a causal reading. Always `NOT_ASSESSED`.
* **The checker is the right checker.** `run` is a definition. Its faithfulness to "what a
  statistician means" rests on reading about 500 lines of Lean plus the Mathlib meaning theorems
  above. There is no proof that the CSV automaton implements RFC 4180; it is a deliberately strict
  subset, and where it rejects a file the result is UNKNOWN.
* **Rounding convention.** PROVED means "within half a unit of the last printed digit" (ties
  accepted either way). A paper that truncates, or reports more digits than it computed, can be
  REFUTED although an author would call it correct. The assumption is printed in every receipt.

## 3. Trusted computing base for a PROVED/REFUTED result

1. Lean 4.28.0 kernel and compiler binary (pinned release digest in `scripts/activate_lean_428.sh`).
2. `formal/ClaimCheck.lean` as reviewed (digest pinned in `formal/ClaimCheck.lean.sha256`; the
   runner refuses a file that differs; the replayer takes the digest from the reviewer).
3. The process boundary that hands the obligation file to `lean` and reads its exit status and
   output (`lean.py`; independently `replay_independent.py`). Accepted only if: exit status 0, empty
   stderr, exactly one axiom line per claim theorem in order, only standard axioms.
4. The SHA-256 implementation and file system used to bind the file to its digest (Python
   `hashlib`; the browser uses WebCrypto). The digest is **not** computed inside Lean.

Not in the TCB for the arithmetic: the Python oracle, the JavaScript core, every proposer, every
language model, the benchmark harness. If the oracle predicts a wrong outcome the kernel rejects
the theorem and the claim stays UNKNOWN (exercised by `check_live.py`: 11 forged outcomes rejected,
hundreds of random cases with zero oracle/kernel disagreement).

In the TCB for question 2 (source binding): `grounding.py`. It is not formally verified. Its
failure modes are measured in the benchmark (unsupported positives and refutations, adversarial
families A and C).

## 4. How untrusted input is contained

| Input | Containment |
| --- | --- |
| Paper text | Never interpreted as instructions by the verifier. Quotes must be exact substrings (whitespace runs aside). The injection variants in the benchmark test model obedience; the verifier ignores it. |
| Model output | Parsed as JSON data; only `quote` and a strict `spec` are read; unknown fields reject the proposal; no model text reaches Lean except through the typed spec. Models never see data rows. |
| Names and values in a spec | Rendered into Lean either as string literals drawn from a conservative character whitelist (no quote, backslash or newline) or as explicit byte lists. A defence-in-depth scan rejects any generated tail containing `sorry`, `native_decide`, `axiom`, `unsafe`, `implemented_by`, `extern`, `partial`, `ofReduceBool`. |
| Data file | Embedded as one hexadecimal numeral; parsed only by the Lean checker (and, without authority, by the oracle). Size-bounded to 65,536 bytes. A digest mismatch with the manifest stops everything before any check. |
| Manifest | Supplied by the submitter, validated (missing-value tokens may not be numbers, etc.). It is trusted for vocabulary only. A hostile manifest can make source checks pass that should not; it cannot change the arithmetic except through `na_tokens`, which are printed in every receipt together with the number of rows they excluded. |
| Receipts and bundles | Not trusted on import. The replayer recomputes digests, re-derives obligations, re-runs Lean, recomputes values with different code and recomputes each result from its parts; an edited "PROVED" fails. |
| Credentials | Environment variables only; one fixed host per provider; no redirects; never in prompts, URLs, cache keys, logs, receipts or errors (unit-tested). The website has no provider access at all. |

## 5. Fail-closed behaviour (tested)

No Lean, wrong Lean version, timeout, non-zero exit, warnings, extra output, missing or unexpected
axiom report, checker digest mismatch, data digest mismatch, oversized data, malformed proposal or
manifest, quote or number not found, unit conflict, missing anchor, missing statistic wording,
out-of-scope wording, undefined statistic, conflicting conventions: each yields UNKNOWN with a
specific reason. No code path produces PROVED or REFUTED without a kernel acceptance and a passing
source binding.

## 6. Residual risks, stated plainly

1. **Wrong reading that passes the lexical checks.** A sentence can name a column and a statistic
   and still mean something else. This produces false alarms (REFUTED for a true sentence) more
   often than false confirmations, because a wrong reading rarely reproduces the number. The
   benchmark reports both rates per proposer and the coincidence-search attack measures the false
   confirmation risk directly.
2. **Low-information numbers.** A one-digit number can coincide with some statistic. The
   statistic-wording gate removes most such coincidences found in development; it is a heuristic.
3. **Manifest aliases are a human judgement.** Too few aliases cause abstention; careless aliases
   cause false alarms.
4. **Same-author annotation.** Gold labels were prepared by the same AI system that built the
   tool, not by domain experts. Truth values are computed, but which numbers count as "derivable
   from the table" is a judgement.
5. **Scale bound.** Kernel evaluation costs seconds per claim and grows with file size; tables over
   64 KB are out of reach without a different (compiled, larger-TCB) path.
6. **Kernel arithmetic.** Lean's kernel uses GMP-accelerated natural-number arithmetic; that
   acceleration is part of the trusted kernel.

## 7. Relation to existing PCS boundaries

* Production v0.6 (`pcs verify-v06`, compiled `pcs-lean-authority`): unchanged and not used.
  Reproduced during this work: `lake -d formal build PCS pcs-lean-authority pcs-semantic-check`
  completed, and the v0.6/Lean/authority test subset passed (591 passed, 33 skipped).
* PR #211 (`research/llm_claim_harness_v1`): generates a bespoke Lean program per claim for CSV
  files up to 512 bytes and strict note formats. ClaimCheck instead fixes one reviewed checker and
  states every claim as `run src claim = outcome` about it, scales to 64 KB, and adds source gates,
  real documents and a frozen evaluation. It does not include #211's continuous-perturbation OLS
  bounds. The two are independent; neither imports the other.
* PR #207 (`research/scientific_review_v4`): whole-project review with a strict claim-recovery
  benchmark (0/70). ClaimCheck does not attempt whole-paper understanding; see REPORT.md for why
  the 0/70 measured identifier agreement and coverage of uncheckable prose rather than verification.
* The repository's source-admission gate (`research.integration_v2.reconcile`) rejects any new
  tracked file until a maintainer admits it. This PR therefore cannot pass `source-policy`; the gate
  was not modified or bypassed.
