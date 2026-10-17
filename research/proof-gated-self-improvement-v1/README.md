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

- **21 Python tests** (CI): 5,184 exact finite-lattice transitions, 3,000 randomized transitions,
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
