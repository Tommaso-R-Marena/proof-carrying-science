# Finite response models and sharp trial bounds

The research receiver answers one question. Given an independently randomized binary treatment, binary outcome, arm size (N>0), and marginal responder counts (c,r) in the two arms, which counts of individual responders to treatment are compatible with those margins? Here the counts are **exact population masses on a common integer grid**. Sampling error, causal assumptions and extraction of the margins from a study require separate justification.

The unit model has a treatment-assignment bit and two potential outcomes. Every response type occurs with equal multiplicity in both assignment arms. The observed outcome uses the structural equation selecting the potential outcome corresponding to the assigned treatment. Benefit means that intervening on this same unit changes its outcome from zero to one. Write (k) for its count per (N) units. Lean proves that the compatible values are precisely

```text
max(0, r − c) ≤ k ≤ min(r, N − c).
```

The proof constructs a complete response table for every such integer. Equality of the endpoints characterizes point identification. The population interpretation divides each count by (N). The construction specializes classical Fréchet bounds on binary potential outcomes. See Jin Tian and Judea Pearl, “Probabilities of causation: Bounds and identification,” *Annals of Mathematics and Artificial Intelligence* 28 (2000), 287–313. The contribution here is the executable finite model, constructive proof and replay against a separately implemented table enumeration.

| Status | Result | Assumptions and scope | Evidence |
|---|---|---|---|
| FORMALLY_PROVED | Structural solution exists and is unique for each simultaneous intervention. Matching every assigned component in the factual world preserves the solution, including after conditioning. | Equations on a typed, finite ordered schema, finite-support integer-weight exogenous law, fixed shared exogenous state across interventions. Empty evidence mass returns `none`. | `FiniteResponse.solves_iff`, `consistency`, `conditional_consistency` in [FiniteResponse.lean](lean/PcsPccr/FiniteResponse.lean) |
| FORMALLY_PROVED | Every compatible helped-cell count is attained, and a proposed interval passes precisely when it equals the full achievable set. | Binary randomized population as specified above. Finite counts; stochastic assignment in a real trial does not establish exact equality of arm populations. | `sharp`, `identified_iff`, `accepted_iff_exact` in [SharpResponseBounds.lean](lean/PcsPccr/SharpResponseBounds.lean) |
| FORMALLY_PROVED | Two models can agree on the four observational masses and both interventional responder masses while the conditional probability of responding under treatment among untreated nonresponders takes values zero and one. | All positive multiplicities (m), all nonnegative excess always-responders. Increasing the excess changes even the common normalized observable law. | `opposite_conditionals` in [SharpResponseBounds.lean](lean/PcsPccr/SharpResponseBounds.lean) |
| EXECUTABLY_VERIFIED | Separate Python table enumeration reproduced both Lean endpoint witnesses for all 284 margin pairs with arm sizes 1 through 8. | Enumerates 494 four-cell tables. The comparison rejects 19,380 incorrect intervals, 3 infeasible populations and 8 malformed lines. The 19,675 decisions are exhaustive within the stated grids and directed parser examples. | [Replay script](scripts/replay_response_bounds.py) |

## Replay

From this research directory, put the pinned Lean 4.28.0 distribution on PATH. Run:

```sh
(cd lean && lake build && lake env lean ResponseAxioms.lean)
python3 scripts/replay_response_bounds.py
(cd lean && printf '4 2 2 0 2\n4 2 2 1 2\n' | lake env lean --run CheckResponseBounds.lean)
```

The example prints `ACCEPT 2 0 0 2 0 2 2 0` and `REJECT`. The eight numbers in the first response encode the lower and upper endpoint witnesses in never, helped, harmed, always order. Each input line supplies five canonical unsigned decimals of up to 18 digits, separated by single spaces. The first three fields come from the trusted study context. The last two are the proposed interval. Output is per-line. An invalid interval produces `REJECT` and a field grammar error produces `MALFORMED`.

The axiom probe checks twelve declarations. Unit-level consistency has no axioms; the remaining closures use subsets of Lean's standard `propext`, `Quot.sound` and `Classical.choice`. The new proofs use kernel-checked tactics, including arithmetic certificates. The running receiver additionally trusts the Lean compiler/interpreter, decimal parser, host and supplied study counts. The theorem pertains to `checkInterval` over Lean natural numbers. The parser and text printer are exercised by replay. The receiver establishes a numerical subclaim, with source identity, randomized assignment, measurement validity and natural-language fidelity remaining external.
