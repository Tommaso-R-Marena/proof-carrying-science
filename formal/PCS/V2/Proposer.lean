import PCS.V2.DomainAuthority

/-!
# Untrusted proposer non-authority

PCS uses external (possibly AI) proposers to suggest claim translations, decompositions,
obligations and proof repairs.  This file proves that such a proposer has **no authority**:
whatever it proposes — honestly, incompetently, adversarially, adaptively after seeing
earlier verdicts, or stochastically — every proposal that PCS accepts has a true semantic
conclusion, under hypotheses about the *trusted checking layers only*.

A `Proposal` contains

* `claimId`     — which signed certificate claim the proposer wants to ground;
* `translation` — the proposer's suggested domain-native reading of that claim;
* `graph`       — the proposer's suggested decomposition into obligations (also the form of
  a proof *repair*: a repaired proposal is just another proposal).

`checkProposal` (deterministic, trusted) accepts a proposal only if domain acceptance of
the claim with the proposed graph succeeds and the proposer's translation **equals** the
claim obtained by the adapter's deterministic decoding of the signed predicate
(grounding).

A proposer is modelled as an arbitrary function from the feedback history to the next
proposal (`Strategy`); randomness is modelled by quantifying over all strategies (a
stochastic proposer is a distribution over strategies / seeds, and the theorems hold for
every seed).  `runLoop` is the propose → check → feedback → repair loop.

Theorems:

* `loop_output_checked` — (generic, any check) every output of the loop passed the check;
* `untrusted_proposer_cannot_forge_assurance` — PCS instance: any proposal output by the
  loop for any strategy denotes a true domain proposition, with PCS `Assures`;
* `no_strategy_forges` — the same, stated as non-existence of a forging strategy;
* `untrusted_proposer_archive_sound` — on top of the production raw-archive authoritt�PЀL@����r�