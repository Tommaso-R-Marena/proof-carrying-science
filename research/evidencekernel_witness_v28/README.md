# EvidenceKernel v28 — Witnessed randomization receipts for prospective experiments

**Research only. Not an external witness service, a PCS kernel theorem, an authenticated trial, or a clinical result.** This isolated module connects a *bounded cryptographic ceremony* to the existing v25 exact-rational, anytime-valid causal inference receiver. It addresses v27's largest structural limitation: **past calibration alone cannot certify the conditional treatment probabilities actually used in a later study** if the physical assignment mechanism can drift.

## What the implementation does

For each enrolled unit, the operator and an independent witness contribute separate 256-bit shares. Both share commitments, the current preregistered policy state and previous-record hash are included in an **Ed25519 witness-signed commitment receipt**. After the two shares are revealed, a second witness signature binds the reveals, treatment assignment, feedback report and prior receipt. The next record binds the entire signed previous record; missed, reordered, forged or altered records fail closed.

The assignment is `1` exactly when the high `b` bits of `(operator_share XOR witness_share)` are less than `q * 2^b`, with `1 <= b <= 20`. The registered statewise treatment probability `q` is required to have an exact dyadic representation with denominator `2^b`. A full 256-bit XOR preserves uniformity when at least one share is independently uniform and hidden from the adversary while both shares are fixed. The deterministic threshold introduces **no modulo-reduction bias**. The module verifies all v25 tuning references and propensity ceilings equal the probability of the witnessed draw in each state; no hidden statistical calibration delta is added for a mere asserted probability ceiling. A separate externally asserted measurement-calibration failure budget remains.

The Python cryptography backend uses `cryptography==46.0.4` (Ed25519 verification). The separate JavaScript implementation uses Node.js built-in Ed25519 verification, BigInt and its independent v25 inference receiver. Both reject noncanonical signatures and malformed scientific inputs. The witness's signing secret is NEVER required by or distributed with the verification code.

## The main caveat: cryptographic verification is not physical assurance

**Signatures authenticate what the key holder signed, not when the ceremony happened or whether the signer was independent.** The verifier cannot prove enrollment was complete, commitments preceded reveals, either share was fresh and genuinely uniform, no party withheld a reveal or enrolled units selectively, or outcomes were genuine. These require a prospectively registered, separate trusted custodian and independent retained/dated receipts. Hash-commitment hiding also depends on computational assumptions. At least one share must be hidden at the time the other participant fixes theirs; otherwise a dishonest participant can predetermine the XOR.

In particular, the code's `make_demo.py` uses a **publicly reproducible, insecure synthetic signing key and deterministic synthetic shares**. Its output only demonstrates that the verifier checks messages correctly. It cannot be used as an independent attestation or an actually randomized study, even though all signatures verify.

The additional proof obligation is **abort-resistant, complete enrollment custody**. An operator who discards unfavorable completed draws can make a fair 50/50 process appear to produce 100% treatment in the *selected* transcript. The regression suite reproduces this exact attack. V28 rejects inconsistencies **within a submitted enrolled prefix**, but cannot detect entire sessions or subjects omitted before the submitted prefix. Deployment would require a witness that independently retains *all enrollment requests, commit receipts, reveals, cancellations and aborts*, with failures counted as terminal failures rather than silently retried trials.

## Reproduction

Run from the PCS repository root (Python 3.12+, Node.js 20+, `cryptography==46.0.4`):

```sh
python -m pip install cryptography==46.0.4
python -m unittest discover -s research/evidencekernel_witness_v28 -t . -v
python -m research.evidencekernel_witness_v28.make_demo  # SYNTHETIC ONLY
D=research/evidencekernel_witness_v28
python -m research.evidencekernel_witness_v28.kernel \
  "$D/example_ceremony_contract.json" "$D/example_study_protocol.json" "$D/example_witness_evidence.json" \
  --contract-pin "$(cat "$D/example_contract_pin.txt")" \
  --study-pin "$(cat "$D/example_study_pin.txt")" \
  --evidence-pin "$(cat "$D/example_evidence_pin.txt")"
node "$D/independent.js" \
  "$D/example_ceremony_contract.json" "$D/example_study_protocol.json" "$D/example_witness_evidence.json" \
  "$(cat "$D/example_contract_pin.txt")" "$(cat "$D/example_study_pin.txt")" "$(cat "$D/example_evidence_pin.txt")"
```

The synthetic 256-unit demonstration has all positive potential effects; it produces a conditional ATE lower bound `83/128` from 256 verified signed draws. The statistical *claim* is NOT justified for this demonstration because its deterministic pseudo-random shares are public and were not produced by an independently witnessed randomized process. The numerical result is useful **only as a software-replay fixture**.

The suite covers forged witness signatures, modified commitments, altered reveals, missing/reordered draws, changed reports, tampered protocols, no valid dyadic probability, exact 256-way XOR enumeration, selection-after-reveal, and Python/Node agreement over 40 perturbed-outcome cases. All relevant claims are conditional; no Lean theorem or prospective real-trial evidence exists yet.

## Prior art and next steps

Two-party commitments and coin flipping date back to Manuel Blum (1981); verifiable random beacons and auditability are also established. See *Coin Flipping by Telephone* (CRYPTO '81) and NIST *Interoperable Randomness Beacons*. This is an **integration/replay research prototype**, not claimed novel cryptography. Meaningful advancement now requires a functioning independent witness service with signed time-and-completeness custody, a prospective frozen experiment, and independent wet-lab or measurement verification. Do not merge or deploy without security review.
