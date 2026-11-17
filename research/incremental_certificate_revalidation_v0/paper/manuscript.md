# Formally Verified Incremental Certificate Revalidation for Proof-Carrying Science

**Status:** Research draft — not a production release.  
**Namespace:** `research/incremental_certificate_revalidation_v0/`  
**Lean package:** `PCSIncremental` (Lean 4.28.0)

## Abstract

We study when a previously accepted computational certificate on a finite DAG may
be reused after a precisely represented change set without weakening the
guarantees of a full fresh verification. We distinguish cache *lookup*,
*eligibility* (exact obligation equality), and *authority* (prior acceptance
under an explicit trust model). We formalize the model in Lean 4, prove that
incremental acceptance implies fresh validity under stated hypotheses, prove
invalidation soundness/completeness for an inductive Affected relation (least
fixed point), and implement an independent Python verifier with a full-recomputation
oracle and an adversarial cache-poisoning suite.

## Distinction from prior PCS work

Checked-lemma reuse optimizes proof *search*. Scientific intake caches host-local
checker results under an external completeness premise (PR #201). Epistemic and
workflow invalidation reopen claims heuristically. Our contribution is
infrastructure-level soundness for **graph certificate revalidation** with proved
fresh correspondence and explicit non-escalation — see `OVERLAP_AUDIT.md`.

## Formal results

Central theorem `incremental_implies_fresh`: any state satisfying
`IncrementalAccept` is `FreshValid`. Supporting families cover dependency
correctness, invalidation, safe reuse, policy/version sensitivity, non-escalation,
composition, and mutation safety. Axiom audit: only `propext` where used; no
`sorry`/`admit`/custom axioms. `affected_least` shows Affected is the least
predicate closed under dependency from change seeds.

## Executable system

Restricted ops (exact Int/Rat, equality, composition). Local ValidState cache.
Independent `fresh_verify` oracle. Differential mutation tests (30×6 sequences).
Nine adversarial categories all resisted under default defense-in-depth.

## Performance

On cheap synthetic Int ops up to ~20k nodes, incremental wall-clock was slower
than fresh (~0.45–0.53×) because bookkeeping dominates trivial arithmetic.
Reuse *counts* match theory (e.g. 19937/19999 reused on sparse scientific graphs).
Speedups are expected only when local checks are expensive; we do not invent them.

## Limitations

Python↛Lean refinement unproved; serialization decode is the remaining boundary.
Cross-process trust, rollback epochs, and concurrency are out of scope.
No claim of scientific truth for measurements.

## Conclusion

PCS can state precise conditions for certificate reuse on changing DAGs and prove
that those conditions imply fresh validity. Empirical tools validate the
executable prototype without overclaiming refinement or production authority.
