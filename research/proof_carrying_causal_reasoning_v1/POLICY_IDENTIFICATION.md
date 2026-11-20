# Identifying finite policy response from observational data

The receiver answers how many members of a specified finite population would succeed if everyone followed a deterministic treatment policy. One observational table can yield different conclusions under different causal assumptions. The caller fixes those assumptions and the policy in a study file. A separate proposal supplies numerical claims or full candidate causal models.

## Model and results

An equal-weight population of size `N > 0` has arbitrary finite pretreatment strata `Z`, categorical actions `X`, and a binary outcome event. A latent unit contains its stratum, its natural action and a potential outcome for every action. The factual outcome is `Y(X)`. The policy assigns `p(Z)`, preserving the stratum and the latent unit. Assignment and responses may share latent causes. The observation is the multiset of factual triples, including multiplicities. A certificate may present subjects in a different order. Dividing a verified count by the independently supplied population size gives the corresponding policy response probability.

Write `L` for the observed number of successful policy followers and `F` for the number of units whose natural action differs from the policy. For each stratum `z`, let `N_z` be its size, `T_z` its follower count, and `S_z` its number of successful followers.

| Result | Exact hypotheses and conclusion | Implementation |
|---|---|---|
| Structural interpretation | For each latent unit, natural evaluation yields its factual triple. Surgically assigning its policy action yields its potential response at that action. | `factual_evaluation`, `policy_evaluation` in [PolicyIdentification.lean](lean/PcsPccr/PolicyIdentification.lean) |
| Sharp identified set | Under unrestricted assignment–response dependence, a compatible model with success count `k` exists exactly when `L ≤ k ≤ L+F`. The constructive direction produces a complete response vector for every unit, for every integer inside the interval. All compatible models agree exactly when `F=0`. | `sharp`, `identified_iff` in [PolicyIdentification.lean](lean/PcsPccr/PolicyIdentification.lean) |
| Two-model countercertificate | A pair passes when its models reproduce the entire external factual multiset and their actual policy success counts equal two distinct claims. Acceptance rules out any common target value across that observation class. | `checkPair`, `pair_sound` in [PolicyIdentification.lean](lean/PcsPccr/PolicyIdentification.lean) |
| Stratified adjustment | In every occupied stratum the policy receives positive probability. Within each stratum the binary response `Y(p(Z))` is independent of the indicator `X=p(Z)`. Under these hypotheses every compatible model has exactly `Σ_z N_z S_z / T_z` successes, summing only occupied strata and dividing within each term. The binary cross-product identity makes every term an integer on an admissible equal-weight population. The receiver also checks a full model witnessing that such a population exists. | `Balanced`, `Positive`, `adjustment_at`, `policy_adjustment`, `adjusted_sound` in [PolicyAdjustment.lean](lean/PcsPccr/PolicyAdjustment.lean) |
| Wire consequence | For any two Lean strings, if `check source proposal = some reply`, there exist a successfully decoded study and a claim whose rendered value equals the reply and whose mathematical `Meaning` holds for that study. `Meaning` binds the assumption mode and claim-specific consequences. | `receive`, `check_sound` in [PolicyReceiver.lean](lean/PcsPccr/PolicyReceiver.lean) |

The model class allows arbitrary mixtures of the response vectors. The exchangeability requirement is policy-specific, so evidence about one policy does not license conclusions about a different policy. The receiver uses the binary outcome's conditional independence directly. Inferring such independence by inspecting an arbitrary causal DAG is outside the implemented procedure.

### Two reproducible counterexamples

**Positivity alone.** Take one stratum, policy action 1, and two units with natural assignments 0 and 1. Both factual outcomes are zero. One compatible population has two all-zero response vectors. In a second, the naturally untreated unit would succeed at action 1. Both populations have positive policy support, with respective intervention probabilities 0 and 1/2. The second population violates conditional exchangeability. A pair receipt certifies disagreement under unrestricted latent dependence.

**Integer-grid feasibility.** Suppose one of two followers in a stratum succeeds, with a third unit assigned a different action. Exchangeability would require 3/2 successful units in the stratum. The size-three population admits no such model. The exchangeable receiver requires a full compatible witness and rejects this proposal. Treating empirical sample counts as exact population laws, or changing the population grid by replication, changes the statistical question.

## Evidence

The independent Python program enumerates multisets of complete latent unit types, projects each one to observed triples and evaluates its policies. It independently tests exchangeability by comparing exact rational response rates in followers and nonfollowers. The Lean checker uses cross-products. The protocol was fixed before the first full differential run. [Protocol](POLICY_REPLAY_PROTOCOL.md) · [Replay implementation](scripts/replay_policy_identification.py) · [Recorded output](qualification/policy_identification/replay.json)

| Item | Result |
|---|---:|
| Full populations across the two grids | 2,192 |
| Observational multisets | 254 |
| Observation and policy contexts | 1,466 |
| Positive, feasible exchangeable contexts | 582 |
| Positive contexts infeasible on the fixed population grid | 16 |
| Contexts with an unsupported occupied stratum | 868 |
| Interval decisions | 26,796 |
| Ordered model-pair decisions | 8,658 |
| Feasible adjusted point claims and altered-value controls | 582 each |
| Inadmissible adjustment witnesses | 2,772 |
| Directed controls and examples | 35 |
| Paired decisions agreeing with the reference | **39,425 / 39,425** |

The grids use two strata. The binary-action grid exhausts sizes 1 through 3 and the three-action grid exhausts sizes 1 and 2. Every deterministic policy is covered. A directed eight-unit example illustrates genuine adjustment with a pooled follower success fraction of 3/5 and a policy response fraction of 4/8. Two further decisions exercised the ordinary single-study CLI, and both length mismatches were rejected in paired replay. These authored tests establish implementation agreement on the stated grids.

## Replay and wire format

From this research directory with Lean 4.28.0 on PATH, run the following commands.

```sh
(cd lean && lake build && lake env lean PolicyAxioms.lean)
python3 scripts/replay_policy_identification.py
study=$(mktemp)
printf '%s\n' 'U|2|1|0,0,0;0,1,0' > "$study"
printf '%s\n' 'B|0|1' 'W|0|1|0,0,0;0,1,0|0,0,2;0,1,0' |
  (cd lean && lake env lean --run CheckPolicy.lean "$study")
rm "$study"
```

The example returns `PARTIALLY_IDENTIFIED 0 1` and `NOT_IDENTIFIED 0 1`. The former supplies an exact interval. The latter supplies two witnessed, distinct counts disproving point identification. Both use `N=2`. An accepted singleton interval or accepted exchangeable point claim returns `IDENTIFIED k`. Rejection indicates the submitted claim failed verification. It carries no identification verdict.

The study line is `U|action-count|policy|factual-rows` for unrestricted latent dependence or `E|action-count|policy|factual-rows` to require conditional exchangeability and positivity for adjustment. Policy is a comma-separated list of action indices in stratum order. Factual rows use `z,x,y` and are separated by semicolons. Proposal formats are `B|lo|hi`, `W|first-count|second-count|first-model|second-model`, and `A|count|model`. A full model uses the same row format with a natural-number bit mask in the third field, with bit `x` encoding the outcome under action `x`. The wire supports 1–16 actions, 1–32 strata, and 1–128 units, with canonical unsigned decimal fields of at most nine digits and lines of at most 8,192 characters. The mathematical theorems quantify over arbitrary finite cardinalities. The ordinary CLI applies one independently supplied study to every proposal. Batch replay accepts a separate ordered study file and checks input-stream lengths.

The axiom audit reports `propext` for the two structural evaluation equalities. Each of the other eight probes uses only `propext`, `Classical.choice` and `Quot.sound`. The exact Lean statements and declarations to probe are linked above and in the audit file. [Axiom probe](lean/PolicyAxioms.lean)

The mathematical consequence starts at the decoded Lean study, and `check_sound` binds it to the successful decoder result. The external origin, intended encoding, meaning of the policy, population representativeness, validity of the causal assumptions, host I/O, and compiled runtime remain trust boundaries. A compatible submitted model demonstrates feasibility of the assumptions. Establishing that they hold in a real population requires scientific evidence.

## Relation to prior work

The unrestricted interval specializes classical worst-case bounds on potential-outcome means. The positive formula is standardization for a deterministic baseline treatment rule. The contribution is a constructive finite-population formalization, a shared structural model for both assumption classes, and a proof-carrying executable receiver. For established results, see Charles F. Manski, “Nonparametric Bounds on Treatment Effects,” *American Economic Review* 80(2), 319–323 (1990), and Miguel A. Hernán and James M. Robins, *Causal Inference: What If* (2020), chapters 2–3. [Hernán and Robins](https://miguelhernan.org/whatifbook)
