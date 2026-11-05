# Independently replayed finite action-shield assurance

PCS has a first-party finite-state tool-use shield whose concrete certificate is
freshly kernel-checked in a receiving process. The general Lean induction theorem
then establishes safe states and forbidden-action exclusion for **every finite
admitted history**, under any proposing policy and every declared nondeterministic
outcome. This extends the existing bounded committed-trace capability; no observed
trajectory is substituted for the universal model certificate.

The implementation was developed against protected core `c600b007940881fd65fe41d2adddd5f002679478`.
It is new first-party continuation, not an imported external AI-safety result.
External proof-generation traces were not used as training data. The new model is
an authored illustrative monitor, with no empirical deployment observations,
authenticated outside reviewer or claim of general AI safety.

## Exact new formal contracts

The Std-only [`PCSActionShield.lean`](../formal/PCSActionShield.lean) adds:

| Theorem | Exact scope |
|---|---|
| `PCSActionShield.check_iff_certified` | Finite Boolean closure check is equivalent to safe initial states and preservation/exclusion for every admitted modeled edge from every safe source. |
| `PCSActionShield.admitted_histories_safe` | Any finite history starting at a declared initial state and following admitted modeled edges ends safe and contains no forbidden action. No policy correctness assumption. |
| `PCSActionShield.optimized_guard_histories_safe` | Same conclusion for any guard extensionally matching the allowed state/action table. Guard correspondence must be proved separately. |
| `PCSActionShield.deployed_histories_safe` | A deployed history's abstract state is safe under explicit initial-state, transition and admission correspondence. These premises are not established by the certificate. |

Each receiving replay generates two concrete named theorems:
`PCSActionShieldReplay.certificate_checked` and
`PCSActionShieldReplay.all_finite_histories_safe`. The first is proved by kernel
`decide`, with no `native_decide`; the second instantiates the general induction
theorem with those exact integer literals. The receiver executes a private
snapshot of its own formal source and regenerated data proof, ignoring producer
proof-generation transcripts.

Seven additional kernel-checked controls in
[`PCSActionShieldControls.lean`](../formal/PCSActionShieldControls.lean) prove the
positive certificate and universal consequence, reject an unobserved unsafe
nondeterministic successor, exhibit both an actual safe observed history and an
actual unsafe admitted alternative, reject a forbidden action even with a safe
target, demonstrate the missing-model-branch correspondence boundary, and show
that an all-deny safe certificate can deadlock. The fresh audit of all 11 distinct
static theorem names reports only `propext` and `Quot.sound`; concrete replay also
audits both generated theorem names and rejects unexpected axioms.

## Implemented executable capability

[`pcs/action_shield_v1.py`](../pcs/action_shield_v1.py) provides strict bounded
model/certificate intake, an untrusted deterministic shield proposer, independent
closure/reachability diagnostics, actual proposal filtering, deterministic Lean
proof rendering, and fresh private kernel compilation. Unsupported versions,
resource exhaustion, malformed fields, stale model hashes and failed proofs grant
no kernel support.

The supported fragment has up to 32 states, 16 actions, 512 transition triples and
512 allowed pairs, with 2 MiB input limits. State/action IDs are exact natural
integers below 65536. Initial/safe sets are nonempty; data lists and triples must
be sorted and unique. Boolean/numeric confusion, unknown endpoints, missing
successors, duplicate JSON keys, nonfinite JSON and undeclared fields are rejected.
Only validated integer literals enter generated Lean text; free-form premise
statements are retained as provenance and never interpreted as proof code.

The [`tool-use example`](../examples/action_shield_v1/README.md) distinguishes
unreviewed requests, reviewed grants, confidential and sanitized payloads,
completion and unauthorized disclosure. Confidential network sending has a
declared safe outcome and an unsafe outcome. Universal replay rejects a shield
that permits that action despite its safe observed outcome. The alternative
shield permits review, authorized loading, sanitization, sanitized sending and
completion. Forbidden bypass exclusion is checked independently of state safety.

The proposer is not an authority. The receiver permits weaker/nonmaximal safe
certificates and reports reachable deadlocks. Liveness and maximal permissiveness
remain OPEN. A valid all-deny certificate never becomes a useful-task or liveness
guarantee.

## Executed and preserved evidence

The immutable final campaign is
[`research/action-shield-v1/final`](../research/action-shield-v1/final/).
Its protocol pins and archives the exact core, adapter and campaign sources; every
case retains original model/certificate bytes, independent Python report,
regenerated Lean proof and actual receiving kernel outcome.

| Observation | Final execution |
|---|---|
| Fresh model/kernel cases | 53: five tool-use controls and 24 seeded positive/negative pairs |
| Actual kernel acceptances / rejections | 27 / 26 |
| Python/kernel outcome mismatches | 0 |
| Final campaign wall time | 57.331705 s |
| Child user / system CPU | 41.062768 / 15.602171 s |
| Largest child RSS, Linux | 420,552 KiB |
| Focused tests | 33 passed, including actual positive and negative kernel compilation |
| External empirical observations / training / spend | None / none / zero |

The earlier 53-case campaign is preserved unchanged under
`preceding-admission-interface`; it precedes the runtime proposal-filter entry
and exact adapter/script source archival. It is not counted as an additional
independent scientific result. Both campaigns include a deliberately incomplete
model which is formally safe only for its changed relation; deployment/model
completeness remains OPEN. The evidence seal is unsigned byte-consistency metadata,
not outside scientific validation.

Reproduce into a new output directory:

```sh
python scripts/run_action_shield_campaign_v1.py --output /tmp/pcs-action-shield-fresh
python -m pytest -q tests/test_action_shield_v1.py
cd formal
lake env lean PCSActionShieldAudit.lean
```

## Remaining authority boundaries

Model completeness, accurate observations and shield enforcement without a bypass
are explicit typed OPEN premises in the model. Initial-state, transition and
admission abstraction are hypotheses of the deployment theorem; `FaithfulLog`
remains required for existing trace-to-deployment results and is not discharged
by this work. Producer signatures establish byte/identity integrity under the
existing `NoForgery` assumptions, not truth of modeling premises.

The receiving kernel checks the regenerated Lean literal model and exact source
snapshot. The SHA identity binds original JSON bytes operationally; JSON parser,
literal renderer and Python proposal-filter correspondence are not universally
source-extracted by this module. Native compiler/operating system correctness,
sensor integrity, real-tool transition completeness, unrestricted continuous
state, timing/concurrency side channels, liveness and empirical safety are not
proved. Formal model truth, implementation correspondence, scientific assumptions
and empirical validity remain separate.

The specialized package receiver may combine this fresh certificate with existing
PCS package integrity and separately supported implementation correspondence. The
new shield claim remains OPEN in the base v0.6 authority until a registered
proof-carrying checker is added through its normal source-integrity gates. A
specialized receiving result must label its independently checked formal model
support explicitly and must not silently rewrite the base claim decision.
