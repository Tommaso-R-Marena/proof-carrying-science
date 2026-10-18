# Reproduce the integrated research

Use a fresh checkout of the integration branch and Lean4.28.0 via scripts/activate_lean_428.sh. Install research/integration_v1/requirements.lock with pip --require-hashes, then pip install --no-deps --no-build-isolation -e . This is a research qualification environment, not a new production dependency requirement.

Run python scripts/check_repository_integrity.py and python -m research.integration_v1.source_gate. The latter reads1977+ pinned source identities and never regenerates expectations. Run ./scripts/verify_lean.sh and ./scripts/verify_lean_real.sh. Large cryptographic/golden modules may need serial prebuilds on a9.7GiB host; never alter statements, admit proofs or forge build traces to reduce resource use.

The new .github/workflows/pcs-integration-research.yml is the executable qualification inventory. It runs each original Python stream in its own process with scratch result paths, checks for skipped tests, builds real authority/certificate dependencies, executes15 cross-PR tests, and queries every public theorem's actual type and axiom closure in each isolated project. The original V5/V6/V7, controller, checkpoint, journal, native PGSI1, affine and pointwise workflows remain active. Frozen jobs only adapt their working directory and path triggers.

Run python -m research.integration_v1.demo --out /fresh/output. A clean Git archive must reproduce the semantic report digest. The report binds SOURCE_PROFILE.json and names OPEN obligations. No empirical or deployment authority is emitted. A matching hash is identity evidence, not a signature.

Historical frozen campaigns use research/isolated/pgsi1/research/proof-gated-self-improvement-v1. Build a fresh authority bundle, set PCS_PGSI_AUTHORITY_BUNDLE and PCS_PGSI_REQUIRE_NATIVE=1, execute tests, kernel/tests and pointwise/tests, then original campaign/verify_results/negative-control/oracle/preserved-composition commands. Use fresh output directories; never regenerate old expected hashes.

Dependency-cache sharing verifies exact manifest revisions and clean tracked source before linking an owned checkout cache. It is a build optimization, not binary attestation. Reconstruct the cache with lake exe cache get in a fresh checkout. Actual tested toolchains, durations, commands and source commits remain in evidence records; timestamp-bearing logs are distinct from deterministic semantic outputs.
