# Threat model (PCS Next)

Adversary classes: malicious producer, substituted policy, mutated packages, stale artifacts,
forged signatures (when pins empty: signature checks optional), compromised local FS.

Out of scope for this candidate: production key theft, OS kernel compromise, Lean kernel bugs
(assumed), social overclaim by humans (mitigated by status separation).
