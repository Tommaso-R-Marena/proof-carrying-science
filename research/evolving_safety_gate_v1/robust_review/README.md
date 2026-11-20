# Corrupted reports and authenticated promotions

A receiver can decide correctly on every reachable report after up to `k` corrupted Boolean channels exactly when every pair of differently labeled episodes is more than `2k` channels apart. Different episodes can have different error budgets. In a separate model of delayed effects, a universal timeout requires a uniform bound on the allowed reporting delay. An offline promotion receiver also checks that a signed candidate improves its measured score and preserves each hard case the incumbent answered correctly.

## Monitoring

`RobustObservation.lean` uses a relation between episodes and possible reports. The episode can include the policy, proposed and executed actions, raw output and later effects. The relation specifies which of these a sensor actually reports. Labels are supplied separately.

| Lean theorem | Hypotheses and conclusion |
| --- | --- |
| `exact_verdict` | For any finite episode list, Boolean label and decidable Boolean compatibility relation, the executable monitor reports `b` iff at least one compatible row exists and every compatible row has label `b`. |
| `refinement` | If a later report still has a reachable row and its compatible rows form a subset of an earlier report's, every earlier decisive verdict persists. |
| `balls_intersect_iff` | For all widths `n`, Boolean words `x,y` and natural radii `a,b`, a word within both Hamming balls exists iff `d(x,y) ≤ a+b`. The induction constructs a common report when the bound holds. |
| `robust_monitor_iff` | For any finite domain, encoding into `n` Boolean channels and episode-specific corruption radii, the monitor is total and correct on every allowed report iff each cross-label pair satisfies `d(x,y) > r(x)+r(y)`. |
| `indistinguishable_pair` | If labels differ and the balls intersect, every deterministic observation-only monitor fails to give a correct verdict on at least one allowed report if it tries to decide both episodes everywhere. |
| `deadline_iff`, `no_uniform_timeout` | Suppose quiet episodes never emit an effect bit and a positive episode with deadline `d` emits it from time `d`. A decoder can certify the quiet episode and every allowed positive episode at time `t` iff all allowed deadlines are at most `t`. Allowing every natural deadline precludes this at any finite time. |

The finite-domain conclusion depends on the reachable-episode list, labels and corruption model. Removing a reachable conflicting episode can yield a false verdict outside the table. The Hamming result applies the classical minimum-distance argument to policy labels, per-episode radii and an abstaining receiver. It supplies no bound for an instrument that violates the declared budget. Indistinguishability arguments for delayed information also have a long history. [Hamming, 1950](https://doi.org/10.1002/j.1538-7305.1950.tb00463.x) · [Halpern and Moses, 1990](https://doi.org/10.1145/79147.79161)

## Promotion and the held-out boundary

A candidate is an immutable, eight-bit truth table over three Boolean channels. Packet bits 0, 1 and 2 record flags for proposal, execution and later effect respectively. Bit `p` of the table gives the candidate verdict on packet `p`. The artifact declares the existing `jointChannel` class. The receiver requires the candidate to distinguish unflagged packet 0 from packet 1, whose only flag is the proposal. Both predecessor and successor must meet this criterion. This class witness concerns these two packets.

`receiver.py` starts with an independently retained checkpoint. It pins the reviewer's public key by SHA-256, the challenge, evidence epoch, case-set digest, hard-contract digest, rule-source commitment, champion digest, generation and last receipt digest. The reviewer signs a domain-separated canonical encoding of the proposed edge, including both candidate digests, successor generation and a hash of that entire checkpoint. The rule commitment covers the Python receiver, Lean adapter, Lean gate and imported research admission table. A signature authenticates the review and candidate bindings through their hashes. Every prediction comes from the actual bounded candidate bytes. The envelope has no prediction or score field.

SHA-256 and Ed25519, canonical byte parsing, trusted source files, the pinned checkpoint, local execution tools and key custody are engineering assumptions. A valid signature authenticates what the holder approved. The accuracy and independence of their labels require evidence from outside the protocol. The published fixture key was generated locally for this demonstration. Each invocation is a pure transition from its supplied checkpoint. A service consuming these receipts would need durable compare-and-swap state to arbitrate concurrent successors and prevent checkpoint rollback. [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032) · [Torres-Arias et al., in-toto](https://www.usenix.org/conference/usenixsecurity19/presentation/torres-arias)

| Lean theorem | Hypotheses and conclusion |
| --- | --- |
| `HardReview.gate_exact` | For arbitrary predictor and case types, anchors and finite hard/measured lists, the Boolean gate accepts iff both tables satisfy behavioral admission, every previously correct hard case stays correct, and the measured correct count strictly increases. |
| `HardReview.path_preserves` | From an admitted seed along any finite path of accepted edges with fixed predictor semantics, anchors and hard cases, the final candidate is admitted and preserves every hard answer the seed got right. Each edge may use a different measured set. |
| `HardReview.sweep_scores`, `HardReview.repeated_heldout_loss` | For any benchmark size `n`, a constructed family at generation `g` scores `min(n,g)` on the measured set and `n−min(n,g)` on an equally large disjoint held-out set. Each of the `n` successive steps is accepted, preserves its protected anchors and loses exactly one held-out answer. |

The wire lineage pins one review digest in its checkpoint. Using a different measured suite requires the receiver to provision a new trusted checkpoint while retaining the hard-contract digest. The sweep uses arbitrary finite cases in the generic Lean gate. The wire implementation specializes that gate to eight packet values. The sweep is a constructive possibility result for repeated optimization. Its construction supplies no prevalence estimate. [Dwork et al., 2015](https://doi.org/10.1126/science.aaa9375)

## Replay evidence

Use repository-pinned Lean 4.28.0 on PATH and a Python environment with the repository dependencies. From the root run

```sh
python -m research.evolving_safety_gate_v1.robust_review.replay /tmp/new-robust-review
python -m pytest -q research/evolving_safety_gate_v1/robust_review/test_receiver.py
```

The output directory must be new. The replay builds from source, audits all eleven theorem closures, runs a fresh kernel check, matches all finite audit outputs against Python and runs the signed fixture through the normal CLI at both generations. It writes each CLI input and output checkpoint for inspection. A single edge can then be rerun from that directory using the repository-path receiver and the arguments `state0.json reviewer.pub review.json edge1.json mask18.json mask22.json`.

| Replay | Evidence |
| --- | --- |
| All opposite-label Boolean word pairs, widths 0–4, both radii from 0 to width | 7,585 pair/radius combinations. Exactly 1,062 satisfy full robust separation. Independently enumerating subsets of flipped bits matched Lean on 111,201 report cells, including 53,260 decisive, 40,339 conflicting, and 17,602 unreachable. |
| All ordered pairs of eight-bit detector tables on each of two fixed review suites | 131,072 Lean decisions independently matched Python. There were 1,332 accepted and 129,740 rejected transitions. The suites include conflicting measured labels for one packet and pointwise hard constraints. |
| Signed synthetic lineage | Two accepted generations, measured scores 1/3 → 2/3 → 3/3 and 2/2 protected answers at every generation. The signing secret is absent from the fixture. |
| Receiver controls | 35 tests, consisting of the positive two-generation lineage and 34 rejection controls. These include substituted source bytes, signed but stale edges, changed cases, incomplete evidence, equal hard counts with a lost protected answer, and disagreement between semantic interpreters. |

`deadline_iff` uses `propext`. Each of the other ten theorem closures contains only `propext` and `Quot.sound`. The mathematical results are formal applications of known arguments, plus a parameterized negative example for this gate. The dual replay validates the bounded implementation on the stated domains. Operational use still requires independent labels, trusted checkpoints and representative telemetry.
