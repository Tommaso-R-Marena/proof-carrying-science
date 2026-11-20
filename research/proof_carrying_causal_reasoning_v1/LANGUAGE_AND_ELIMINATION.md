# Population causal questions and exact variable elimination

## Language and decision boundary

The new public-text interpreter answered 2,471 of 10,112 exposed CLadder questions. It matched 2,464 labels and disagreed with seven. The Phase I text rule answered 425, with 423 matches. Both rules see exactly the background, given information and question. The new rule was written with access to public examples from this previously exposed corpus. Its output was locked before scoring against the answers. The test partition likewise measures exposed performance. The reviewer-owned set has a separate protocol and empirical scope. [Evaluation protocol](qualification/language_ii/PROTOCOL.md) · [Reviewer artifacts](qualification/language_ii/reviewer/)

| All published items by question family | Total | Correct | Incorrect | Abstained |
|---|---:|---:|---:|---:|
| ATE | 1,422 | 212 | 0 | 1,210 |
| Adjustment comparison | 1,580 | 1,106 | 0 | 474 |
| Association | 1,422 | 591 | 0 | 831 |
| Marginal | 1,580 | 555 | 7 | 1,018 |
| Other six families | 4,108 | 0 | 0 | 4,108 |
| **Total** | **10,112** | **2,464** | **7** | **7,641** |

Coverage was 24.44% and selective accuracy was 99.72%. The descriptive iid Wilson interval on selective accuracy was 99.42–99.86%. Dependence between templates and examples rules out interpreting this as a population generalization interval. The rules answered 378 items in common, including the same two errors. The 47 items answered only by the baseline all matched. The typed parser requires a resolvable link between the marginal and the two strata and sometimes declines a case the baseline can handle by dominance alone. Of 2,093 additional answers, 2,088 matched. The seven discrepancies with published labels belong to questions 20876, 21002, 22290, 23329, 23996, 25982 and 28626. All remain errors in the report.

The deterministic parser returns a typed question, treatment when present, outcome, query direction, intervention arms, operative assumptions, graph edges, unobserved variables, proposed adjustment sets and typed probability facts. Facts contain event, condition and reported percentage. The interpretation and decision stages are distinct. Unsupported syntax, inconsistent graph or probability facts, missing values, lack of exchangeability, ties and rounding uncertainty have explicit abstention codes. Parsing can fail before a full claim exists. The interpreter never invokes a semantic model. Numerical and graphical consequences depend on the selected reading and declared assumptions.

* For a binary partition, compute the outcome mixture at all corners of the rounded risk and mixing-weight intervals. Each integer percentage permits a half-percentage-point error. Compare the mixture with its binary complement.
* For an association, let `p=P(T), a=P(T,Y), b=P(¬T,Y)`. The target contrast is `a/p − b/(1−p)`. Feasibility imposes `p≥a` and `p≤1−b`. For fixed feasible `p` the minimum uses the smallest feasible `a` and largest feasible `b`, and conversely for the maximum. Both resulting envelopes decrease with `p`; evaluate them at opposite endpoints of the feasible interval. A possible zero denominator requires abstention. A graph-implied marginal independence also constrains the contrast when both event names resolve.
* For intervention effects, compare two conditional risks only when treatment randomization is explicit or empty-set adjustment is valid in the fully declared DAG under the stipulated positivity and consistency assumptions. This fragment does not perform numerical covariate standardization when confounding requires adjustment.
* For a pair of adjustment methods, the formal reading asks which population standardization is valid over the specified DAG model class with positivity. For singleton exposure and outcome, remove first edges of proper directed causal paths, exclude descendants (including themselves) of non-exposure vertices on those paths, and require d-separation in the modified graph. Answer only if exactly one set passes. A descendant off every causal path can be harmless, so ruling out all descendants would give incorrect comparisons. The connection of this reading to the source English is an assumption. This implementation uses the published complete adjustment criterion. [van der Zander, Liśkiewicz and Textor, 2014](https://ceur-ws.org/Vol-1274/)

All 1,039 distinct threshold points are archived. A positive threshold compares its value to the distance between the numerical contrast interval and zero. Structural answers remain enabled. These are exact sign margins in probability units. They measure robustness to rounding under the parsed interpretation.

| Minimum numerical margin | Correct | Incorrect | Abstained |
|---|---:|---:|---:|
| Strict sign | 2,464 | 7 | 7,641 |
| 0.05 | 2,285 | 5 | 7,822 |
| 0.10 | 2,126 | 3 | 7,983 |
| 0.20 | 1,874 | 1 | 8,237 |
| 0.30 | 1,623 | 0 | 8,489 |
| Structural answers alone | 1,106 | 0 | 9,006 |

Development controls enumerate eight three-node DAGs in fixed topological order, every ordered endpoint pair, and each permitted adjustment set (96 comparisons). Direct rational world summation supplies the interventional arms. Applying the standardization formula numerically gives a concrete counterexample for every rejected set on these graphs. This finite test supplements the established criterion. Other controls cover reversed causal directions, incomplete and malformed texts, rounded-probability bounds, hidden confounding, ambiguous and counterfactual questions, unrelated marginal facts, equivalent wording and relevant background modifiers. They were written by the implementation author. [Unit tests](tests/test_typed_language.py) · [Frozen rows](qualification/language_ii/typed.rows.json.gz) · [Full report](qualification/language_ii/report.json) · [Full margin curve](qualification/language_ii/coverage.json.gz)

## Exact computation on structured models

The separate research entry point `exact_mass(scm, evidence, do)` implements standard variable elimination with rational arithmetic on binary Markovian DAGs. After intervening, only ancestors of observed evidence contribute factors. The algorithm validates every original CPT, restricts factors to supplied assignments, repeatedly multiplies the factors containing a selected variable and sums over its two values. The selected variable has the smallest current neighborhood, with lexical tie breaking. A running product over the remaining factors, summed over their free variables, is invariant under each elimination by distributivity. Removing a leaf with no evidence or retained children sums its normalized conditional law to one. The resource cap bounds individual binary scopes and validation arity. Dense graphs can exceed the cap, and ordering overhead and exact rational bit lengths can grow. The bound gives no total runtime or memory guarantee.

Direct world summation matched **288/288** model/evidence/intervention combinations on 24 generated DAGs (2–7 nodes, four densities). Inputs include empty and conflicting assignments, deterministic cells, disconnected DAGs and multiple interventions. On archived structured protocol B tasks, elimination rebuilt both exact arm values of **all 1,422 certificates**. The existing independent whole-world verifier accepted each reconstructed receipt. The issuer projects generator-supplied models and queries for this structured comparison. This tests inference conditional on those inputs.

A separate scalar recurrence over disjoint subtrees matched all 12 scaling cases, 7–255 nodes, for binary trees and chains. The largest restricted factor or elimination bucket covered at most three variables in the trees and two in the chains. The 255-node tree scanned 1,642 bucket assignments and took 74.726 ms. At 15 tree nodes, the existing frontier took 8.204 ms and elimination took 1.795 ms. On the 255-node chain, the existing implementation was faster (16.461 ms versus 68.953 ms). Each number is the median of three runs on one x86-64 host with Python 3.12.14. Whole-world timing is restricted to seven nodes and the tree frontier comparison to 15 nodes. The tree recurrence is valid because its parent subtrees have disjoint exogenous noise. Comparison on general DAGs uses full world sums. The new implementation has executable differential evidence. A Lean refinement of this Python algorithm remains open. [Variable elimination](kernel/elimination.py) · [Scaling data](qualification/elimination-results.json) · [Zhang and Poole, 1994](https://www.cs.ubc.ca/~poole/papers/ZhangPoole_cai94.pdf)

## Replay

From the checkout root with the Phase I pinned CLadder archive, SHA-256 `9fdae052b1ebe4ee6a19fdfb3e1eb88a381c7345df394cea524bcce97e2349b3`, run the following. The text replay projects public inputs, starts an offline predictor, freezes predictions before scoring and compares the complete rows, report and coverage curve with archived bytes. The benchmark checks all exact masses and operator counts and reports fresh host timings.

```bash
P=research.proof_carrying_causal_reasoning_v1
python -m "$P.qualification.language_ii.replay" /path/to/cladder-v1.zip
python -m "$P.qualification.replay_eliminated_ate" /path/to/cladder-v1.zip
python -m "$P.qualification.benchmark_elimination"
python -m unittest "$P.tests.test_elimination" "$P.tests.test_typed_language"
```
