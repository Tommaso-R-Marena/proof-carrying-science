import PCS.V2.Witnesses.Instances

/-!
# Falsification attempts against the generic abstractions

Each attack is either **impossible** (the deterministic checker rejects it â€” proved by
evaluation) or appears as an **explicitly failed premise** (proved by exhibiting the
counter-model).  Concrete attacks reuse the biology witness (`MAVKL`, sites `2 3 5`,
threshold 3) whose honest graph `bioGraph` is accepted (`bioGraph_accepted`).

| attack | outcome |
|---|---|
| cyclic decomposition | rejected (`cyclic_rejected`; general: `ClaimGraph.cycle_rejected`) |
| missing leaf / unresolved child | rejected (`missing_leaf_rejected`; general: `missing_child_rejected`) |
| duplicate node ids | rejected (`duplicate_rejected`; general: `duplicate_ids_rejected`) |
| unsupported node | rejected (`unsupported_node_rejected`; general: `unsupported_rejected`) |
| wrong claim binding (graph for another root) | rejected (`wrong_root_rejected`) |
| swapped artifact in evidence | rejected (`swapped_artifact_rejected`) |
| stale / failed evidence | rejected (`failed_evidence_rejected`) |
| evidence not required by the claim | rejected (`unrequired_evidence_rejected`) |
| leaf proposition â‰  parent's expectation | rejected (`weaker_leaf_rejected`) |
| dishonest adaptive proposer | loop returns nothing (`adversary_gets_nothing`) |
| unsound decomposition rule | premise `CheckerSound.rule` fails (`rule_soundness_necessary`) |
| unsou4T4 =x×Í…ªì