# Pointwise dominance: mathematical result, executable replay and limitations

Base: PR #131 head `e1178468f5779557e1fff0982cb65d012e2c1be8`.
Implementation branch: `codex/pgsi-pointwise-dominance-v1`.
This work is an unmerged research extension. Production authority and all seven
original `ProofGated*.lean` source files are unchanged.

## The result

The previous offline guard preserved previously correct integer predictions and
bounded-window maximum error, yet admitted a supported infinite worsening-tail
family. The new checker establishes the stronger relation

`forall integer x, |candidate(x)-target(x)| <= |incumbent(x)-target(x)|`.

For supported exact integer ReLU sums, its positive certificates imply universal
correctness preservation, preservation of arbitrary-domain error bounds and
nonincreasing finite aggregate error. The relation composes transitively across
multiple accepted updates. Its separate PGSI1 composition additionally proves
the original finite benchmark's strict improvement and correctness obligations.
This composition has no old-incumbent nonvacuity conjunct; that existing policy
requirement remains available unchanged in the earlier guard and must be
retained explicitly when required. No runtime policy has been replaced.

The producer is untrusted. Activation thresholds and zeros of both error
functions partition all integers into cells. On each cell, the checker derives
each model's affine form, verifies the error signs, and checks that the incumbent
absolute-error affine form minus the candidate's is nonnegative everywhere.
An ordered adjacency check includes both infinite tails. A negative certificate
is a concrete integer with strictly worse candidate error. Every accepted claim
is reduced in the Lean kernel using `decide`, without `native_decide`, new axioms,
`sorry`, assumed verifier responses or imported generation traces.

## Exact new theorem inventory

`PCS.Research.Pointwise`, in `Pointwise.lean`:

| Theorem | Guarantee |
| --- | --- |
| `absForm_sound` | The checked affine form equals the original form's absolute value throughout its cell. |
| `dominanceRow_sound` | A valid row implies nonincreasing absolute prediction error throughout that cell. |
| `accept_sound` | A complete valid certificate implies pointwise error dominance over every integer. |
| `preserves_correct` | Dominance preserves every previously correct integer prediction. |
| `preserves_bound` | Dominance preserves an existing error bound on any specified domain. |
| `sum_error_le` | Dominance prevents aggregate absolute error increase on any finite list, including repetitions. |
| `transitive` | Two dominance steps compose to a dominance guarantee from the initial model. |
| `refutes_sound` | A verified worsening witness refutes universal dominance. |
| `check_sound` | The typed positive/negative claim checker implies its mathematical meaning. |
| `batch_sound` | Every member of a successfully checked claim batch has its declared meaning. |
| `guard_sound` | Finite PGSI1 admissibility and whole-integer dominance hold together. |

The post-hoc file `experiments/BlockFamily.lean` adds, under
`PCS.Research.PointwiseFamilyBlock`:

| Theorem | Guarantee |
| --- | --- |
| `no_positive_certificate` | For every k >= 18, no certificate can make the earlier worsening-tail family pass pointwise dominance. |
| `no_guard_authorization` | For every k >= 18, no certificate can make that family pass the new finite-gate composition. |

These last two reuse the exact retained family proof from PR #131. They quantify
over mathematical integer neurons; only k in [18,31] is asserted to fit the
existing bounded artifact codec. These 13 declarations' audited axiom closures
are contained in `{propext, Quot.sound}`.

`experiments/PreservedGuard.lean` adds three declarations under
`PCS.Research.PreservedPointwiseGuard`: `accepts_sound` preserves every guarantee
of the previous `GuardMeaning` while adding pointwise dominance; `first_update`
and `second_update` are concrete successful controls for the same two-generation
improvement as PR #131. Thus the combined predicate retains incumbent
nonvacuity, universal correctness preservation, the original finite obligations
and the prior bounded-window guarantee. There are **16 authored new theorem
declarations: 14 general results and two concrete controls**. The composition's
closure additionally inherits the previously approved `Classical.choice` from
the prior guard; no axiom declaration or trust assumption was added.

## Reproduced experiments

The final local suites passed **119 parent + 29 parent-kernel + 25 new = 173
distinct tests**, with zero failures and zero skips. The six existing Lean
modules built successfully; all 31 frozen-theorem and 37 parent-kernel theorem
audits passed. The new 11 core and five post-hoc declarations also passed their
exact-name axiom audits. Historical 19-file and 35-file evidence profiles remain
unchanged; the new main campaign binds 41 critical source files.

The prespecified runner completed **17,992 kernel-checked claims in 146 retained
proof modules**. The full 128-model lattice contributes all 16,384 ordered
pointwise decisions: **2,953 positive and 13,431 refuted**. The finite gate accepts
4,081 transitions, of which **2,203 satisfy pointwise dominance and 1,878 do not**.
The counts concern this finite synthetic lattice, not a population estimate.
Additional claims cover all 729 ordered two-unit configurations (permutation and
zero-error-target controls), 128 seeded multiunit cases, every one of the 14
supported tail cases, the wider-network tail counterexample, two useful
improvement steps and widths 4,8,16,32,63. All known worsening-tail controls were
rejected. The generic family blockade is separately proved, not extrapolated
from those 14 cases.

The main campaign's semantic digest is
`38f17acde6925ef519ca66bd8dd2835949a9b243fe6231ce3cc015ef3e378329`.
Its complete proof source archive, per-module axiom logs, transition matrix,
protocol, scaling measurements and inventory are retained in `results/v1`.
These self-hashes support consistency and replay, not authenticated history.

An independent post-hoc oracle uses exact rational activation thresholds and
quadratic squared-error minima, without the producer's absolute-value partition
or optimized activation sweep. It found **zero disagreements** over all 16,384
lattice pairs and 1,024 additional seeded multiunit comparisons, including
30-digit parameters. Its quadratic-minimum helper also matched direct exhaustive
enumeration on 22,638 bounded problems. This Python oracle is testing evidence,
not a newly proved authority. The 1,024 extra cases are not included in the
17,992 kernel-claim count.

The exact local-proposal graph exposes a negative result. A local proposal
changes one parameter by one or toggles activation:

| Policy | Accepted local edges | Nontarget local dead ends | Starts reaching target (includes target) |
| --- | ---: | ---: | ---: |
| Finite gate | 110 | 49 | 20 |
| Finite gate + pointwise dominance | 77 | 63 | 17 |

Every recorded dead end admits a direct jump to the known target. This control
uses an explicit oracle target and demonstrates a coordinated-change barrier;
it is not evidence of learned discovery. The graph is an exact Python experiment,
not a kernel theorem about search. These policies omit initial nonvacuity; they
must not be confused with the preserved prior-guard composition.

Of the 2,203 finite-and-pointwise transitions, 673 have a previously correct
integer witness and 1,530 do not. Thus the preserved nonvacuous policy retains
673 of the earlier 741 acceptances, rejecting 68 further transitions. Its separate
post-hoc campaign checks all 673 complete prior-guard-plus-dominance compositions
in the real kernel, using the old witness classification and exact window
certificates. This is a distinct stronger property on a subset of the same model
pairs, not 673 new model pairs. Evidence is retained in `results/preserved-v1`.

Local width-control replay took approximately 1.14,1.22,1.61,1.96,3.05 seconds for
widths 4,8,16,32,63 respectively. These controls have only 6–12 distinct refined
cells, so they demonstrate increasing term count, not worst-case partition
scaling. Producer and kernel times are recorded separately; timing is descriptive
for this host and is not included in deterministic semantic comparisons.

The additional GitHub Actions research job rebuilds proofs, reruns the full new
campaign and both independent post-hoc experiments, and compares frozen semantic
results. Parent finite/native and affine-kernel jobs remain enabled. Final run
links and exact tested head/merge commits are recorded in the stacked PR.

## Trust assessment

Lean proves the encoded mathematical claims. Receiver-owned models, strict
canonical JSON, bounded numeric template generation, original-request hashing,
source checks and compiled-checker pins are tested host mechanisms. They are not
proofs of Python/native/OS correctness or an immutable root. A compromised owner
can replace the kernel/toolchain, host or unsigned evidence. Artifact decoding
and actual native PGSI1 authorization remain the unchanged parent implementation.

The new receiver cannot promote a model, reopen an inference artifact or alter
protected state. Its receipt says `HOLDS` or `REFUTED`; both can be successful
kernel replays, but only the former proves dominance. A receiver must inspect the
claim and its original-request binding. Historical mathematical and host evidence
is preserved without modification. No Aristotle formal development was imported
or edited, and future codec migration still requires independent differential
validation.

## Scientific scope and next milestone

These are synthetic exact-integer experiments against an explicit known target,
not independent scientific task improvement or evidence of accelerating recursive
self-improvement. Universal dominance prevents deterioration against that target;
it says nothing about an incorrect target, a different domain, real-valued inputs,
floating-point execution, deep architectures, learned search, or deployment.
The checker is proved sound; formal completeness of the Python producer is not
claimed. Bounded-size receiving may reject otherwise valid mathematical models
whose derived certificate integers exceed the resource budget.

The next meaningful integration is a separately versioned experimental promotion
policy using the proved preserved-guard composition and binding these proofs
to exact canonical bytes, protected generation state and sealed inference.
That requires independent process ownership and storage/rollback assumptions to
be made concrete; ordinary Python privacy, hashes or containers do not supply
them. A further mathematical milestone is a compositional checker for scalar
multilayer networks. Neither milestone should weaken the original source gates
or be deployed as production self-modification in this research stack.
