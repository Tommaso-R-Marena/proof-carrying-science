# PRISM: Proof-Carrying Certificates for Sharp Bounds, Impossibility, and Minimax-Optimal Adaptive Experiments over Finite Mechanistic Model Classes

*Research manuscript, draft. All mathematical claims below are machine-checked in
Lean 4 unless marked otherwise. Literature positioning was done without internet
access and is unverified for 2025–2026 work (see §3 and `NOVELTY_AUDIT.md`).*

## Abstract

We study a finite, deterministic formalization of a recurring scientific
situation: several mechanistic models fit the available observations but disagree
on a quantity of interest, and a set of costly experiments is available. For this
setting we give, and verify in Lean 4 with Mathlib, a complete certificate
architecture with seven verdicts: CERTIFIED, BOUNDED, FALSIFIED, UNIDENTIFIABLE,
EXPERIMENT, IMPOSSIBLE and INCONSISTENT.

Our strongest results are the following.

* **Bellman characterization.** The worst-case-optimal total cost of an adaptive
  experimental strategy that reduces the query's uncertainty to at most ε is the
  value of an explicit Bellman recurrence. This holds over the class of *all*
  finite adaptive decision trees, including wasteful ones.
* **Exact, complete certificate classes.** We give certificate classes for each
  conclusion:
  * policies, for upper bounds;
  * local "adversary" tables, for lower bounds, which we prove complete via the
    truncated value function;
  * pairs of observationally equivalent models with query gap greater than ε, for
    impossibility, which we prove complete via an exact identifiability
    characterization through observational-equivalence classes.
* **Kernel-checked checker.** All of these are checked by a Boolean checker whose
  soundness is proved and which the Lean kernel evaluates on concrete certificates.
* **Optimality sandwich.** A certificate checked on an outer approximation proves
  exact optimality for every version space between a small core and that outer
  approximation.
* **Nuisance-factor elimination.** If every experiment depends either only on the
  query-relevant factor or only on a nuisance factor, the exact optimum on a
  product version space equals the optimum on one nuisance section. A
  counterexample shows the splitting hypothesis is necessary.

A counterexample-guided refinement loop builds such certificates. On a
parameterized family designed to have a small "hard core", it certifies instances
with 131 072 models in seconds, where memoized dynamic programming times out. On
unstructured random instances and on an OR-type negative control it gives no
advantage. A small core does not imply a small explicit certificate: OR requires
2^n − 1 table entries over its (n+1)-model core.

We also formalize an anytime-valid noisy extension: a mixture-likelihood-ratio rule
whose false-certification probability is at most α under arbitrary adaptive
experiment selection and optional stopping, together with a formal counterexample
showing that the post-hoc maximum-likelihood variant is invalid.

The mathematics is classical or elementary. The contribution is an end-to-end,
auditable, machine-checked integration and an honest empirical characterization
of when core-guided certification helps.

## 1. Motivation

A model that fits the data is not thereby correct, and a posterior is not a proof.
Scientists need to know:

* what *follows* from evidence plus assumptions;
* what *range* of answers remains;
* which experiment best reduces that range;
* when no permitted experiment can settle the question.

They also need these answers to be checkable by someone who does not trust the
software that produced them. We take the most rigid version of this problem that
can be solved exactly: finitely many candidate mechanisms, deterministic
observations, exact rational quantities. We aim for complete, independently
verifiable answers there before addressing noise (§10).

## 2. Contributions

1. A Lean 4 development, about 2 350 lines with no `sorry` or custom axioms,
   covering:
   * version-space soundness, sharp bounds, and inconsistency certificates (§4);
   * the Bellman recurrence and global minimax optimality over all adaptive
     policies (§5);
   * impossibility, an exact identifiability criterion, and complete two-model
     certificates (§6);
   * complete adversary lower-bound certificates (§7);
   * the optimality sandwich, exact abstractions and nuisance-factor elimination
     (§8);
   * executable checkers with soundness proofs (§9);
   * an anytime-valid noisy layer (§10);
   * parametric families: OR evasiveness for all n, a Θ(n) adaptivity gap, and
     greedy suboptimality (§11).
2. An independent checker architecture. Untrusted Python search produces
   certificates, which are checked by a Python mirror and, authoritatively, by the
   Lean kernel through generated modules (`decide +kernel`, with no compiled-code
   trust).
3. A core-guided certification algorithm and an empirical study, including
   negative controls and failure analysis (§12–13).
4. Three demonstrations: biochemical, causal, and scalable (§12).

## 3. Related work (from memory; unverified for recent work)

* **Partial identification.** Manski's bounds and the Balke–Pearl LP bounds are
  the continuous and LP analogues of our sharp finite bounds. Our causal demo
  reproduces the natural (Manski) ATE bounds on a finite grid.
* **Observational equivalence and identifiability** (Koopmans, Rothenberg; Pearl).
  Our `identifiable_iff` is the finite, ε-tolerant form of "the query factors
  through the observation map".
* **Optimal decision trees and adaptive diagnosis.** Hyafil and Rivest showed
  NP-hardness. Minimax dynamic programming and AND/OR search are standard, and
  decision-tree complexity and the adversary method (evasiveness of OR) are the
  sources of our lower-bound certificates.
* **Optimal experiment design for causal identification.** The mandated
  references (Akbari et al. 2025; Maringgele and Etesami 2026; Choe et al. 2026;
  Zhang et al. 2023) address graph-structured intervention selection, partial
  identification and canonical domain reduction. **We could not read them.** We
  expect substantial conceptual overlap with our identifiability and abstraction
  components, and difference mainly in our use of explicit finite model classes,
  adaptive policies and machine-checked certificates.
* **Certificate checking.** Examples are DRAT/LRAT for SAT and LP certificates
  checked in proof assistants (the Lean `lp` project). We apply the same pattern to
  a new certificate type.
* **CEGAR/CEGIS** (Clarke et al.) and row and scenario generation. Our refinement
  loop is an instance.
* **Anytime-valid inference.** Relevant work includes Ville's inequality,
  universal inference (Wasserman, Ramdas and Balakrishnan) and e-processes. Our
  noisy layer formalizes the mixture-likelihood-ratio argument on finite adaptive
  trees.
* **CausalSmith/CausalForge** (Tan and Syrgkanis 2026) and StatLean were not read
  or used.

## 4. Formal setting and inference core

A problem `P : Problem M E O` has `obs : M → E → O`, `q : M → ℚ` and
`cost : E → ℚ≥0`. Given candidates `M₀`, assumptions `A` and data `D`, the version
space is `K = {m ∈ M₀ | A m ∧ ∀ (e,o) ∈ D, obs m e = o}` (`mem_versionSpace`).
For nonempty `K`, `L = min q`, `U = max q` and `W = U − L`.

* **Soundness and sharpness** (`bounds_sound`, `bounds_sharp`, `bounds_optimal`).
  Every admissible query value lies in `[L,U]`, both endpoints are attained, and
  no smaller interval is valid.
* **Claims** (`classify_sound`). CERTIFIED requires `K ≠ ∅`. FALSIFIED returns a
  countermodel in `K`. An empty `K` yields INCONSISTENT, with a complete
  certificate (`inconsistencyCert_sound/complete`). `empty_certifies_everything`
  records why vacuous certification must be blocked.
* **Model-class relativity** (`certified_transfers_to_truth`,
  `certified_does_not_imply_truth`).

## 5. Adaptive policies and Bellman optimality

A policy is a finite tree `stop | test e (O → Policy)`. `Succeeds ε p K` says that
for every true `m ∈ K` the version space at which `p` stops has width at most ε.
The value is

```
value ε K = 0                                                    if W(K) ≤ ε
          = min_{e informative on K} [cost e + max_{o feasible} value ε K(e,o)]   otherwise
```

with `min ∅ = ⊤`, defined by well-founded recursion on `|K|`.

**Theorem 1** (`value_le_iff`, `value_optimal`, `value_eq_top_iff`). For `ε ≥ 0`:

* `value ε K ≤ v` if and only if some policy succeeds on `K` with all path costs
  at most `v`;
* if `value ε K = v < ⊤`, an only-informative policy attains worst-case cost
  exactly `v`, and every successful policy has worst-case cost at least `v`;
* `value = ⊤` if and only if no policy succeeds.

*Proof idea.* For the lower bound (`value_le_of_succeeds`), induct on the policy.
At a `test e` node, either `e` is uninformative on `K`, in which case the child
on the unique feasible outcome is a successful policy for the same `K` with
smaller budget, or it is informative, in which case the recurrence applies with
the children's bounds. For attainment (`exists_policy_of_value_le`), use strong
induction on `|K|`, choosing a minimizing informative experiment. Tie-breaking
(`exists_policy_test_of_backup_le`), elimination of uninformative experiments
(`exists_optimal_onlyInformative`) and termination (`pathLength_lt_card`) are
separate lemmas. Zero costs are allowed, and termination never relies on positive
costs. ∎

Greedy is not optimal: `trap_greedy_suboptimal` gives cost ≥ 5 against an optimum
of 4.

## 6. Impossibility and exact identifiability

**Theorem 2** (`impossibility`). If `m₁, m₂ ∈ K` satisfy `obs m₁ = obs m₂` on
every experiment and `q m₁ − q m₂ > ε`, then no adaptive policy succeeds. Proof:
`obsEquiv_mem_terminal` shows that `m₂` survives every path generated by `m₁`. ∎

**Theorem 3** (`identifiable_iff`, `value_ne_top_iff`). For `ε ≥ 0` and finite
`E`, a successful policy exists if and only if every observational-equivalence
class of `K` has query spread at most ε. Hence (`impossibilityCert_complete`)
unattainability *always* has a two-model certificate, checkable in `O(|E|)`
without reference to policies. Sufficiency uses the nonadaptive policy "run every
experiment" (`terminal_testAll`).

Invalid strengthenings include "distinguishable pairs exist ⇒ identifiable" and
"identifiable ⇒ identifiable by one experiment" (`or_value`: n experiments are
needed).

## 7. Lower-bound certificates

`IsAdversary ε lb` requires, for every set `S`, that either `lb S = 0`, or
`W(S) > ε` and every experiment has a feasible outcome `o` with
`lb S ≤ cost e + lb(S(e,o))`.

**Theorem 4** (`adversary_sound`, `adversary_complete`, `le_value_iff_adversary`).
`B ≤ value ε S` if and only if some adversary has `lb S = B`. The truncated value
`min(value, B)` is always an adversary.

This is a finite strong-duality statement: optimal upper bounds (policies) and
optimal lower bounds (adversaries) always meet. The adversary condition is local
and quantifies over all experiments, so the checker needs no reasoning about
informativeness.

## 8. Optimality sandwich and abstraction

**Theorem 5** (`optimality_sandwich`, `value_eq_of_sandwich`). If
`Klo ⊆ K ⊆ Khi`, policy `p` succeeds on `Khi` with cost at most `B`, and
`value Klo ≥ B`, then `p` is exactly optimal on `K` and `value K = B`.

The checkable form (`checkSandwich_sound`) proves optimality for every `K` between
the certificate's core and `Khi`. `K` itself is never needed.

**Theorem 6** (`IsExactAbstraction.value_image`). A map that preserves
observations, query values and costs preserves the value. The signature-and-query
quotient is exact (`value_signatureQuotient`). The signature-only quotient is not
(`signature_only_quotient_unsound`).

**Theorem 6b** (`value_prod_eq_section`, `section_policy_lifts`). Suppose the
model space is `A × Z`, `q` depends only on `a`, and each experiment's outcome
depends only on `a` or only on `z`. Then for every `z₀ ∈ KZ`,
`value ε (KA ×ˢ KZ) = value ε (KA ×ˢ {z₀})`, and every only-informative optimal
policy for the section is optimal for the product.

*Proof idea.* On a section, an informative experiment must be relevant
(`relevant_of_informative`). An only-informative section policy therefore runs
only relevant experiments. Simulated on the product, it produces terminal sets
that are the section's terminal sets times `KZ` (`terminal_liftZ`), with
unchanged widths and costs. Monotonicity gives the reverse inequality. ∎

`nuisance_mixing_counterexample` shows that a single experiment depending on
`a xor z` breaks the conclusion: the query is identifiable on a section and
impossible on the product.

These results are elementary. They are the formal backbone of §12. Theorem 6b
explains the lesion-family results: the certificate size is independent of the
number of nuisance switches.

## 9. Checkers and the trust boundary

`checkPolicy`, `checkAdversary`, `checkOptimal`, `checkSandwich`,
`checkImpossible`, `checkBounds`, `checkCountermodel`, `checkCertified` and
`checkInconsistent` are executable Boolean functions with soundness theorems.
`checkPolicy` is also complete, and `optimal_certificate_exists` guarantees that
accepted certificates exist. Concrete certificates generated from JSON are checked
by `decide +kernel`. The JSON → Lean emitter and parser are trusted and unverified.
They are mitigated by self-describing output and SHA-256 binding
(`TRUST_BOUNDARIES.md`). There is no verified byte-level parser.

## 10. Anytime-valid noisy extension

Each model gives rational outcome distributions per experiment. An adaptive
procedure is a policy tree. With prior `π` and mixture `mix(h) = Σ π(m) P_m(h)`,
the rule rejects `m` at history `h` when `P_m(h) ≤ α · mix(h)`.

**Theorem 7** (`reject_ever_le`, `false_certification_le`). For every adaptive
procedure, `P_m(m is rejected at some time) ≤ α`. A procedure that certifies `C`
only after rejecting every model violating `C` errs with probability at most α
under every model violating `C`.

The proof shows that `mix/P_m` is a nonnegative martingale on the outcome tree
(`mixProb_martingale`, `leafSum_martingale`) and applies a first-passage argument,
which is Ville's inequality in finite form. **Counterexample**
(`posthoc_alternative_invalid`): replacing `mix` by `max_m P_m(h)` gives
rejection probability 1 at α = 1/2.

The deterministic and probabilistic guarantees are kept separate.

## 11. Parameterized families

* `or_value`: exact cost `n` for all `n`, via a closed-form adversary on an
  (n+1)-model core.
* `ptr_adaptive` and `ptr_nonadaptive`: 2 versus at least n+1.
* `trap_*`: greedy is suboptimal.

## 12. Algorithm, demonstrations and complexity

**Core-guided sandwich**:

1. Start from the core `C = {argmin q, argmax q}`.
2. Solve the exact DP on `C`, obtaining value `v`, policy `π` and an adversary
   table.
3. Validate `π` on `K` by pushing `K` down the tree, which costs `O(|K|·depth)`
   bitset operations.
4. If validation passes, emit `(π, v, C, table)`, which `checkOptimal` verifies.
5. Otherwise add the failing extreme or over-budget models to `C` and repeat.

If `value(C) = ⊤`, emit a two-model impossibility certificate. A progress lemma
guarantees that each round adds a model, so there are at most `|K|` rounds. This
lemma is informal, not formalized; soundness does not depend on it. In the worst
case `C = K`, and the cost is that of DP plus overhead. The underlying problem is
NP-hard in general.

**Demo A (synthetic enzyme regulation).** There are 32 candidate mechanisms:
four inhibition modes times three binary switches (feedback, activator and
isoform). A recorded and justified assumption admits 24 of them, and 16 remain
admissible after one observation. The results are:

* query bounds `[1/4, 5/6]` (sharp);
* one claim certified and one falsified, with a countermodel;
* first experiment `product_spike`, with exact optimal worst-case cost 3
  (certificate core of 8 models);
* a simulated discovery that identifies the query (2/3) at total cost 3;
* under a restricted assay set, IMPOSSIBLE, with a two-model certificate.

Everything is kernel-checked (`PRISM/Examples/Generated/Biochem*.lean`).

**Demo B (causal).** The setting is a binary treatment X and a binary outcome Y,
with `X := U_X` and `Y := g_{U_Y}(X)`, where `U_Y` ranges over the four canonical
response types (Balke–Pearl). A model is a joint distribution of `(U_X, U_Y)`
with probabilities in multiples of 1/6, which gives 1716 models and permits
arbitrary confounding. The experiments return exact, idealized infinite-sample
distributions: an observational survey, two RCT arms and a coarse RCT.

After the survey, 36 models remain. Their sharp ATE bounds `[−1/3, 2/3]` coincide
with the analytic natural (Manski) bounds. With only observational experiments
the verdict is IMPOSSIBLE, as expected from non-identifiability. With RCT arms,
the exact optimal costs are 4, 3 and 2 at ε = 0, 1/3 and 1/2.

The formal model encodes potential outcomes per response type, so interventional
predictions are computed from the same latent structure as observational ones.
This is the correspondence the causal interpretation requires, and it is checked
by construction in `examples/causal/build.py` rather than proved in Lean. Only the
36-model version space is exported to Lean.

**Demo C (scalable).** See §13.

## 13. Benchmarks

The full methodology and tables are in `EXPERIMENTS.md`. In summary:

* **Lesion family** (designed to favour the method). The sandwich certifies
  optimality for up to 131 072 models in 8.6 s, plus 4.0 s of independent
  checking. With n = 8, naive DP times out at 10 s from 2 048 models and pruned DP
  from 32 768 models. The certificate size is independent of the number of
  nuisance factors.
* **Random held-out instances.** No advantage: the core reaches about 80% of `K`,
  and the sandwich is 1.3–3.3× slower than pruned DP on average.
* **OR negative control.** No advantage, and explicit certificates have
  exponential size.
* **Greedy** is suboptimal on up to 100% of instances in the larger random class.
* **Verification.** The Python checker takes milliseconds to seconds. The Lean
  kernel takes seconds per small instance.

## 14. Failure cases and negative findings

See `NEGATIVE_RESULTS.md`. Key items:

* greedy is suboptimal;
* the signature-only quotient is unsound;
* post-hoc likelihood-ratio rules are invalid;
* a small core does not give a small explicit certificate;
* there is no sublinear-in-|K| algorithm without symbolic representations, which
  were not implemented;
* the adaptivity gap is at most |E| for unit costs, so it can only be linear;
* a quadratic-validation bug was found and fixed during the work.

## 15. Trust assumptions and limitations

The following are trusted: the Lean kernel and Mathlib; the standard axioms
`propext`, `Classical.choice` and `Quot.sound`; the Python emitter and parser; and
the model class. The following are limitations:

* the observations are deterministic;
* the model sets are finite and explicit;
* the cost criterion is worst-case total cost (no expected cost, no budgets per
  step);
* there are no symbolic model representations;
* the Python checker is tested, not extracted;
* the literature review is unverified.

## 16. Significance (assessed conservatively)

The results show that, for finite deterministic model classes, every one of the
seven verdicts has a *complete* certificate class with a small verified checker.
Positive optimality claims, impossibility and lower bounds can all be checked
without trusting the solver. The empirical study identifies a concrete structural
condition, a small query-relevant core with multiplicative nuisance variation,
under which certified optimal experiment design scales beyond DP. It also
identifies the obstacle to going further: explicit certificates can be
exponential even when cores are small, which calls for symbolic, verified
adversaries.

We do not claim a mathematical breakthrough (`BREAKTHROUGH_ASSESSMENT.md`).

## 17. Reproducibility

Run `python3 scripts/run_all.py` (see `REPRODUCIBILITY.md`). The toolchain is
pinned: Lean 4.28.0 and Mathlib v4.28.0. The Python code is stdlib-only.

## 18. What is missing for publication

* A verified literature review, in particular of the four 2025–2026 references.
* Comparison against MILP/SAT optimal-decision-tree solvers.
* Symbolic model-space representations, together with a symbolic adversary
  checker.
* A formalized progress lemma.
* A verified parser, or extraction of the checker.
* A real (non-synthetic) scientific case study.

## References (well-known sources only; recent items unverified)

* T. Mitchell. Generalization as search. *Artificial Intelligence*, 1982.
* C. F. Manski. Nonparametric bounds on treatment effects. *AER P&P*, 1990.
* A. Balke, J. Pearl. Bounds on treatment effects from studies with imperfect
  compliance. *JASA*, 1997.
* J. Pearl. *Causality*. Cambridge University Press, 2000/2009.
* L. Hyafil, R. Rivest. Constructing optimal binary decision trees is NP-complete.
  *IPL*, 1976.
* E. Clarke, O. Grumberg, S. Jha, Y. Lu, H. Veith. Counterexample-guided
  abstraction refinement. *CAV*, 2000.
* J. Ville. *Étude critique de la notion de collectif*, 1939.
* L. Wasserman, A. Ramdas, S. Balakrishnan. Universal inference. *PNAS*, 2020.
* A. Wald. Sequential tests of statistical hypotheses. *Ann. Math. Stat.*, 1945.
* The request's mandatory references 1–7 (not consulted; see `NOVELTY_AUDIT.md`).
