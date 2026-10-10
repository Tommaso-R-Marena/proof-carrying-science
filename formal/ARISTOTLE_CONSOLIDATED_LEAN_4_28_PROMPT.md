# Single Aristotle request: PCS bounded reasoning, repair and optimal intervention

Produce a complete, compiling Lean **4.28.0** source package for the open obligations
below. Read the attached implementations and existing proofs before changing them.
This prompt supersedes the earlier finite-FOL, adaptive-search and conditional-BDD
requests. Return one integrated package with a theorem inventory and explicit open
obligations. Preserve `leanprover/lean4:v4.28.0`, existing dependency locks, compiled
authorities and import graph. The standalone `formal/` workspace uses `import Std`
and has no Mathlib dependency. Do not add a dependency unless indispensable and
explicitly justified. Use new modules such as `PCSOmega` and `PCSDecisionDiagram`.

No `sorry`, `admit`, custom axioms, unsafe proof code, `native_decide`,
`Lean.ofReduceBool`, external oracles, disabled kernel checks or redefinitions that
turn the requested statements into tautologies. Ordinary kernel-checked `decide`
on finite examples is allowed. Print the actual axiom inventory of every principal
theorem, including standard axioms. Supply source, commands and actual logs when
executed; never claim an unexecuted compilation. Put false-claim controls outside
the production import graph. If a stage remains incomplete, deliver the completed
modules without imported placeholders and name the exact remaining theorem.

## 0. Existing proofs to reuse and boundaries to preserve

`formal/PCSCountermodel/{Core,Enumeration,Named,Fixtures,Missions,Audit}.lean` already
prove finite-FOL evaluation against independently defined propositional satisfaction,
fixed-world checker soundness/completeness, world enumeration/search through domain
sizes 1–3, minimal-domain witnesses, named lowering with shadowing, and a concrete
four-element boundary showing bounded absence of witnesses is not unbounded
equivalence. Audit and retain those proofs; do not repeat the earlier request as
though these results were absent. The actual Python/game named JSON parsing and
lowering boundary is distinct from typed reference proofs.

The existing compiled `PCSAuthority`/`PCSSemanticCheck` and PCS proof umbrella have
their own authority/claim-binding contracts. Keep them intact. Experimental Omega,
conditional and intervention receipts have `pcs_authority:false`; existing browser
receipts also have `lean_kernel_checked:false`. A proved Lean reference model does
not by itself justify changing these flags. Selected repair equalities, 12 selected
conditional equalities and 12 selected intervention minima/counts are example
controls, not general algorithm or implementation-refinement theorems.

## 1. Shared typed Boolean semantics and exhaustive repair checking

Read `pcs/experimental/omega/{logic,search,adaptive}.py` and the matching website
`public/{omega-core,omega-adaptive}.mjs`. Define a typed Boolean AST over `Fin n`
with atom, TRUE/FALSE, NOT, AND, OR, implication (`!a || b`). Independently define
propositional satisfaction and prove evaluator correctness. Prove complete
False-before-True valuation enumeration, including n=0 constants. Prove fresh
exhaustive equality checking is equivalent to agreement on every valuation and
that its first returned disagreement genuinely distinguishes the immutable source.
The actual Omega protocol has 1–4 sorted variables, at most 63 AST nodes and depth
8; do not silently expand the learned model's scope to 24 variables.

Prove remembered-witness filter rejection implies non-equivalence, adding witnesses
cannot restore a rejected candidate, and every genuinely equivalent candidate
survives every valid remembered witness. Survival alone does not imply equivalence.
Define replay states with an immutable source, legal bounded edits, checked parent
states, source-bound remembered counterexamples and acceptance only after a fresh
exhaustive check. Prove accepted typed replay solutions preserve source semantics.
Parameterize ranking by an arbitrary ordering: learned weights affect priority,
not truth. Initial checking, outgoing proposal ranking and examined candidates all
consume actual work. Prove the implemented accounting bounds where possible.
Do not claim bounded-search completeness, fairness, global repair optimality,
learned accuracy, training improvement or scientific grounding.

## 2. Ordered decision diagrams and bounded apply/compilation

Read `pcs/experimental/conditional.py` and `public/conditional-core.mjs`. Define
validated reduced ordered diagrams with false/true roots 0/1, other IDs indexing
append-ordered `[variable,low,high]` nodes. Children precede their parent; variables
strictly increase along edges; reduced nodes have unequal children and a unique
triple. Define evaluation independently from formula evaluation. Prove invariant
preservation, extension preservation of old-root meaning, Shannon decomposition,
and canonicity/constant-root completeness before using root=0 as unsatisfiability.

Implement AND/OR/XOR apply and AST compilation with explicit fuel/budgets and
memoization. Successful apply preserves invariants and denotes the requested
connective; successful compilation preserves AST meaning. Exhaustion is unresolved.
Cache-hit calls count against the documented apply budget. Existing limits are
4,096 nodes and 100,000 apply invocations; formulas individually have at most
128 nodes/depth 12, at most 24 sorted variables and eight assumptions. If exact
Python/JavaScript operational parity is unproved, state that explicitly and label
the executable Lean protocol as a separate reference. Do not replace BDD apply
with 2^24-world enumeration and claim it refines the bounded implementation.

## 3. Conditional outcomes, witnesses and minimal conflicts

Compile premises first, stopping at the first inconsistent prefix. Prove prefix
inconsistency implies full-context inconsistency, without compiling the query.
For equivalent-under-assumptions, require a satisfying context witness and prove
all satisfying assignments give equal original/candidate values. For disagreement,
prove the returned total assignment satisfies every premise and separates meanings.
For inconsistency, prove the reported core inconsistent and each removal witness
satisfies the other *core* premises. Prove inclusion minimality, not minimum
cardinality; removal witnesses need not satisfy premises outside the core.
Resource exhaustion establishes none of these semantic outcome claims.

Prove false-first witness extraction satisfies its root and, with a defined total
assignment ordering, is lexicographically least. Include n=0, unused variables,
inconsistent contexts, conditional entailment and work-limit controls.

## 4. Positive-cost intervention optimization, count and explanations

Read `pcs/experimental/intervention.py`, `intervention_cli.py`,
`public/intervention-core.mjs`, `docs/INTERVENTION_PLANNING.md`, the 27 measured
cases and `scripts/verify_intervention_lean.py`. An intervention task wraps a
conditional problem with `source=target`, `candidate=FALSE`, a Boolean baseline,
integer costs 1–1,000,000 and a sorted subset of locked variables. A feasible total
assignment satisfies all premises and target and keeps every locked variable at
baseline. A baseline is allowed to violate premises. Objective:
`sum i, if assignment i != baseline i then cost i else 0`.

The actual symbolic root is `context AND target`. The appended-node Bellman table
contains null for infeasibility, or `[cost,count,mandatoryMask,possibleMask]`.
Terminal 0 is null; terminal 1 is `[0,1,0,0]`. Inspect each unlocked/permitted
low/high branch. Add variable cost and flip bit when its value differs from
baseline. Choose the smaller cost; at ties sum counts, intersect mandatory masks
and unite possible masks. False wins a tie for reconstruction. Skipped variables
retain baseline. This is essential: **strict positive costs** make their optimal
completion unique. Zero-cost generalization would require different counting and
explanation rules and is outside this protocol.

Prove, for every valid ordered diagram and positive cost vector:

1. The single pass terminates, preserves cell invariants and uses at most one
   cell computation/two branch inspections per node (at most 4,096 in protocol).
2. A null root cell iff no feasible assignment respecting locks exists. Distinguish
   goal/lock infeasibility from inconsistent premises and from unresolved work.
3. Successful reconstruction reaches true, satisfies locks and has the reported
   objective; the reported cost is globally minimum among all feasible assignments.
4. False-before-True reconstruction with baseline completion is the lexicographically
   least optimal *total* assignment. Explain skipped-variable uniqueness formally.
5. Counts equal the number of distinct optimal total assignments. Low/high sets are
   disjoint; tied counts add; skipped variables do not introduce arbitrary extra
   assignments. Cover constants and n=0. Show count≤2^n and total cost≤24,000,000
   under the protocol, hence exact JavaScript integer representation (n≤24).
6. Each mandatory bit iff every optimal total assignment flips that variable; each
   possible bit iff at least one optimal total assignment flips it. These statements
   concern optimal assignments, not all feasible ones. Prove tie intersection/union
   semantics and mask range/non-overlap with forbidden locked flips.
7. `audit_proposal` feasibility is the actual conjunction of target, premises and
   locks; when both a proposal is feasible and an optimum is resolved, its reported
   gap is nonnegative and zero iff that proposal is optimal. An unresolved planner
   never supplies a gap. A false/infeasible proposal does not become accepted from
   having a low objective.
8. Compose compilation correctness with Bellman correctness to prove AST-level
   optimality/count/explanation contracts for successful typed intervention results.
   Resource-limit receipts contain no costs, assignment, count or Bellman table.

## 5. Decoder, refinement and evidence integrity boundaries

Typed proofs do not certify JSON bytes, named parsing, mutable caches, hashing,
serialization, browser concurrency, participant authenticity or research consent.
Specify concrete executable validators and prove any bridge actually completed:
strict exact fields, sorted distinct names, explicit Bool/int distinction, finite
limits, bounded ASTs, lexical grammar/precedence and innermost named binders.
The conditional text grammar binds NOT then AND then OR then right-associative
implication; aliases !/&/&&/|/||/->; uppercase declared variable names; logical
keywords case-insensitive; exact Unicode whitespace/splitlines rules matter.

Core receipt replay regenerates the entire deterministic result and checks all
content, including work and authority flags. Prove deterministic reference replay
rejects changed tasks, limits, cells, witnesses, masks or costs unless equal to the
reference output. SHA-256 collision resistance/content identity alone is not a
proof of algorithm correctness or authentication. Browser APIs snapshot input
before the first asynchronous digest; UI revision guards prevent stale downloads.
Explicitly list unproved Python/JavaScript refinement and external runtime
assumptions. Do not infer game-player identity or model-training generalization
from mathematically valid records. Existing game data remain consent/validation
bounded; no theorem creates scientific authority automatically.

## 6. Required executed controls and delivery

Run `cd formal && lake build && lake env lean PCSCountermodel/Audit.lean` plus
the new modules and their axiom audit under Lean 4.28. Keep existing imports/tests
passing. Include: implication reversal and De Morgan; remembered counterexample
rejection but partial-filter survivor requiring a fresh check; TRUE vs B under A
and A->B, with A removed giving disagreement; opposite premises with a dense
uncompiled query; 24-variable De Morgan; dense ordering work-limit; weighted
`A OR B` baseline false/false with costs 3/1 (minimum1, mandatoryB); tied costs1/1
(count2, no mandatory flip); lockB (mandatoryA); lockboth (infeasible); skipped B
in `A OR (B AND NOT B)` retaining a true B baseline; 12 disjoint two-variable
choices (24 variables, minimum12, count4096); TRUE/FALSE at n=0; inconsistent
context separately from infeasible goal. Do not require brute-force enumeration
of the 24-variable controls.

Provide genuine negative compilations for a false equivalence and a false weighted
minimum, and runtime rejection controls for invalid ordering/child IDs, zero costs,
forged counts/masks and exhausted work. Record intended semantic rejection, not
syntax/missing-import failures. Deliver all sources and exact build commands,
theorem-to-contract map, actual `#print axioms` output, completed/reference/refined
scope distinctions, and one list of any unresolved obligations. No theorem here
establishes natural-language interpretation, empirical causality, human provenance,
scientific discovery, a language-model breakthrough or real-world AI safety.
