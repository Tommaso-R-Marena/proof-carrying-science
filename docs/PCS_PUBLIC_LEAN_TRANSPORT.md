# Bounded public Lean proof-result transport

The actual three-policy induction request produced 960,268 UTF-8 JSON bytes. Encoding that result as one Base64 log line required 1,280,379 bytes. The complete result now compresses losslessly into a 35,372-byte marked log line. No proof, state, comparison, provenance or explanation field is removed from an eligible result.

The original hosted attempt remained in progress beyond its configured timeout and was cancelled; the provider returned no usable logs. Its cause is unresolved. This change removes the measured oversized-line exposure. Hosted success must be recorded independently, rather than inferred from the local result or transport tests.

## Contract

`public_transport.serialize_result` emits one `PCS_LEAN_RESULT_GZIP_V1:` line containing Base64-encoded gzip. The inner `pcs-public-lean-result-v1` object is unchanged. Limits are 1,000,000 decoded JSON bytes and 48,000 compressed bytes, keeping the complete ASCII log line below 64 KiB. Exceeding either limit emits a bound request with `resource_exhaustion`, no accepted proof and no scientific authority.

The Worker streams gzip decoding with the same byte limits, fatal UTF-8 decoding and gzip integrity checks. Exactly one result declaration is allowed across legacy and compressed formats. Missing, duplicate, mixed, malformed, truncated or oversized results fail closed. Legacy plain results remain readable.

Compression grants no checker authority. Successful approved workflow/job provenance, immutable core/source/interpretation/action bindings, allowed kernel axioms and the exact original theorem remain required. All model weights, search budgets, theorem statements, proof actions, RL rewards and protected mathematical gates are preserved. Training consent and independent replay remain separate requirements. No financial resource or paid dependency is introduced.

## Executed verification

- Five Python transport tests cover Unicode, lossless large results, deterministic encoding, marker injection and both byte-exhaustion cases.
- Twenty-one website protocol/reuse tests, including native workerd decoding, and ten Bridge tests pass. New negative cases cover corrupted gzip, expansion bombs, mixed/duplicate markers and forged source/action/interpretation/axiom bindings. Protocol fixtures are not mathematical evidence or participant data.
- Fresh smoke rechecks eight admitted lemmas, an actual five-action learned proof and the exact six-action public human-path entry point using the compressed producer.
- The actual full three-policy result round-trips byte-for-byte through gzip and preserves all three verified five-action outcomes.

```bash
source scripts/activate_lean_428.sh
python -m pytest -q tests/test_public_proof_transport.py
python scripts/check_abstraction_proofs.py
cd ../proof-carrying-science-site
npm run test:lean-research
```

The full formal gate and both repositories' existing protected release checks remain mandatory. A log codec test is not a fresh mathematical proof, and a local execution is not a successful hosted execution.
