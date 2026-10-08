import PCS.V2.DomainAdapter
import PCS.V2.ClaimGraphMemo

/-!
# Distributed, untrusted contributors cannot forge PCS assurance

A finite population of contributors (humans, AI systems, adversaries, stochastic or
adaptive strategies, colluding coalitions) submits obligation-graph nodes — claims,
decompositions, repairs, leaf evidence, checker inputs, adversarial cases — in an
arbitrary interleaving.  **No contributor is assumed honest or competent.**

## Protocol

The shared store is a list of committed entries `(author, node)`.  A submission becomes
authoritative (is committed) only if the deterministic admission check `admitSubmission` passes:

* the node id is not already committed (**no overwrite**: an accepted commitment can never
  be replaced, by its author or anyone else);
* a **leaf** is admitted only if the trusted validator accepts its obligation for the
  leaf's *own* claim (`V.leaf ob claim`); unverified material can never discharge a leaf;
* a **derivation** is admitted only if every child id is already committed and the trusted
  rule check accepts the parent claim from the committed children's claims (so the
  committed graph is built bottom-up and is acyclic by construction);
* an **unsupported** node is never admitted.

The root id and the root claim `goal` are protocol parameters fixed by the deterministic
claim binding (for PCS: the compiled, signed certificate claim); contributors cannot choose
them.  `protocolAccepts` holds iff the committed node with the root id carries exactly
`goal`.

## Results

* `run_invariant` — under `CheckerSound V Sem`, **every committed node's claim holds**, for
  every submission list (hence for every population, strategy and interleaving).
* `accepted_contributions_cannot_forge_assurance` — for every contributor population,
  every (adaptive, stochastic, colluding) strategy profile and every schedule, protocol
  acceptance implies `Sem goal`.  No honesty assumption appears.
* Protocol facts: `unverified_leaf_rejected`, `no_overwrite`, `committed_persistent`,
  `committed_provenance` (nothing is invented and authorship is preserved),
  `committed_ids_nodup`, `committed_children_earlier` (acyclic by construction),
  `accepted_root_claim_fixed`, `accepted_conclusion_order_independent`,
  `coalition_is_submission_list` (collusion = an arbitrary joint submission list, already
  covered).
* Honest limitation (proved, not hidden): an adversary *can* block acceptance by squatting
  an id first (`squatting_blocks_liveness`) — ordering can change **whether** the root is
  accepted, never **what** an accepted root means.
* `pcs_distributed_domain_sound` — the PCS instance: contributions checked against an
  accepted PCS package with the adapter's induced checker yield the domain proposition.
-/

set_option autoImplicit false

namespace PCS.V2.DistributedContributors

open PCS.V2.ClaimGraph

variable {Cid L C : Type}

/-- A submission: who proposes which node. -/
structure Submission (Cid L C : Type) where
  author : Cid
  node : Node L C

/-- The committed store. -/
abbrev Store (Cid L C : Type) := List (Submission Cid L C)

/-- Claims of committed children; `none` if one is not committed. -/
def childClaims (st : Store Cid L C) : List String → Option (List C)
  | [] => some []
  | i :: is =>
    match st.find? (fun e => e.node.id == i), childClaims st is with
    | some e, some cs => some (e.node.claim :: cs)
    | _, _ => none

/-- Local admission validation of a node against the current store. -/
dee4T4 =�㽜���