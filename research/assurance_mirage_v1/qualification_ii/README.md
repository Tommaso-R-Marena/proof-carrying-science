# Authorization with missing evidence and selection on a fixed panel

Three synthetic ledgers admit multiple actions and settle a proposal after a delayed event. On the 816 frozen records, the monitor decided 656 cases at submission and another 160 at settlement. Every decision matched the separate operational adjudicator. At settlement, a simple policy check also decided every case correctly. A second experiment found that repeated selection among weaker instruments increased measured panel accuracy while decreasing expected future accuracy. Both experiments run offline.

## Frozen evaluation

The commitment to the protocol, packet generator, adjudicator, packet bytes and answer-key bytes was sent to the coordinator before scoring. SHA-256 of `frozen/freeze.sha256` is `c43aff32e100b831790703cd8a0a91a9d347abc79dc5be0a13d1dfb6eb8607b7`. The design and domain bounds are in [PROTOCOL.md](PROTOCOL.md).

The held-out nested schema combines two signature rules and an embargo, expiring resource allowances, or a delegated seat change. This changes the original single-mandated-route task. The development representation uses flat fields and lower-case names. All methods use one decoder and see the same fields within each condition. A packet identifier and its answer never enter a monitor. Each complete ledger state and proposal appears under two note renderings and four independent erasure schedules. The 816 records therefore represent **102 distinct semantic cases**. The allocations are 192 exhibit, 432 allocation and 192 recital records. Across them the adjudicator denies 240 proposals and permits 576.

| Telemetry available | Permitted decisions | Denied decisions | Abstain on permitted / denied | Fewest errors if every case must be decided |
| --- | ---: | ---: | ---: | ---: |
| Execution | 0 | 0 | 576 / 240 | 224 |
| Execution and proposal | 448 | 64 | 128 / 176 | 96 |
| Submission registers added | 496 | 160 | 80 / 80 | 80 |
| Settlement event added | 576 | 240 | 0 / 0 | 0 |
| Any one of proposal, A, B or E erased at settlement | 442 | 132 | 134 / 108 | 94 |

Each issued decision is correct. Counting labels among identical inputs gives an independent zero-error coverage ceiling, attained in each row. The forced-error floor sums the minority label counts across those same groups. At submission, for example, the same observable state can support a legal and an illegal final allocation because provisional tokens may expire. In the recital ledger the submission registers add zero decisive cases beyond the proposal and canonical execution. The larger gains in the allocation and exhibit ledgers account for the pooled improvement.

The disagreement baseline flagged every denied proposal when proposals were visible and falsely flagged 304 of 576 permitted proposals. At settlement it scored 240 TP, 272 TN, 304 FP and 0 FN. With one field erased it scored 180 TP, 204 TN, 228 FP and 0 FN and abstained on 204. The keyword baseline scored 120 TP, 288 TN, 288 FP and 120 FN for each view. The baseline requiring every register matched the completion monitor at settlement and abstained on all other views. Simpler policy evaluation suffices on complete records. The completion calculation contributes evidence on partial records. Family counts, abstentions and the two hindsight limits are in [results.json](results.json).

The public policy checker enumerates at most 54 completions per call. Two completions with opposite decisions justify abstention. A separately implemented settlement adjudicator issues permissions, spends vested tokens, or updates the final seating chart. Tests compare every returned witness to an actual complete adjudicated episode, check all observation refinements and exercise changed records, answer keys and malformed typed fields. Validity checks on out-of-domain actions, register values and erasures were added after initial scoring and preserved the published output byte for byte.

**Evidence boundary.** This is an exhaustive census of an authored finite model. The policy, dispatch model and domain bounds must describe all reachable episodes. These assumptions enable the coverage result. New policies, silently corrupted fields, malicious loggers and human authorization judgments would require separate evidence. The independent implementations share authorship and a specification. The wire-format change tests the declared adapter. There is no measurement of natural language, learned cross-schema transfer, live agent behavior or operational incident rates. This public set can now be inspected.

## Selection with protected future cases

Each noisy instrument reports the correct binary target independently with probability 3/4 for the incumbent and either 11/16 or 3/4 for all challengers in its arm. The same 32 qualification readings are available to each method. With split confirmation the winner of the first 16 must strictly outperform the incumbent on a separate 16. The winner cannot be changed after viewing confirmation. Every method and prefix selects before future-case generation. Each arm uses 256 independent pseudorandom replicates with 256 final cases apiece. Full paired counts for challenger prefixes 1, 4, 16 and 64 are in the JSON.

| Challenger quality, method at 64 | Promotions / 256 | Qualification gain (pp) | Final gain (pp) | Monte Carlo SE of final gain (pp) | Population gain (pp, analytic) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Weaker, reused panel | 234 | +12.744 | −5.142 | 0.254 | −5.583 |
| Weaker, split confirmation | 73 | +4.639 | −1.898 | 0.231 | −1.568 |
| Equal, reused panel | 248 | +15.723 | +0.575 | 0.248 | 0.000 |
| Equal, split confirmation | 111 | +7.898 | +0.067 | 0.164 | 0.000 |

On the weaker arm, the incumbent answered 49,095/65,536 final cases correctly. Reused-panel champions answered 45,725 and split-confirmed champions answered 47,851. Approximate pointwise 95% Monte Carlo intervals for their paired gains are [−5.64, −4.65] and [−2.35, −1.45] percentage points (replicate mean ±1.96 standard errors). These intervals describe repeated simulation. In the equal arm, the reused-panel point estimate is 2.32 standard errors above its known zero expectation. The exact expectation governs the model even where a single finite run fluctuates.

### Exact population calculation

Let the incumbent correct count on an independent panel of size $n$ be $B$ with mass $f_0$. Each of $k$ independent challengers has binomial count CDF $F_1$. Write $R(n,k)$ for the probability of strict promotion. Conditioning on $B=b$ gives

```text
R(n,k) = sum_b f0(b) * (1 - F1(b)^k)
G(n,k) = sum_b f0(b) * sum_{t=b}^{n-1} (1 - F1(t)^k)
```

Here $G$ is the expected positive count gain against the incumbent. For the reused panel, population accuracy changes by $(p_1-p_0)R(32,k)$. Selection increases the chance of choosing a weaker challenger as $k$ increases. In the equal-quality control the panel gain grows and the population change is exactly zero. For split confirmation the promotion probability is $R(16,k)R(16,1)$. Conditional on any nominated index, the chance of passing the independent confirmation is $R(16,1)$. Its expected full-panel count gain is $G(16,k)R(16,1)+R(16,k)G(16,1)$. The implementation computes the sums with rational arithmetic, rounding only reported values. A test enumerates the full weighted bit space for a small instance.

Panel selection bias is established in model selection. This experiment provides a controlled qualification example with explicit independent-test and same-budget confirmation arms. [Cawley and Talbot, *On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation*](https://jmlr.org/papers/v11/cawley10a.html)

**Evidence boundary.** The candidate probabilities and conditional independence are stipulated. There are no better challengers in either arm, so the study cannot quantify the opportunity cost of rejecting genuinely improved candidates. These experiments measure selection among fixed noisy instruments. Adaptive candidate generation, correlations from shared training and repeated use of the confirmation panel for redesign would change the assumptions. The split procedure still selects inferior instruments.

## Replay

From the checkout root, using Python 3.12.14 or a compatible interpreter, run

```sh
python research/assurance_mirage_v1/qualification_ii/replay.py
python -m unittest discover -s research/assurance_mirage_v1/qualification_ii -v
```

The first command regenerates both studies and requires an exact byte match to the recorded JSON and frozen evidence. The second checks the authorization examples and completeness witnesses, telemetry refinement, erasures, input validation, promotion rules and analytic calculations. No model calls or additional packages are needed.
