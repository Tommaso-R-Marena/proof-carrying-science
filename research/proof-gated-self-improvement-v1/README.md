# Proof-Gated Self-Improvement: neural + symbolic research prototype

**Status: experimental; NOT a deployed immutable authority or proof of general self-improvement.**

## The narrow objective, precisely stated

Models are exact integer neurons `relu(w*x+b)` or `w*x+b`. The frozen certificate corpus is
`[-3,-2,-1,0,1,2,3]`, with target `relu(2*x+1)`. A candidate is accepted only if:

1. Every previously correct corpus prediction remains correct.
2. At least one previously incorrect corpus prediction becomes correct.
3. The sum of absolute corpus errors strictly decreases.

In `formal/PCS/V2/ProofGatedSelfImprovement.lean`, a sound *computable* Lean Bool gate checks
these conditions. Lean proves `accept_sound`, `accepted_preserves`, `accepted_expands`,
`accepted_strict_loss`, composition of two accepted steps, and arbitrary
`CertifiedTrace` length bounds `n + loss(final) <= loss(start)`. Consequently no accepted
sequence can be infinite, and no candidate is *guaranteed* to exist.

## New: arbitrary changing proposal strategies

`gatedStep` accepts a modification or retains the incumbent. Theorems
`arbitrary_strategies_preserve` and `arbitrary_strategies_nonincrease` apply to **any
sequence of proposer functions**, each of which receives the current model. They establish
corpus preservation and non-increasing exact error, even when the proposer is changed or
adversarial. They do **not** guarantee strict progress: rejected updates can leave the model
unchanged forever. The acceptance policy, trusted evaluator and enforcement still must
remain inaccessible to the proposer.

## New: Lean reads and checks actual canonical artifact files

`formal/PCS/V2/ProofGatedArtifacts.lean` defines an exact no-newline UTF-8 format:
`PGSI1|R|1|1` (ReLU) or `PGSI1|L|0|0` (linear). It rejects leading zeros, negative zero,
trailing whitespace/newlines, unknown fields, wrong versions, out-of-range weights,
and malformed encodings. In Lean, `decode_canonical` and `decode_bounded` prove the
successful parse corresponds to the canonical text and bounded mathematical neuron;
`acceptWire_sound` ties an accepted wire request to the proven `admissible` relation.
The experimental Lean CLI **opens the two files itself**, rather than trusting values
translated by Python.

`proof_gate.py` uses Python to propose candidates and place canonical files into a
temporary directory. Only a clean affirmative **Lean verdict** authorizes a simulated
mutation; errors, warnings, missing executables, and malformed artifacts fail closed.
Nothing here enforces OS-level isolation or locks files after approval.

## Symbolic companion

`formal/PCS/V2/ProofGatedSymbolic.lean` proves `e + 0 -> e` and `e * 1 -> e`
preserve expression meaning **for all integer inputs**, strictly reduce expression-tree
size, and compose. The cost metric is AST nodes, not measured runtime or reasoning power.

## Test and falsification results

- **Original 21 reference tests** (now incorporated into the expanded suite): 5,184 exact finite-lattice transitions, 3,000 randomized transitions,
  8,450 unique canonical encodings, malformed inputs, stale incumbent, policy tampering,
  rollout rejection and fail-closed behavior.
- **Two Lean-authorized generations** on actual model files:
  `(ReLU,0,0) -> (ReLU,1,1) -> (ReLU,2,1)`.
  Loss `16 -> 6 -> 0`; solved corpus cases `3/7 -> 4/7 -> 7/7`.
- **Out-of-corpus falsification** (`ood_falsification.py`): among 128 models and 16,384
  enumerated transitions, 4,081 satisfy the frozen certificate and **283 (6.93% of accepted)**
  worsen exact held-out error on inputs `[-20,-4] U [4,20]` under the **SAME** target function.
  Witness: `(ReLU,3,-3)->(ReLU,3,-1)` improves corpus loss `7->3` but worsens held-out
  loss `136->170`. A separate Lean theorem checks the same failure at input `20`.
  This is an exhaustive synthetic counterexample, *not* a real-world failure probability
  or an independently sequestered blind test.

## Reproduce

```bash
cd research/proof-gated-self-improvement-v1
python -m unittest discover -s tests -v
python ood_falsification.py
cd ../../formal
source ../scripts/activate_lean_428.sh
lake build PCS.V2.ProofGatedSelfImprovement PCS.V2.ProofGatedSymbolic PCS.V2.ProofGatedArtifacts
printf 'PGSI1|R|0|0' > /tmp/pgsi-old
printf 'PGSI1|R|1|1' > /tmp/pgsi-new
lake env lean --run PCS/V2/ProofGatedArtifacts.lean /tmp/pgsi-old /tmp/pgsi-new
# ACCEPT; exit code 0 (reference authority only)
```

## Critical trusted-base boundaries

Despite the Lean theorems, a writable checkout is **not an immutable kernel**. A malicious
proposer with write/exec privileges can swap the Lean source, modify files between acceptance
and deployment, change the actual deployed weights, tamper with process arguments or replace
the verifier. There is no remote attestation, pinned compiled authority signature,
cryptographic binding to deployed model bytes, transactionally locked promotion, verified
filesystem loader, or hardened process separation here. `IO.FS.readFile` is an executable
read of a UTF-8 file, not a formal theorem that arbitrary storage faithfully represents
physical bytes or that the bytes remain unchanged.

The meaningful guarantee is only **conditional upon the frozen formal specification and
faithful execution on exactly those decoded model artifacts**. OOD falsification shows the
objective can remain incomplete even when verification is mathematically correct.

## Next research gates

1. Independent, pinned authority and immutable policy with isolated promotion root;
   atomic content-addressed model promotion, concurrency/TOCTOU tests and audited receipts.
2. Verification of canonical byte format and model loading against a non-lean production
   inference implementation, using differential cross-language tests and source-level proofs.
3. Small quantized multilayer networks and verified symbolic prover strategy changes.
4. Multi-domain performance contracts, held-out prospective evaluation, anti-overfitting
   tests and calibrated statistical statements kept separate from logical guarantees.
5. Independent adversarial audit before any deployment or merger into production PCS authority.

**CI workflow:** `.github/workflows/pcs-proof-gated-research.yml`. Keep this PR draft and
this module research-only until trusted deployment boundaries and independent verification
are addressed.

## Research prototype v2: content-addressed CAS promotion

The **new** `promotion_v2.py` is a POSIX-only transactional wrapper around the unchanged
Lean artifact authority. It is deliberately separate from the production PCS gate.

- `ResearchPromotionStore.initialize(...)` exclusively creates a new controlled root,
  with a canonical genesis record, a content-addressed initial blob, and a HEAD pointer.
- `promote(candidate_bytes, expected_head)` locks the root, checks the *entire* receipt
  chain and active blob, and enforces a generation-and-hash compare-and-swap.
- Candidate **bytes** are snapshotted into a SHA-256-addressed `.pgsi` blob; the Lean
  authority reads the actual immutable-by-convention files. It must return exactly
  `ACCEPT\n` on stdout, exit 0, and print nothing to stderr.
- The store rereads exact blob content after checking to reject detected substitutions.
  A sequential, hash-chained receipt is fsynced before HEAD is atomically replaced.
  The committed HEAD is reread, and `audit()` verifies the receipt chain and blob hashes.
- The gate rejects missing Lean, regressive updates, stale versions, policy mismatch,
  simple rollbacks, malformed files, symlink/hardlink inputs and corrupted receipts.
  A partial failure leaves an **orphan receipt**, which is *detected and fails closed*
  until an administrator investigates; no recovery is implicitly claimed.
- Tests use a clearly labeled **fake oracle** for fault injection and filesystem
  transaction behavior, plus a **real Lean-backed CI demonstration** of two
  content-addressed commits and stale/regressive rejection.

```bash
cd research/proof-gated-self-improvement-v1
python -m unittest discover -s tests -v
# The workflow separately invokes the real Lean authority and exercises live CAS.
```

### Pure CAS proof

`formal/PCS/V2/ProofGatedPromotion.lean` defines a mathematical state containing
the **exact artifact text** and generation, with a proposal carrying an expected
generation and incumbent. Lean proves that `tryCommit` can succeed **only if** the
expected generation and active artifact agree, generation advances by one,
the new text is the submitted proposal, and `acceptWire` certifies a genuine
model improvement. It proves stale/substituted proposals cannot commit and a
gated attempt cannot decrease generation. This **does not prove** that the
Python filesystem implementation refines the pure Lean state transition.
The hash-to-text correspondence relies on collision resistance, byte fidelity,
and an honest trusted execution environment.

### Threat-model boundaries and remaining work

The wrapper is **not** an immutable trusted execution root, a signed verifier, or
a system-level sandbox. A user able to modify the verification source, verifier
binary, policy, filesystem, HEAD, receipts, or promoted inference runtime could
still produce a fake success or forge a full history. Advisory locks govern
**cooperating** writers only. The two-file read/verify/commit path has no general
proof of freedom from malicious TOCTOU races. Digest checks detect corruption but
do not prevent same-privilege tampering, malicious kernel/OS behavior, or rollback
with a fully rewritten receipt chain.

A deployable authority therefore requires separate OS credentials/containers with
unforgeable file access controls; pinned signed authority binaries; immutable
policy/configuration outside the model's write authority; a loader that verifies
and then executes the *same sealed bytes*; external monotonic checkpoint anchoring
and append-only audit (ideally independent infrastructure); cross-process crash
recovery protocols; and independent adversarial audits. These are **not** present
in this research PR. No production auto-update integration is enabled.

## Sealed inference and proof-connected promotion (v3, October 17)

`sealed_inference.py` adds an inference loader that locks the cooperative store,
audits the entire hash-chain, reads the exact active content-addressed artifact,
parses strict canonical model bytes, and returns an immutable `SealedInference`
snapshot of that very byte string. All subsequent predictions use only frozen
`bytes` and frozen model parameters; they do not reopen a writable model file.
Snapshot generation is pinned: serving a stale expected generation fails.

`formal/PCS/V2/ProofGatedInference.lean` defines `infer` from the model's
canonical text and proves:
- `infer_sound`: each successful wire inference corresponds to the decoded
  model's exact integer predictor;
- `infer_canonical`: that prediction comes from the canonical original text;
- `committed_inference_preserves_correct_cases`: a successfully certified
  compare-and-swap update preserves every previously correct prediction on the
  trusted corpus, at the very same integer input;
- `committed_inference_exact_artifact`: every successfully committed target
  text decodes into the model whose exact semantics is used by `infer`.

The Python suite compares **8,450** bounded neuron encodings over **41**
integer inputs each (**346,450** calculations) with an independently written
integer formula, checks exact encoding and 10+ tampering cases, stale heads,
post-load file replacement, removed/corrupted receipts and simple rollback.

The **public** `ResearchPromotionStore.promote(candidate, expected_head)`
method does **not** allow a caller to select its acceptance verifier.
The `_promote_with_oracle` method exists **solely for local fault-injection
tests** and demonstrably is *not* a protected security boundary. Python and
the POSIX filesystem remain within the unverified trusted computing base.
Do not grant a self-modifying agent write/exec access to this controller or
interpret in-memory freezing as a cryptographic proof of runtime integrity.

### Formal research next steps

The full independent Aristotle assignment is in
`ARISTOTLE_CHALLENGE_V3.md`; it prioritizes bounded model
`decode (encode m) = some m` roundtrip/injectivity proofs, a quantized
two-hidden-neuron extension, generic accepted-chain theorems, explicit
trusted-host correspondence contracts and an OOD falsification benchmark.

**Current limitations:** no protected process boundary, independent signed
trust anchor, remote attestation, collision-resistance theorem, OS refinement
proof, concurrent hostile-memory model, GPU/real neural inference semantics,
or universally improving model.


## Independent exact all-integer ReLU reference analysis (v4)

**New Python research modules:** \`universal_relu.py\`, \`layered_guard.py\`,
\`global_falsification.py\`, and \`EXACT_INTEGER_DOMAIN_REPORT.md\`.

For any scalar-input integer network expressible as a finite sum
\(\sum_j a_j\operatorname{ReLU}(w_jx+b_j)+c\), partition the entire integer
line at the exact activation thresholds. The network is affine on each cell,
so three problems reduce to finitely many exact checks:

- **Equivalence on every integer input:** each affine difference must vanish
  identically on nonsingleton cells, or at the sole singleton input.
- **All-integer no-forgetting:** every integer input where the old model
  *exactly* matched the target must remain correct after modification.
  When old-vs-target error is nonzero affine, there can be at most one
  previously correct integer in the cell; it is checked explicitly.
- **Exact worst absolute error** on any specified bounded integer interval,
  by evaluating only cell endpoints.

Tests include random differential checking against integer enumeration,
signed/negative weights, distant correctness roots (1,000,000), hidden-neuron
permutation, 220-unit models, and worst-case error on a trillion-scale
interval without exhaustive enumeration.

An existing seven-point Lean-accepted transition
\(\operatorname{ReLU}(3x-3)\to\operatorname{ReLU}(3x-1)\)
**loses a previously correct output at x=4**. The analytic guard catches
this and still admits the original two valid finite-gate generations in
the reference experiment. The exhaustive lattice comparison reports how
often such failures appear among all 4,081 originally accepted transitions
from 16,384 candidate pairs (see \`global_falsification.py\`).

**Caution:** The new unbounded-domain checker currently has a mathematical
proof sketch and adversarial Python tests but **not** a Lean kernel proof.
Its reference decisions must not be presented as Lean-certified universal
facts, or as production-safe authority. The original immutable-judge and
byte-to-inference execution trust gaps remain. Aristotle's ongoing separate
formal work is not modified by these Python research additions.
