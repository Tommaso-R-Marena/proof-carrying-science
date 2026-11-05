# Post-integration research qualification and scientific-history join

## Outcome and branch boundaries

The scientific receiver now derives the expression/state link from exact
canonical input data. A new isolated wrapper joins that actual mathematical
check to the same co-signed candidate's transactional history admission. The
returned snapshot retains those checked bytes and rational results. This closes
a concrete missing conjunction; a valid signature or historical receipt alone
cannot authorize a mathematically false new artifact through this wrapper.

The stack base is the published validation branch
`integration/pcs-post-research-validation-20261019`, exactly
`cb9f4960cb7edbcc7c7ff92e96668d835646b4a1`. That branch combines independently
reviewable drafts, without merging their GitHub PRs. This follow-up changes only
new scientific-history files, their reports and its own workflow.

| Draft | Branch | Published component head |
| --- | --- | --- |
| [154](https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/154), negative receipts | `fix/pcs-intake-veto-receipts-v1-20261018` | `ba07e16a8f63fa031e9823b08a41f837a7a8531a` |
| [155](https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/155), independent audit | `audit/pcs-pr153-independent-qualification-v1` | `d847969c087a74fcc6997eefc23c6ee2c50e2a2a` |
| [156](https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/156), scientific receiver | `research/pcs-receiver-refinement-v1-20261018` | `eec5c653950c3d7975f3f3da0b72ce073b5afda4` |
| [157](https://github.com/Tommaso-R-Marena/proof-carrying-science/pull/157), authenticated history | `research/pcs-authenticated-history-v1-20261018` | `044f9c67263f57f722ddc078df2016d2284fa78e` |
| This isolated join | `research/pcs-scientific-history-v1-20261019` | Implementation `63efdd7`; final publication head/CI in PR description and external handoff |

The current remote main remains protected at
`fabc704efdbda4c8822881366e4db3d3e31f066a`. PR153 remains open/draft at
`b916eec1b9d0d5c02c9cc19b070f7a47df5e5d87`. All 32 original PR heads match
the recorded source snapshots. No production merge, deployment, force push or
original-branch update occurred. Production formal-tree bytes are unchanged.

## Mathematical claims and proof status

For the supported rational discrete A→B system,
`A(k)=A(0)-Σ(i<k)f(i)` and `B(k)=B(0)+Σ(i<k)f(i)`.
There are at most 64 firings; normalized rational input numerators have absolute
value at most 10^18 and denominators are in 1..10^18. The receiver fixes the
stoichiometry, conserved quantity, expression and variable interpretation.
Physical mode checks every received finite state and firing for nonnegativity;
it does not prove chemical kinetics, continuous trajectories or empirical truth.

The exact new receiver theorem is:

```lean
theorem verifiedWireSound (raw : List UInt8) (r : Result)
    (accepted : receive raw = some r) : ScopedScientificClaimHolds raw r
```

Here the conclusion is exactly
`∃ c, decode raw = some c ∧ encodeBytes c = raw ∧ ResultSound c r`.
`ResultSound` includes the checked initial/total/environment/step bindings,
the receiver-derived expression/state equality, conservation, A/B enclosures and
conditional finite physical admissibility. No semantic-link premise is supplied
by the producer. `decode_iff_bounded` characterizes all bounded typed encodings;
the encoded length is at most 3,360 bytes. Full statements and assumptions for
all 54 authored receiver theorems and 190 declarations are in the
[inventory](RECEIVER_THEOREM_INVENTORY.json) and retained qualification logs.
Existing conservation and numerical-soundness theorems are reused unchanged.

For the join, for every receiver-owned root, signature callback, state, envelope
and result, the exact theorem is:

```lean
theorem accepted_sound (root : Root) (verify : VerifySignature) (s : State)
    (e : Envelope) (r : Result)
    (h : (scientificTransition root verify s e).2 = some r) :
    AcceptedFacts root verify s e r
```

`AcceptedFacts` requires the fixed policy, empty auxiliary certificate,
`ScopedScientificClaimHolds e.payload.candidate r`, actual old-history transition
acceptance, state exactly `(commit s e, some r)`, incumbent exactly the candidate,
history exactly `s.history ++ [e]`, generation exactly `s.generation + 1`, and all
authority/witness/policy/checker equalities to the receiver-owned root.
Signature authenticity additionally requires the explicit soundness premise for
the signature callback. Pure key/checker bytes are opaque; their concrete shape,
cryptographic semantics and operator-configuration hash are runtime obligations.

Rejection leaves the state unchanged. An accepted envelope cannot be replayed
after any later wrapper trace. Whole-trace scientific validity requires a
scientifically checked initial history and incumbent; accepting new science does
not establish that premise retrospectively. The new join has 23 authored
theorems and 42 audited closures. The independent review additionally compiled
seven controls, including this contaminated-old-history boundary.

All proofs compile with Lean 4.28.0. Every audited closure uses only the permitted
standard axioms `propext`, `Classical.choice`, `Quot.sound`; no new axiom,
admission or unsafe shortcut was added. Complete join statements are in
`research/scientific_history_v1/reports/statements-and-axioms.log`; history
statements remain in its unchanged 28-theorem audit. See also
[formal join scope](SCIENTIFIC_HISTORY_FORMAL.md).

## Execution, security and negative evidence

The runtime binds the root checker to SHA256 of the fixed host configuration's
canonical identity. A request contains only immutable signed-envelope bytes.
Read-only signature/CAS preflight precedes actual Lean execution; transactional
append independently repeats signatures/CAS afterward. The original captured
envelope is committed, and a snapshot appears only after successful COMMIT.
Restart actually rechecks the incumbent. Current-snapshot reads audit the
retained checkpoint and never reopen a candidate artifact path.

The executable is compiled Lean IR run by pinned `lean --run`, not a standalone
native scientific receiver. Strict Python/Lean result correspondence is tested;
the Python framing/JSON/history/cryptographic/SQLite implementation is not
kernel-refined. Full receiver qualification inventories 4,983 imported modules
and 19,878 distinct dependency paths. The join runtime tests use an explicitly
partial inventory and do not claim that full profile. Source-to-object
correspondence, interpreter/compiler, OS, operator root/configuration and keys
remain trusted. Local dependency caches were source-checked and read-only;
local fresh dependency rebuild is not claimed.

Real two-key signatures, signed predecessor chain digests, generation/incumbent
CAS, exact replay and SQLite transactions protect the modeled local history.
An externally retained checkpoint is still necessary. A committed append whose
return/publication is lost causes a safe halt; recovery requires the exact
retained signed intent and prior anchor, then reconstruction with fresh checking.
No automatic recovery append or independently administered monotonic witness is
provided. Whole-store plus purported external-root/checkpoint replacement remains
indistinguishable. Python freezing/privacy, permissions, process separation and
ordinary hashes are not an immutable security root.

Independent review found that an earlier join launched expensive Lean work
before rejecting invalid signatures. Signature/CAS preflight now prevents this;
the independent reproductions confirm zero verifier launches for unauthenticated,
stale and replayed requests. Other preserved negative controls include validly
co-signed false science, a true response for different bytes, lost-return after
real commit, real process timeout, conflicting verified intents, and invalid
older signed entries followed by a valid incumbent. The latter correctly leaves
`historical_scientific_audit=False`.

## Tests, experiments and CI

The evidence sets are separate; their counts must not be summed as one run.

| Evidence | Actual outcome |
| --- | --- |
| Receiver suite | 160 passed, zero failures/skips |
| Prior combined components, tested `b1abffbb74a962a3f396e69b65f7b5bf9c70a99b` | 316 passed plus 47 additional passed subtests, zero failures/skips; one intentional duplicate-ZIP warning |
| Join implementation worktree | 16 passed in 97.387 s |
| Combined join branch rerun | 16 passed in 105.751 s, zero failures/skips |
| Independent join runtime reproductions | 12 passed, no remaining finding, stable reviewed source hashes |
| Fresh join formal audit, independently repeated | 23 authored / 42 closures passed; seven extra independent controls compiled |
| Source gate | 1,992 original entries + one receipt-contract pin; 38 V7 modules passed |
| Repository integrity / new-workflow actionlint | Passed |

The scientific preregistered campaign executed 10,774 actual-Lean cases in 44
families: 778 accepts, 9,996 rejects, no mismatches. The retained original run
took 801.091 s; its same-source concurrent compilation limitation is recorded.
Thirteen extra actual-process stress cases passed expected outcomes (11 accepts,
two rejects), including a 64-step cancellation with a 576-digit intermediate
denominator. These few startup-dominated timings establish no scaling law.

Three synthetic pilots retain exact transfer/conservation/enclosure, analytical
pharmacokinetic computational consistency, and finite causal non-identifiability.
The transfer pilot has final (13/2,7/2), total 10, and bounded A/B intervals. The
PK sample matches its analytical reference within 2e-15 mg/L and rejects a 10%
tamper; it supplies no clinical/physiological validation. The causal example has
observational TV 0 and intervention TV 1/2, with an explicit zero-positivity
limitation. Actual HECK falsifier and PCSNext invalidation compose through scoped
dimensions: a synthetic contradiction reopens applicability while retaining the
mathematical result. There is no external empirical study or causal upgrade.

Hosted final component evidence:

- [Receiver dedicated run 39192006649](https://github.com/Tommaso-R-Marena/proof-carrying-science/actions/runs/39192006649): success at `eec5c65`.
- [Receiver full public run 39192115831](https://github.com/Tommaso-R-Marena/proof-carrying-science/actions/runs/39192115831): all 11 jobs succeeded at `eec5c65`.
- [Receipt full public run 39190686652](https://github.com/Tommaso-R-Marena/proof-carrying-science/actions/runs/39190686652): all 11 jobs succeeded at `ba07e16`.
- [History dedicated run 39191133912](https://github.com/Tommaso-R-Marena/proof-carrying-science/actions/runs/39191133912): success at `044f9c6`.
- This join's final hosted run/head are recorded in its PR description and the
  external handoff after publication; this document does not predict its outcome.

Full public runs include fresh formal/axiom gates, real compiled production
authority, Python/JavaScript contracts, Rust component integration, independent
cleanroom, adversarial controls, learning research and existing platform checks.
Existing platform checks do not establish portability of the new POSIX host.
Exact new-join commands, hashes, logs, signed reproduction receipts, failed
development source-pin run and independent countermodels are retained under
`research/scientific_history_v1/reports/`, indexed by `EVIDENCE_INDEX.json`.
The source-pin development failure correctly rejected a mid-run edit; the final
stable-source runs pass. No positive verifier mock is used for authorization.

## Remaining obligations and readiness

1. An independently administered root, receiving process and monotonic checkpoint
   publication/recovery service remain the highest security gap. Without them,
   host/key compromise or joint history/checkpoint replacement defeats the model.
2. General executable refinement, history JSON/signature encoding refinement and
   source/object correspondence remain unproved. Pure accepted-transition proofs
   do not discharge these implementation obligations.
3. Scientific scope remains narrow and discrete. Units are declarations;
   arbitrary kinetics, ODE solvers, floating point/GPU execution and empirical
   applicability require additional specifications and evidence.
4. Full historical scientific audit is not established on startup. Its absence
   is explicitly reported rather than inferred from authentication.
5. Authoritative Aristotle V8 remains blocked on the missing expected artifact;
   no incomplete snapshot or proof-generation trace was promoted or used for
   training. Accelerating recursive self-improvement is not established.

The strongest publication candidate is a reproducible narrow byte-to-scientific-
claim receiver with explicit checked semantic binding, falsification-preserving
assurance and authenticated admission composition. The techniques reuse known
proof-carrying-code and verification ideas; priority/novelty and generality need
independent prior-art review and broader evaluation. There is no demonstrated
external research adoption.

The drafts support independent research reproduction and code/formal review.
They do not authorize a production merge or deployment. Review should verify
the exact source/profile successor, theorem statements/axioms, executable
configuration, independent campaigns, negative receipts and checkpoint assumptions.
The next highest-value milestone is a separately administered receiver/witness
with independently replayable checkpoint publication and crash recovery, tested
against whole-host rollback and key/storage separation.
