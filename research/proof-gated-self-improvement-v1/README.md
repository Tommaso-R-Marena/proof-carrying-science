# PCS Proof-Gated Self-Improvement v1 (research only)

**Formal claim (finite domain).** For the exact model `f(x)=relu(w*x+b)` or `f(x)=w*x+b`, the trusted policy fixes inputs -3 through 3 and targets `relu(2*x+1)`. A proposed mutation to activation, weight or bias is accepted iff it (1) preserves every previously correct input, (2) correctly solves at least one additional input, and (3) strictly decreases total exact absolute error. This is **not** a claim of unrestricted recursive improvement, general intelligence, or out-of-distribution generalization.

**Lean formalization:** `formal/PCS/V2/ProofGatedSelfImprovement.lean` defines the policy, executable `accept` gate, theorems `accept_sound`, `accepted_preserves`, `accepted_expands`, `accepted_strict_loss`, `two_accepted_steps`, and `perfect_cannot_advance`. The fixed policy is part of trusted source, not user-supplied. A nonzero Lean CLI verdict means rejection. Only a pinned, integrity-verified Lean executable could serve as a production trusted authority; the CLI is an experimental reference.

**Python reference:** `proof_gate.py` mirrors the domain and predicates, builds deterministic transcript hashes, rejects stale or substituting incumbents, invalid fields, weights and policy identifiers, and demonstrates a deliberately limited two-step success path from (relu,0,0) via (relu,1,1) to (relu,2,1). The **Python `check` function is not a security authority**. `check_with_lean` calls the Lean CLI and fails closed on missing toolchain or bad verdicts; its invocation itself does not establish tamper-resistant deployment or prove Python/Lean correspondence.

## Reproduction

```bash
cd research/proof-gated-self-improvement-v1
python -m unittest discover -s tests -v
python proof_gate.py
cd ../../formal
source ../scripts/activate_lean_428.sh
lake exe cache get
lake build PCS.V2.ProofGatedSelfImprovement
lake env lean --run PCS/V2/ProofGatedSelfImprovement.lean relu 0 0 relu 1 1
# ACCEPT (exit 0)
lake env lean --run PCS/V2/ProofGatedSelfImprovement.lean relu 1 1 relu 1 2
# REJECT (exit 1)
```

The reference suite checks 72×72 = **5,184** model transitions exhaustively on a bounded lattice plus **3,000** randomized transitions, parser/type/policy tampering, rollback, changed activation/architecture, finite termination and no-regression invariants. The frozen benchmark has seven tasks, hence strict certification expansion cannot continue indefinitely (at most seven additions of newly certified correct cases).

## Trusted computing base and boundaries

The verifiable result is conditional on the **actual deployed weights matching the encoded model**, exact task interpretation, trusted policy bytes, trusted Lean kernel/build, and a separate tamper-resistant enforcement process. The active model, proposed weights, source, version, protected dataset, score semantics and the gate cannot be under the attacker's unilateral control. An agent could bypass a user-space gate it can modify, alter evaluations, substitute a model at deployment, or exploit unmodeled behavior. There is no cryptographic model-binding or process attestation in v1. Formal verification of finite performance does not establish safety or performance outside the formal domain.

## Research extensions

- Prove a byte-level refinement and canonical encoding from model artifact to Lean interpretation and integrate with PCS's existing authority/receipt infrastructure.
- Extend the exact gate to small fixed-point multilayer networks, finite symbolic programs and formally specified algorithmic-cost improvements. Quantified resource exhaustion must fail closed.
- Hold out separate prospective tests and track generalization (without misrepresenting them as kernel-proved).
- Search for counterexamples, benchmark overfitting and cases where direct gate-improvement paths are blocked even though a better distant candidate exists.
- Build an independently enforceable, pinned deployment root and hostile-agent threat model before allowing real self-modification.

**Evidence status:** Local Python reference tests passed before submitting this branch. The Lean file is intended for kernel compilation and checking in GitHub CI; **do not infer that the Lean proof is checked until that job passes**. Existing PCS self-improvement reports already caution against claiming sustained general capability improvement.
