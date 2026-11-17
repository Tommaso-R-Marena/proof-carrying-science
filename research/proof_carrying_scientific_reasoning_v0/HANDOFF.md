# HANDOFF — Proof-Carrying Scientific Reasoning v0

- **Branch:** `research/proof_carrying_scientific_reasoning_v0`
- **Base:** `bc78660b` (`BASE_COMMIT.txt`)
- **Exclusive path:** `research/proof_carrying_scientific_reasoning_v0/`
- **Lean:** 4.28.0; `cd lean && lake build`
- **Tests:** `bash scripts/check_all.sh`

## Done (Milestone I–V subset)

- Recon + isolation scope
- Formal spec + Lean core (soundness, authority, non-explosion, retraction, certificates)
- Python reference + independent checker
- Adversarial tests + PK/PD + conflicting-studies case notes
- Prior art / novelty matrix (honest: composition, not foundational breakthrough)

## Next

- Stronger certificate step-linking proofs in Lean
- Finite-model exhaustive enumeration for tiny formula spaces
- Additional case studies (proteomics synthetic; causal assumptions)
- Benchmarks methodology + results
- Draft PR CI census expected red — do not weaken
