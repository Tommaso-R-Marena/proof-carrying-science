# PCS Semantic Contract v1 — actual integration ledger

Target source is feature/pcs-parallel-integration-v1-20261008, stacked on PR #79 and PR #78. Preserve the existing formal core and experimental Python prechecker.

## Real checker interface
Aristotle v1 uses schema pcs-semantic-translation-v1 for requests, pcs-semantic-authority-v1 for the registry and trusted verifier keys, and pcs-semantic-decision-v1 for results. The compiled executable pcs-semantic-check takes two canonical JSON files and returns exit 0 iff ACCEPTED; code 1 on REJECTED or NEEDS_CLARIFICATION. This differs from the existing Python prechecker schema. Never reinterpret a model-authored claim statement or confidence as the actual selected structured interpretation.

The Python bridge in pcs/semantic_kernel_bridge_v1.py hashes and verifies the binary and authority exact bytes, checks strict canonical JSON and output consistency, and returns CHECKER_ACCEPTED_BOUNDED only when the pinned binary actually accepts. It ALWAYS reports pcs_scientific_authority false. Binary hashing establishes byte identity, not an independent Lean theorem or compiler proof. Trusted deployment configuration, not a model request, must supply the pins.

## Missing formal integration (release blocker)
The user-uploaded complete Aristotle archive was inspected previously and a guarded integration bundle was produced. Its ZIP SHA-256 is aba3a7f3bff15065e63d16587cff1dd3d7a63da6531872d8f545e534260c7f9e. It has not been committed to this remote branch. The only planned modifications of pre-existing formal sources are appended imports to formal/PCS.lean and a new executable in formal/lakefile.toml. Run scripts/check_aristotle_semantic_source_v1.py before full Lean validation; it rejects absent modules and fixture drift rather than silently passing.

In a clean checkout of this branch, inspect/apply the guarded source overlay and commit it. Then run from formal/: lake build; bash tools/run_semantic_fixture_tests.sh; python3 -m unittest discover -s python/tests. From the parent repository, also run complete PCS pytest, authority fixtures, adversarial campaigns and cross-language byte vectors. Do not mark full release PASS on a partial or skipped check. Keep credential/signing key material outside repository and CI logs.

## Training and evaluations
scripts/build_semantic_golden_benchmark_v1.py converts source fixtures to an explicitly machine-generated regression benchmark. Its output does not claim actual human interactions, actual learned-model supervision, or independent Lean reruns. Train/evaluation partition labels are fixture-specific and insufficient as a broad generalization claim. Real gameplay trajectories must go through independent consent/PII/data provenance governance.

## OPEN trust boundaries
Full v1 source import; independent proof checker binary tested on exact integrated revision; Claim IR symbol mapping and human confirmation; external actual-Lean declaration grounding, elaboration and proof issuer; provenance/versioned evaluation and privacy; core repo publication and Cloudflare shared-token isolation. Website Workers cannot run arbitrary Lean locally. A privileged, isolated job runner plus authenticated receipts is needed for live checker-backed user submissions.
