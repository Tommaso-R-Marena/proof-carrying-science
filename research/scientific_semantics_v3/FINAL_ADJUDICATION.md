# Independent review of the frozen prospective evaluation

A separate agent reviewed all 22 supported reference cases and six counterprobes against original source bytes and the final predictions after the runtime was frozen. This is AI-assisted internal adjudication, not qualified human or external expert validation. The reviewer prepared the references before inspecting implementation or predictions. This review changed no source code, annotations, protocol, or primary results.

The primary result remains **19/22 core matches and 14/22 strict typed/context matches**, compared with **10/22 and 5/22** for the old interpreter under the same new protocol on the same fresh cases. The old PR #202 evaluation remains unchanged and is not directly comparable to these denominators or criteria.

All 28 reference source spans and all 75 generated candidate source spans bind to the expected exact source bytes and hashes. No false positive was found among the 14 supported strict typed/context matches. This is a statement about selected annotated slots, not overall semantic precision across all generated material.

| Final supported cases | Primary result | Independent source assessment |
| --- | --- | --- |
| Five encoded biological parameter values | Core and context match | Correct literal values. Physical units and biological interpretation in other narrative sections are not established by these slots. |
| Two initial amounts | Core match; context miss | Correct amount, compartment and initial-state role. `hasOnlySubstanceUnits="true"` is retained under `declarations`, rather than normalized into `conditions`. |
| Two assignment rules | Core match; context miss | Correct source MathML, symbols and assignment-rule role. The redundant `conditions.rule_type` field is absent. |
| One reaction kinetic law | Core and context match | Correct scoped reaction rate `kd_mRNA*X`; no empirical biological adequacy is inferred. |
| One minute-to-second unit definition | Core match; context miss | Correct exact factor 60. The multiplier is present under unit terms and resolution, rather than `conditions.multiplier`. |
| One biological repression relation | Miss | The direct source statement linking LacI protein PX to inhibition of tetR expression is not extracted. |
| Eight NIST tabulated estimates/statistics | Core and context match | Correctly transcribed reports. They are not independently reproduced fits or validated uncertainty estimates. |
| One NIST exponential response model | Miss | `exp[-b2*x]` is parsed as a subscript on a symbol named `exp`, rather than the exponential function. This is a genuine interpretation failure. Independent equation and numerical checks return `UNKNOWN`. |
| One NIST predictor definition | Miss | The explicit meaning of x as pressure, with unspecified pressure units, is not extracted. |

Five strict context misses therefore reflect field placement, while three core failures concern scientific or mathematical interpretation. These observations do not replace the frozen primary scores with a more favorable post-hoc score. They identify the next representation and interpretation work.

The source-expansion distinction matters. For example, the encoded `tau_mRNA` attribute has no explicit `units` attribute, so the reference and candidate both carry null literal units. The paper/model notes separately discuss minutes. A successful literal parameter match does not demonstrate that PCS resolved that cross-section physical meaning. Similarly, correct recognition of a NIST standard-deviation column does not validate a confidence interval, an error distribution, independence, homoscedasticity or the scientific appropriateness of the fitted model.

The coarse counterprobe metric reports five abstentions out of six, with one core match on the confidence-interval probe. Inspection shows that the actual candidate reports a **parameter standard deviation**, while the reviewer counterprobe asks for a **95% confidence interval** with the same numerical value. The typed/context match is false because the quantity roles differ. No confidence interval was actually asserted, and no scientific authority was granted. All six counterprobes have zero full typed/context proposals. Missing both the true inhibitory relation and its reversed counterprobe is conservative abstention, not demonstrated causal reasoning.

The final numerical regression remains unsupported: the unrecognized bracketed exponential prevents the independent checker from reproducing the Misra1a fit, and the current dispatch also leaves its source-table checks unknown. The final run demonstrates stronger source-grounded organization and interpretation of selected declarations/reports. It does **not** demonstrate independent numerical reproduction of this previously unseen regression study.

The audit record `evidence/final-independent-adjudication.json` contains one entry for every reference, including the source assessment, original metrics, and limitations. It binds primary results SHA256 `5fdd50e46c177deaf2d107ea8a3488938a4fb13bd9b190e7c603b6b7228ab8ae`, software SHA256 `330d32e5ce3fe152ebdb68f7ad20afdfcd62fceb305962ec65f571e09beeed29`, and final reference SHA256 `85fbe7815cc7e826ac6e22b74164223d53edaf30bff8d47b2b70710469e0c754`.

The highest-value next experiment is an independently annotated, fresh family of scientific documents requiring function notation, cross-section units, and biological relation resolution. It should compare stronger deterministic semantic adapters with any learned interpretation under the same source-grounding and independent checking requirements. Expert review remains necessary before interpreting improvements on these small internal probes as general scientific understanding.
