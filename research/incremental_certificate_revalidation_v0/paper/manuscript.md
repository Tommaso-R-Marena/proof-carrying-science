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

`IncrementalAccept` states minimal sufficient premises (prior FreshWitness,
ChangesComplete, idsCovered, Affected recheck on the updated graph, eligible
authoritative reuse) and does **not** embed `FreshValid`. Central theorem
`incremental_implies_fresh` derives fresh validity from those premises.
Supporting families cover dependency correctness, invalidation (including
new-edge / new-graph requirements), safe reuse, policy/version sensitivity,
non-escalation, composition, and mutation safety. No `sorry`/`admit`/custom
axioms; transitive uses of `propext` / `Classical.choice` / `Quot.sound` audited.

## Executable system

Restricted ops (exact Int/Rat, equality, composition). Local ValidState cache.
Independent `fresh_verify` oracle. Differential mutation tests (not a refinement
proof). Assumption-removal counterexamples show incomplete changes, prior-only
invalidation, and forged authority break the guarantee. Nine adversarial
categories resisted under default defense-in-depth.

## Performance

Cheap Int ops: incremental slower than fresh (~0.45–0.53×) — negative result kept.
Expensive synthetic local checks (`DelayedRegistry`): trusted sparse leaf reuse
~64–123× vs full recompute; root-heavy changes ~1× (performance failure when reuse
is empty); defense recheck-on-reuse erases the speedup. Cost axes distinguished:
cache validation, certificate rechecking, full mathematical recomputation.

## Limitations

Python↛Lean refinement unproved; serialization decode is the remaining boundary.
Cross-process trust, rollback epochs, and concurrency are out of scope.
No claim of scientific truth for measurements.

## Conclusion

PCS can state precise conditions for certificate reuse on changing DAGs and prove
that those conditions imply fresh validity. Empirical tools validate the
executable prototype without overclaiming refinement or production authority.
