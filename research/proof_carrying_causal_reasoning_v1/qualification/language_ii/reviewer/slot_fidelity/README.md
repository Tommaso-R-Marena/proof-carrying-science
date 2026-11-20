# Typed-slot fidelity on the 72 frozen reviewer cases

The locked parser emitted a typed claim on **48 of 72 cases (66.7%)**. Every emitted claim matched all seven scored fields. The 48 include 24 cases on which the decision stage correctly abstained. These comprise 12 cases with a missing arm rate and 12 with a zero conditioning probability. Interpretation coverage and justified answer coverage therefore differ on this corpus.

| Family | Cases | Complete matching claims | No claim |
| --- | ---: | ---: | ---: |
| Observational association | 12 | 12 | 0 |
| Randomized intervention | 12 | 12 | 0 |
| Missing arm rate | 12 | 12 | 0 |
| Zero conditioning probability | 12 | 12 | 0 |
| Possible unmeasured common cause | 12 | 0 | 12 |
| Fair-coin intervention paraphrase | 12 | 0 | 12 |

All 24 missing interpretations stopped at the background parser. The common-cause cases required a decision abstention but still expressed a causal question. The fair-coin cases supplied enough evidence to answer and yielded no typed interpretation. Together these cases contained 60 of the 168 design probability facts.

The comparison covers query kind, treatment, outcome, contrast direction, ordered intervention arms, stated background, and the complete multiset of probability facts (marginal, joint or conditional, with event, negated or positive condition, and percentage). The design uses binary exposure and outcome names across all cases. An observational question has no intervention arms. This exercise contains no adjustment set comparison or named causal graph. An unexpected graph, latent name, or method is flagged. The checked cases provide no positive evidence for extraction of those structures.

Every one of the **108 emitted percentage literals** matched its design value and operands. The independent design generated exact percentages. The receiver deliberately applies a half-percentage-point rounding enclosure to each displayed percentage. All 108 enclosures contained the exact design value and none was a singleton. The counts of matching literals therefore establish transcription fidelity. The resulting precision differs from the generator's. The report also counts inferred conventions separately, including the 24 declarations each of consistency, modular intervention and positive arm support on typed interventions. These conventions add conditions for inference beyond the background text.

This audit was devised post hoc after the original sign evaluation. `references()` transcribes the independent coordinator design's three name pairs, two probability tables, two directions, and six ordered families. It receives no public text, answers, or parser results. The released case bytes matched the original design's causal output byte-for-byte. The full original script's SHA-256 is recorded alongside the checked parser and corpus digests. Only the three public text fields reach the parser. The reference construction used the untouched design, with no parser tuning, model call, or human semantic adjudication. Counts describe this finite template grid.

Run both commands from the repository root.

```sh
python -m research.proof_carrying_causal_reasoning_v1.qualification.language_ii.reviewer.slot_fidelity.replay
python -m pytest -q research/proof_carrying_causal_reasoning_v1/qualification/language_ii/reviewer/slot_fidelity/test_slots.py
```

The tests replay the checked-in result and inject changes to endpoint roles, direction, facts, negation, policy assumptions, query kind and intervention arms to confirm the scorer detects them.
