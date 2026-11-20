# Unary predicate translation pilot

One zero-shot batch to Gemini 3.5 Flash Lite, temperature 0, with a 1,536-token output cap, public synthetic prompts, and no repairs. The request omitted the set-theoretic reference. The protocol, reference and input digests were computed before generation. The service reported 298 prompt tokens and 256 completion tokens (554 total) on the user-confirmed free tier. This design used one generation request.

All 12 requested expressions agreed with the researcher's reference on all 15 nonempty subsets of the four possible unary predicate profiles. **The batch failed the response contract** because it also supplied an unrequested ID. The output is retained verbatim inside the response receipt. No second attempt was made. This is a hand-authored diagnostic of one constrained grammar. It has no population accuracy estimate, independent human semantic annotation or FormL4 comparability.

From this directory run `python3 replay.py` and compare with `score.json`. Run `lean ProfileQuotient.lean` with Lean 4.28.0. The theorem proves truth invariance for arbitrary domains whose objects realize the same unary predicate profiles, for equality-free one-variable formulas in this grammar. Its axiom audit lists `propext`. The executable scorer, JSON parser and English-to-reference judgments remain outside that proof. Probing the API again is optional and consumes a new request.

## Replay of the 12 individual equivalences in Lean

The following also checks each recorded formula against a handwritten logical counterpart to the pre-call set reference. It quantifies over arbitrary domains. These formal counterparts were supplied after observing the response. They are available for independent review against the frozen English and Python references. The name and arity checks in the generator allow only the declared grammar to enter the compiler.

```bash
set -eu
out=$(mktemp -d)
cp ProfileQuotient.lean "$out"
python3 check_formulas.py > "$out/RecordedFormulas.lean"
(cd "$out" && LEAN_PATH=. lean -DwarningAsError=true -o ProfileQuotient.olean ProfileQuotient.lean && LEAN_PATH=. lean -DwarningAsError=true RecordedFormulas.lean)
```

All 12 equivalences passed on Lean 4.28.0. Their combined audited dependency set was `propext`, `Classical.choice` and `Quot.sound`. Individual equivalences apply to the requested keys. The extra ID still causes the wire contract to fail.
