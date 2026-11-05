# PCS Studio v0.5 — threat model, scoped claims, and known gaps

## Roles and assumptions

**Proposer:** uploads an AI or scientific model, a declared model property and a scoped input range. Both inputs and the proposer's own property declarations are untrusted unless a reviewer independently accepts them.

**Local inspector:** parses a bounded set of model formats and produces detailed observations. It does not call the PCS Lean kernel. The parser, dependency graph, host process, operating system and local filesystem remain within the tool's trusted computing base.

**Numerical reference workers:** receive a strictly screened JSON computation graph rather than the original ONNX bytes. NumPy/PyTorch execute small arithmetic operations in separate processes. Subprocess isolation is not a hardened OS security boundary, and no random third-party code is executed intentionally.

**Publisher:** may sign a receipt using an Ed25519 private key. Possession of a valid signature authenticates only the exact receipt content to the pinned key; it does not prove the publisher's policy is appropriate or their tools are trustworthy.

**Reviewer:** independently receives the source model, exact policy/receipt/proof and a trusted public-key fingerprint. The reviewer's reanalysis can test exact byte consistency, local replay and finite-cover proof reconstruction, but remains dependent on the same model semantics interpreter.

## In-scope examples

- Exact rational conditional real-arithmetic upper/lower bound for a tiny explicit dense FLOAT32 graph under an input-box assumption; PASS requires a fully covered finite partition and each leaf recomputed.
- Existence of a particular numerical reference violation for a specific float32-valued input, with exact model/policy hashes, numerical outputs, and independently replayable source bytes.
- Syntactic and limited semantic interpretation of small SBML reaction networks, documented stoichiometric invariants and explicitly annotated element/charge balance (assuming reaction-only dynamics and correct chemical annotations).
- Rejection of unauthorized action proposals before they reach the synthetic in-memory tool dispatcher under a fixed host-owned policy.

## Explicitly out of scope

- Arbitrary ONNX operator semantics, ONNX Runtime execution, GPU behavior, model weights stored externally, dynamic axes, custom kernels, control-flow graphs, any ONNX model with unsupported topology or parameters.
- Mathematical soundness of the Python implementations under all attacks, IEEE-754 complete reasoning, full binary32 error bounds, secure arbitrary-artifact parsing, cryptographic proof of audit completeness, signed external telemetry, host compromise, filesystem rollback or third-party revocation.
- Full AI alignment, safety against prompt injection, privacy guarantees, clinical validity, regulatory approval, simulation fidelity, protein conformational plausibility, laboratory replication, or causal scientific truth.
- True PCS v0.6 certificate production, Lean theorem import, kernel replay or accepted signed packages. The PCS-shaped JSON is an untrusted candidate claim inventory.

## Known failure modes and mitigations

1. **False confidence from static PASS:** overall decision intentionally remains OPEN unless there is a scoped FAIL; no unconditional SAFE status.
2. **Lost correlations in interval arithmetic:** capped finite subdivision can sometimes resolve a true bound; incomplete proof remains OPEN. A complete tree still relies on the limited real-number semantics interpreter.
3. **Blind spots in random probing:** opt-in SciPy MILP seeks interior counterexamples, but is only a challenger. Solver timeout/infeasibility is never proof of safety; all proposed inputs are float32-normalized and re-evaluated exactly.
4. **Floating-point mismatch:** optional NumPy and PyTorch independently compute screened operations with recorded outputs and an explicitly approximate comparison tolerance; neither is official ONNX Runtime.
5. **Forged unsigned receipt:** the receipt binds the model/policy via SHA-256 but is recomputable. Optional publisher Ed25519 sidecar requires independent key fingerprint pinning; signatures alone do not prove correctness.
6. **Bypassed in-memory tool guard:** demo guard mediates toy tool effects only; any actual agent could access tools through an alternate route unless a future deployment ensures exclusive, least-privilege dispatch and independently anchored telemetry.
7. **Untrusted native-parser attack surface:** application listens on localhost, caps input size and rejects overt executable serialization disguises, but does not provide secure process/container isolation or a complete supply-chain audit.
8. **Differential replay portability:** installed dependencies and underlying BLAS/CPU implementations can change exact outputs and hash-bound receipts. Replay intentionally refuses mismatched code versions.

## Roadmap acceptance gates before real-world use

- Supported-operator semantics checked against official ONNX Runtime with pinned artifacts and truly isolated workers.
- Reviewer-owned behavioral/specification property semantics with well-formed typed IR and explicit threat context.
- A formally machine-checked trusted verification component (Lean) for the exact supported checker or constrained soundness theorem.
- Tamper-evident, independently anchored and authenticated tool-execution records, plus secure exclusive dispatch.
- Cleared external partners and independently audited evaluation sets with documented failures and counterexamples.
