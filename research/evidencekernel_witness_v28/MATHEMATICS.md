# EvidenceKernel v28 — conditional fairness and failure modes

## Conditional treatment-law reduction

For unit i, let the researcher's 256-bit share be `A_i`, the external witness's share be `W_i`, and the public registered state `s_i` determine a dyadic probability `q(s_i)=m(s_i)/2^b`, `1<=m<2^b`. Define `X_i=A_i XOR W_i` and `Z_i=1{floor(X_i/2^(256-b)) < m(s_i)}`. If either `A_i` or `W_i` is uniformly distributed over `2^256` possibilities and independent of the other **conditional on all earlier experiment history and after the adversary's share is irrevocably fixed**, then `X_i` is uniform, so

`P(Z_i=1 | past, state s_i) = m(s_i)/2^b = q(s_i)`.

Proof: for each fixed adversarial share value `a`, the XOR map `w -> a XOR w` is a bijection of `{0,1}^256`, so the uniform distribution is preserved. Exactly `m(s_i)*2^(256-b)` uniformly distributed bit strings have a high-bit prefix less than `m(s_i)`. This is an elementary, previously known result. No deterministic hash-to-modulus conversion is needed.

**Cryptographic caution:** SHA-256 commitments are computationally hiding, not information-theoretic proof of secrecy. If an unbounded adversary could recover an honest share from its hash commitment, the conditional hidden-share assumption would fail. Even with computational hiding, aborts are a separate and severe issue. No guarantee is inferred merely from valid signatures.

## Scientific inference conditional on a genuine witnessed allocation process

If every enrolled unit's actual assignment is made by that physical process, if registered policy states evolve from the complete, signed feedback stream, and if the preregistered fixed-cohort scientific potential-outcome, interval and stopping premises hold, the exact treatment propensity used by the v25 receiver is the verified `q(s_i)`. V28 requires the reference weights and upper propensity fields of *all registered v25 tuning configurations* to equal `q(s_i)` exactly. V25's existing conditional martingale and interval bounds then apply. Thus one can replace an externally asserted numerical propensity ceiling with a **different external assumption**: at least one secretly random honest party, truthful chronology/complete custody, and no selective abort.

This assumption is not weaker in every setting; a faithfully calibrated trusted randomization device might be preferable. V28 is complementary to v27, not a universal dominance result.

## Exact attacks and limitations

1. **Selective abort:** if a unit's treatment assignment is fair with `P(Z=1)=1/2`, but the operator completes the enrollment only when `Z=1`, then `P(Z=1 | completed)=1`. The submitted records can still contain valid commitments and signatures. The verifier alone cannot detect never-submitted sessions, so an independent witness must log all attempts and aborted sessions. The test suite checks this exact 256-value example.
2. **Precomputation/collusion:** if both parties know the shares before either is committed, they can select joint values yielding arbitrary `Z` and still produce perfectly valid signatures and matching hash commitments. External prior commitment ordering and honest hidden randomness are essential.
3. **Incorrect denominator:** mapping a uniform byte `r` to `r mod 3` yields `[86,85,85]` across three outcomes, not a uniform distribution. This research implementation therefore allows only dyadic treatment probabilities and an exact prefix comparison; unsupported rational probabilities fail closed.
4. **Backdating:** an Ed25519 signature proves that a key signed a message, not its creation time. The double-signed receipt is a useful witness attestation only with externally retained chronological logs and a trusted independent key holder.
5. **Mutable scientific endpoints:** signer-approved allocation receipts do not attest physical outcome measurements, noninterference, complete enrollment, or the pre-registration chronology. Any such failure defeats the causal conclusion.

**The contribution is a bounded, independently implemented integration and an explicit demonstration of where cryptographic evidence does and does not close statistical trust assumptions. No novel cryptographic or martingale theorem, external assurance, or biological efficacy claim is established.**
