# Primary final reference and outcome review

This is a **post-evaluation, internal AI-assisted review**, with a separate read-only source-binding audit. It is not external validation, qualified scientific adjudication or a human usability study. No annotation, protocol, grading code, primary score or mathematical/scientific authority was changed. The later Smith resource-budget repair is excluded from this primary assessment.

## Exact evidence and source binding

The reviewed reference payload is `reference/final.json`, SHA256 `9ef141e1150979bb4e5e37c76fdfe38260537a331eb87598a7fae983a7060644`. All **85 original source bindings pass**: the stated file resolves unambiguously, its SHA256 matches, and the recorded UTF-8 byte interval equals the quotation. There are 70 supported source-statement interpretations, 9 contradicted probes and 6 insufficient-evidence probes. Their kinds are 49 scientific claims, 20 quantities and 16 equations.

The review reads the frozen `evidence/final-first-results.json` and accepted primary packet outputs. [final-error-atlas.json](evidence/final-error-atlas.json) contains one row per annotation, exact source identity, original outcomes, execution/replay validity, original candidate-comparison counts, same-artifact/overlapping-span counts, diagnostic field differences and explicit absence of new credit. It retains the original software digest `582d2da92d8e946e57eb3ff8d04dfb3b4db553286dd0676639dac444e4eaa226` and binds the result bytes by SHA256.

| Project | Reference supported/probes | Actual v3 claims | Frozen v4 claims | V4 paper claims | Accepted primary review and replay |
| --- | ---: | ---: | ---: | ---: | --- |
| Schwen2015 |22/5|58|63|5|Yes|
| Bertozzi2020 |23/5|16|16|0|Yes|
| Smith2013 |25/5|Unavailable|Unavailable|Unavailable|No; both workers timed out|

An unavailable primary interpretation is not an empty successful extraction. Smith's 25 supported claims and 5 probes remain failed-case denominators; later outputs cannot replace them.

## What the zero score establishes

The original principal core and typed/context scores remain **0/70 for both pipelines**, and explicit workflow answers remain **0/24**. The strict grader first selects candidates with exact equality of the reference's `entity` and `kind`; only then does it compare source, scope, relation, value and context. **Across all 85 rows, both engines have zero selected candidate comparisons.** Matching-pair precision is therefore undefined, not 0% or 100%.

Some reference identifiers are curator-selected scientific labels rather than universal source identifiers. For example, Schwen's `τ_typ` with human/mouse branches is labeled `tau_typ_human` with a prose scope; `K_{a,l}` becomes `K_a_l`; Smith's original `R1f` kinetic-law encoding is labeled `v_R1f` with a prose scope. Bertozzi's `ln2/alpha` is represented as `log(2)/alpha`, requiring notation normalization and appropriate domain assumptions. These interpretations can be reasonable, but exact-label matching alone is not a calibrated measure of arbitrary scientific meaning. Literal source binding does not independently settle those semantic choices.

The zero score must nevertheless not be dismissed as merely grading trouble. Looking beyond the entity/kind prefilter to exact source spans gives the following exhaustive supported-row diagnosis:

| Primary diagnostic | V3 | Frozen v4 |
| --- | ---: | ---: |
| Failed project; no accepted interpretation |25|25|
| No candidate from the annotated artifact |44|23|
| Candidates in that artifact, none at annotated source span |1|21|
| Source-span overlap, incomplete/incompatible typed representation |0|1|
| Total |70|70|

All 23 Bertozzi supported claims fall into the v4 no-candidate-from-artifact category: its paper and annotated MATLAB sources produce no supported scientific interpretation records. Its curated SBML declarations are a different scope. Schwen's five paper records are narrow assumptions rather than the principal mathematical, numerical and biological findings requested by the references. Twenty-one supported rows have no overlapping candidate. These are substantial coverage failures independently of exact identifier conventions.

The one partial-overlap example is **S08**: v4 preserves the source's assumption of “a total fat accumulation of 9.2% of the liver volume” in a source-bound prose record. It does not produce the expected typed quantity, entity, scientific scope, percentage unit and conditions. The atlas records that partial source-information capture without assigning typed semantic credit or treating the scientific assumption as verified. Sharing a paragraph is never used as proof that two scientific propositions have the same meaning.

## Scientific utility and remaining obligations

The accepted Schwen/Bertozzi packets provide a usable audit trail of captured files, scoped SBML declarations/equations, declared dependencies and exact residual calculations. Schwen has 38 source declarations and 14 scoped equations checked; Bertozzi has 9 and 2. V4 additionally reports fixed parameter-domain, measurement-reference and supplied-prediction residual checks. The 286 Schwen and 22 Bertozzi supplied prediction rows were joined to measurements, but this does not establish fresh execution of those models or reproduction of their complete published findings. Schwen's conditional ODE checker abstains for unsupported preequilibration/budget; Bertozzi's SBML level is unsupported. The paper's spatial model, statistical interpretation, uncertainty, empirical conclusions and original-author source correspondence remain unresolved.

No unsupported scientific authority promotion is recorded. This finite, selected result is not exhaustive interpretation precision: unannotated candidates have not been scientifically adjudicated, and source/symbol checks cannot certify biological truth. The 10 unsupported probes absent from valid outputs are **absence of a matching proposal**, not demonstrated scientific refutations or informative researcher answers. The 5 probes in failed Smith receive no abstention credit. No explicit workflow answer was produced for any of the 24 questions, so computational assistance cannot be advertised as successful question answering.

The reference preparation and this review do not replace domain experts. Expert assessment should adjudicate source meaning, allowable identifier/equation aliases, units, experimental conditions, uncertainty and scope before a genuinely new prospective benchmark. A useful successor should separately measure source-span recovery, typed interpretation, scientific equivalence and task answers, with independent checks for each. The present final set is now exposed and is diagnostic material only. Neither scores nor expected source meanings should be rewritten to make the current system look successful.
