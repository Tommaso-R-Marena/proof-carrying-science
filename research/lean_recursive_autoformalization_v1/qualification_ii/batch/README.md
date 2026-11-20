# Complete set-translation batches and replayable promotions

A proposal is data. Each revision contains its model/version label and at most eight ordered, literal whole-word substitutions preceding the fixed set-algebra translator. Substitutions consume bounded lengths and contain only alphabetic words and spaces. This admission class permits replay of the actual translator on each source. The proposer supplies no Python, Lean, regular expressions, reference changes, or proof statuses.

The reviewer anchors the exact bytes of the development corpus, final corpus and starting revision outside the proposal. Each corpus binds its split, ordered unique identifiers, source text, and typed references. A response repeats the revision, model, parent receipt, generation, corpus, source-list and verifier identities. The response has one canonical JSON encoding (ASCII escapes, sorted object keys, compact separators) and follows the request order. Every requested identifier occurs once with its own source digest and a typed candidate or explicit null abstention. The receiver bounds UTF-8 JSON before recursive decoding, checks all IDs, bindings, fields and typed candidates, then recomputes every translation before proof checks. A malformed row invalidates the entire response. A kernel timeout or missing elaboration blocks issuance, including for the baseline. The replay of the historical payload calls the same exact-coverage check directly on the archived bytes and rejects the extra `imp_dummy`.

A valid response receives a receipt that binds its exact wire bytes and records separate reference correspondence and theorem-proof verdicts, source/reference/candidate hashes, and the verifier's Lean evidence. Valid correspondence earns one point. A kernel proof of that corresponding statement earns a second. An unrelated, provable statement earns zero. A promotion requires a strict total gain and per-case nondecrease. `advance` rebuilds the supplied history from the reviewer-pinned baseline, checks its head against the caller's current champion digest, and replays the child at precisely that parent and generation. `verify_receipt` replays a detached receipt for byte comparison. `measure_final` rechecks the promoted history and evaluates the exact revision on a separately anchored split with disjoint identifiers and exact source texts. Its result cannot drive `advance`.

## Formal result

For any finite case list, fixed replay function from revision and case to one of three evidence levels, and any history of accepted transitions from revision `a` to `b` of length `k`, `SetBatchPromotion.history_bound_and_preservation` proves that `k + score(a) ≤ score(b)` and that each case retains its initial level. `remaining_promotions_bound` gives `k + score(a) ≤ 2 * cases.length`. Both proofs use Lean's `propext` and `Quot.sound`. The formalization characterizes the policy on replayed evidence. The Python decoder, cryptographic binding, template compiler and any English judgments have their own trust assumptions.

## Replay

From the repository root, place the pinned Lean 4.28.0 executable on PATH and use the repository's pytest environment.

```sh
P=research/lean_recursive_autoformalization_v1/qualification_ii/batch
lean -DwarningAsError=true "$P/Promotion.lean"
python -m pytest -q "$P/test_receiver.py"
python -m research.lean_recursive_autoformalization_v1.qualification_ii.batch.pilot --check
```

The two three-case splits, reference ASTs and literal rewrite were authored and frozen before evaluating the translators. They are replay fixtures, publicly visible, with no independent human annotation or statistical claim. The external model/version label is bound as supplied metadata. The demonstrator's two revisions are hand-authored and use no external generation service. Immutable identities require trusted local verifier sources, a trusted pinned kernel environment and independently retained anchors/head. A multiwriter deployment of this pure verifier would need an external atomic head store. Public corpus files cannot provide secrecy or prevent a researcher from tuning to them.

| Split and revision | Cases | Corresponding | True with kernel proof | False with kernel countermodel | Abstentions | Score |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Development, baseline | 3 | 2 | 1 | 1 | 1 | 3 |
| Development, synonym | 3 | 3 | 2 | 1 | 0 | 5 |
| Final, baseline | 3 | 0 | 0 | 0 | 3 | 0 |
| Final, synonym | 3 | 2 | 1 | 1 | 1 | 3 |

The one rewrite maps “is contained within” to “is a subset of.” On the final split, `f1` correctly translates a false universal inclusion. The kernel produces a singleton countermodel. The phrasing “X contains Y” in `f3` stays unresolved. An adversarial revision that also rewrites “is a subset of B” to “is a subset of A” raises the aggregate development score from 3 to 4 while destroying the correspondence of `d3`. The operational promotion rule rejects it. No sampled-population interval is appropriate for these six deliberately selected cases.
