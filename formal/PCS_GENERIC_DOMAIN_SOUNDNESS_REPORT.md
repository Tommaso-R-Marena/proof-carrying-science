# PCS generic-domain soundness report

This covers the domain-independent layer added to the production V2 formalization
(`PCS/V2/…`). It builds on `PCS.V2.Frontier.pcs_frontier_archive_acceptance_sound` and leaves
that theorem and every existing definition unchanged.

New files (2360 lines, all part of the default `PCS` library target):

| file | content |
|---|---|
| `PCS/V2/ClaimGraph.lean` | Theorem 2: heterogeneous proof-obligation graphs (Lean core only) |
| `PCS/V2/DomainAdapter.lean` | Theorem 1: generic domain adapters |
| `PCS/V2/DomainAuthority.lean` | Theorem 5: flagship for the production authority and for the authority extended with domain checkers |
| `PCS/V2/Proposer.lean` | Theorem 3: untrusted proposer non-authority |
| `PCS/V2/WorkflowRefinement.lean` | Theorem 4: compositional workflow refinement (Lean core only) |
| `PCS/V2/Witnesses/Registry.lean` | how domain checkers are registered (`registry_valid`) |
| `PCS/V2/Witnesses/Biology.lean` | witness 1: computational biology |
| `PCS/V2/Witnesses/AISafety.lean` | witness 2: AI-safety trace invariant |
| `PCS/V2/Witnesses/MLEval.lean` | witness 3: ML-evaluation split hygiene, run on the **unchanged production authority** |
| `PCS/V2/Witnesses/Instances.lean` | one shared registry for the witnesses, plus non-vacuity runs |
| `PCS/V2/Witnesses/WorkflowWitness.lean` | a small instance of Theorem 4 |
| `PCS/V2/GenericCounterexamples.lean` | falsification attempts (each proved) |
| `PCS/V2/GenericAudit.lean` | `#print axioms` for all 56 new results |

`PCS.lean` imports all of them. No existing file was modified apart from that import list.

---

## 1. Theorem statements and what they establish

### Theorem 2: obligation-graph root assurance (`PCS.V2.ClaimGraph`)

Data. A graph `Graph L C` is a list of nodes `⟨id, claim : C, kind⟩` plus a root id. A node's
`kind` is one of:

* `leaf (ob : L)`,
* `derive (rule : String) (children : List String)`,
* `unsupported tag`.

`L` (the obligation type) and `C` (the claim IR) can be any types. The only trusted component
is a `Checker L C`, made of `leaf : L → C → Bool` and `rule : String → C → List C → Bool`.

```lean
structure CheckerSound (V : Checker L C) (Sem : C → Prop) : Prop where
  leaf : ∀ ob c, V.leaf ob c = true → Sem c
  rule : ∀ r p cs, V.rule r p cs = true → (∀ c ∈ cs, Sem c) → Sem p

theorem root_assurance_sound [DecidableEq C] {V : Checker L C} {Sem : C → Prop}
    (hV : CheckerSound V Sem) {g : Graph L C} {goal : C}
    (h : checkGraph V g goal = true) : Sem goal

theorem accepted_graph_facts [DecidableEq C] {V : Checker L C} {g : Graph L C} {goal : C}
    (h : checkGraph V g goal = true) : AcceptedGraph V g goal
```

`AcceptedGraph` holds with **no** soundness assumption. It says:

* node ids are duplicate-free;
* the root exists and its claim is exactly `goal`;
* every node reachable from the root exists and passes its local check. So it is not
  `unsupported`, all of its children exist, its rule check passes, and if it is a leaf its
  validator accepts the leaf's *own* claim;
* no cycle passes through any reachable node.

Rejection corollaries: `cycle_rejected`, `missing_child_rejected`, `duplicate_ids_rejected`,
`unsupported_rejected`.

Heterogeneous evidence: `Checker.sumLeaf` and `sumLeaf_sound` combine validators over different
obligation types `L₁ ⊕ L₂` (formal, computational, empirical, external, …). The combined
validator is sound if each part is.

Scope. The theorem applies to any finite graph, including DAGs with shared children.
Termination is ensured by a fuel bound equal to the number of nodes. Cycles are caught by the
ancestor-path check (and in any case cannot pass, because of the fuel bound). Soundness does not
depend on the duplicate-id check, but acceptance guarantees it anyway.

### Theorem 1: generic domain-adapter soundness (`PCS.V2.DomainAdapter`)

```lean
structure Domain where
  World : Type
  Claim : Type
  [decEq : DecidableEq Claim]
  Holds : World → Claim → Prop

structure DomainAdapter (D : Domain) where
  IR : Type
  [decEqIR : DecidableEq IR]
  decode : JVal → Option D.Claim          -- typed decoding of the signed claim predicate
  compile : D.Claim → Option IR           -- typed compilation to the root obligation
  world : ArtifactTable → D.World          -- world given by the committed artifact bytes
  sem : D.World → IR → Prop
  leafCheck : JVal → IR → Bool            -- evidence object ⟶ IR node
  ruleCheck : String → IR → List IR → Bool

structure AdapterSound (A : DomainAdapter D) (Valid : ReplayRequest → Prop) : Prop where
  compile_sound : ∀ w c ir, A.compile c = some ir → A.sem w ir → D.Holds w c
  rule_sound : ∀ w r p cs, A.ruleCheck r p cs = true → (∀ q ∈ cs, A.sem w q) → A.sem w p
  leaf_sound : ∀ req n, A.leafCheck req.evidence n = true → Valid req →
    A.sem (A.world req.artifacts) n

theorem domain_adapter_sound {O : Oracles} {T : TrustAnchor} {inp : PackageInput}
    {r : AcceptedResult} {Valid : ReplayRequest → Prop} (hacc : acceptPCS O T inp = some r)
    (hV : ReplayFaithful O.exec Valid) (A : DomainAdapter D) (hA : AdapterSound A Valid)
    {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (h : domainAccepts A r cid g = some c) : DomainAssurance A r cid g c
```

`domainAccepts A r cid g` succeeds only if all of the following hold:

1. certificate claim `cid` exists;
2. it has an accepted normalized decision whose status is an assurance level;
3. its predicate decodes to `c`;
4. `c` compiles to `ir`;
5. the **untrusted** graph `g` is accepted for `ir` by the induced checker `pcsChecker A r cl`.

That checker's leaves are evidence ids. A leaf is discharged only if all of these hold:

* the evidence is required by claim `cid`;
* its replayed outcome is `PASS`;
* `leafCheck` accepts its evidence object for the leaf's own IR claim.

`DomainAssurance` contains:

* `holds : D.Holds (A.world r.table) c`, i.e. the domain proposition about the committed,
  digest-bound artifacts;
* `bound`: `c` is the decoding of signed certificate claim `cid`;
* `pcsAssures`: PCS's kernel judgement `Assures (gamma p.2) L (kernelClaim p.2) (kernelEvidence p.2)`
  for that claim;
* `graph`: the `AcceptedGraph` facts.

The theorem works for arbitrary oracles `O`. The link to the executor is only the existing
`ReplayFaithful` interface.

### Theorem 3: untrusted-proposer non-authority (`PCS.V2.Proposer`)

```lean
abbrev Strategy (α : Type) := History α → α        -- arbitrary, adaptive
def runLoop (check : α → Bool) (P : Strategy α) : Nat → History α → Option α

theorem untrusted_proposer_cannot_forge_assurance {O : Oracles} {T : TrustAnchor}
    {inp : PackageInput} {r : AcceptedResult} {Valid : ReplayRequest → Prop}
    (hacc : acceptPCS O T inp = some r) (hV : ReplayFaithful O.exec Valid)
    (A : DomainAdapter D) (hA : AdapterSound A Valid)
    (P : Strategy (Proposal A)) (fuel : Nat) (h₀ : History (Proposal A)) {p : Proposal A}
    (hrun : runLoop (checkProposal A r) P fuel h₀ = some p) :
    D.Holds (A.world r.table) p.translation ∧
      DomainAssurance A r p.claimId p.graph p.translation
```

A `Proposal` consists of a claim id, a suggested domain translation, and a suggested
decomposition graph. A repair is simply another proposal. `checkProposal` adds a grounding
check: the proposed translation must **equal** the adapter's deterministic decoding of the
signed predicate.

There is no hypothesis about `P`. The proposer is modelled as an adaptive function of the
verdict history. A stochastic proposer is covered by `stochastic_proposer_sound`, which
quantifies over all seeds.

Related results:

* `no_strategy_forges`: the same statement, phrased as the non-existence of a forging strategy;
* `loop_output_checked`: the same principle for any check function;
* `untrusted_proposer_archive_sound`: the same on top of the production raw-archive authority.

### Theorem 4: compositional workflow refinement (`PCS.V2.WorkflowRefinement`)

```lean
structure Contract (α β : Type) where  pre : α → Prop;  post : α → β → Prop
abbrev Impl (α β : Type) := α → Option β                       -- fail-closed
def Refines (f : Impl α β) (K : Contract α β) : Prop := ∀ a b, K.pre a → f a = some b → K.post a b
def Contract.seq  -- demonic composition: pre₁ ∧ (∀ b, post₁ a b → pre₂ b);  ∃ b, post₁ ∧ post₂

inductive Pipeline : Type → Type → Type 1
  | stage (K : Contract α β) (f : Impl α β) : Pipeline α β
  | seq (p : Pipeline α β) (q : Pipeline β γ) : Pipeline α γ

theorem pipeline_refines : ∀ {α β : Type} (p : Pipeline α β), p.StagesRefine →
    Refines p.impl p.spec
theorem pipeline_total : ∀ {α β : Type} (p : Pipeline α β), p.StagesTotal →
    Refines p.impl p.spec ∧ Total p.impl p.spec
```

Pipelines can have any length and any bracketing, the intermediate types can differ, and the
contracts can be relational (non-deterministic). `seq_pre_of_compatible` shows that when
adjacent stages are compatible, the composed precondition is just the first stage's.

Instance: `Witnesses.WorkflowWitness.evaluator_sound`. The three-stage evaluator
trace → risks → cumulative risk → verdict, with types `List UInt8 → List Nat → Nat → Bool`,
certifies the per-transition invariant on every accepted run.

### Theorem 5: flagship from raw signed archive to domain proposition (`PCS.V2.DomainAuthority`)

**Production authority (unchanged code path):**

```lean
theorem pcs_generic_domain_archive_acceptance_sound {t : AuthorityTranscript} {T : TrustAnchor}
    {signed : List UInt8 → Prop} (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {ExtHolds : ReplayRequest → Prop} (hExt : ReplayFaithful (transcriptExecutor t) ExtHolds)
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithTranscript t T raw = some (inp, r))
    (A : DomainAdapter D) (hA : AdapterSound A (BuiltinHolds ExtHolds))
    {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (hd : domainAccepts A r cid g = some c) :
    (∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
      HighAssurance t T (verifiedContracts t T signed hB) inp r) ∧
    DomainAssurance A r cid g c
```

`pcs_generic_domain_archive_acceptance_sound_builtin` takes `ExtHolds := "transcript said PASS"`,
which discharges `hExt`. Its only hypotheses are therefore `NoForgery` and `AdapterSound`.

**Authority extended with registered domain checkers.** Here
`authorityOraclesWith cs t` runs `dispatch (builtinCheckers ++ cs) (transcriptExecutor t)`.

```lean
theorem pcs_generic_domain_archive_acceptance_sound_with (cs : List CertifiedChecker)
    {t : AuthorityTranscript} {T : TrustAnchor} {signed : List UInt8 → Prop}
    (hB : NoForgery PCS.V2.Ed25519.verify T.pk signed)
    {ExtHolds : ReplayRequest → Prop} (hExt : ReplayFaithful (transcriptExecutor t) ExtHolds)
    {raw : ByteArray} {inp : PackageInput} {r : AcceptedResult}
    (h : acceptArchiveWithCheckers cs t T raw = some (inp, r))
    (A : DomainAdapter D) (hA : AdapterSound A (AuthorityValid cs ExtHolds))
    {cid : String} {g : Graph String A.IR} {c : D.Claim}
    (hd : domainAccepts A r cid g = some c) :
    (∃ es, CanonicalZip raw es ∧ ArchivePartition es inp ∧
      ExtendedAssurance cs t T (extendedContracts cs t T signed hB ExtHolds hExt) inp r) ∧
    DomainAssurance A r cid g c
```

`…_certified` discharges `hExt` in the same way. `ExtendedAssurance` re-derives, for the
extended executor, everything the frontier theorem gives:

* the full generic `ScientificAssurance` (structure, canonical control records, exact member
  set, claim scope, per-claim `Assures`, authenticity under `NoForgery`, environment);
* the transcript binding;
* that built-in evidence keeps its verified semantics (`authorityValid_builtin`: domain
  checkers run after the built-ins and cannot shadow them);
* FIPS 180-4 member and artifact digests;
* `EnvFacts`;
* `WorkflowDescribes`.

`acceptArchiveWithCheckers_nil` proves that with `cs = []` the extended authority **is**
`acceptArchiveWithTranscript`.

---

## 2. Hypotheses and trusted components

| item | where it appears | status |
|---|---|---|
| `NoForgery` for the Lean RFC 8032 verifier and the trust-anchor key | flagship theorems | cryptographic hypothesis, inherited unchanged from the frontier theorem |
| `hExt : ReplayFaithful (transcriptExecutor t) ExtHolds` | `…_sound`, `…_with` | the meaning of transcript-reported PASS for evidence kinds that no certified checker handles. Discharged for free in `…_builtin` / `…_certified`, where transcript reports get only their literal meaning |
| `AdapterSound A Valid` | every domain theorem | the per-domain contract. Proved once for each witness |
| `Registered ks` (tags unique and not built-in) | witness instances | decidable; proved by `decide` for the witness registry |
| `ReplayFaithful O.exec Valid` | Theorems 1 and 3 (arbitrary oracles) | a theorem for the authority executors (`builtinExecWith_faithful`, `authorityWith_faithful`) |

The proposer and the obligation graph appear in **no** hypothesis.

Axioms, as printed by `PCS/V2/GenericAudit.lean` for all 56 audited results: only `propext`,
`Classical.choice` and `Quot.sound` (or a subset). `Checker.sumLeaf_sound` uses no axioms.

No new `axiom`, `sorry`, `admit`, `unsafe`, `extern`, `implemented_by` or `native_decide`. The
concrete computations use only kernel `decide`.

---

## 3. Counterexamples found and falsification attempts

All of these are proved in `PCS/V2/GenericCounterexamples.lean`. The concrete attacks reuse the
biology witness, whose honest graph is accepted (`bioGraph_accepted`).

| attack | result |
|---|---|
| cyclic decomposition | rejected: `cyclic_rejected` (general form `cycle_rejected`) |
| missing leaf or unresolved child | rejected: `missing_leaf_rejected` (general form `missing_child_rejected`) |
| duplicate node ids | rejected: `duplicate_rejected` |
| unsupported node (e.g. "llm-says-so") | rejected: `unsupported_node_rejected` |
| wrong claim binding (honest graph, different root claim) | rejected: `wrong_root_rejected` |
| swapped artifact (evidence checks `bad_sites` instead of `sites`) | rejected: `swapped_artifact_rejected` |
| stale or failed evidence (replayed outcome `FAIL`) | rejected: `failed_evidence_rejected` |
| evidence belonging to another claim (not in `requiredEvidence`) | rejected: `unrequired_evidence_rejected` |
| accepted leaf whose proposition differs from what the parent expects (threshold 2 vs 3) | the leaf passes on its own (`weaker_leaf_accepted_alone`), but the graph is rejected (`weaker_leaf_rejected`) |
| dishonest adaptive proposer cycling through all the attacks above | the loop returns `none`: `adversary_gets_nothing` |
| unsound decomposition rule | **failed premise**: the graph is accepted and leaves are sound, but the root is false (`rule_soundness_necessary`) |
| unsound leaf validator | **failed premise**: `leaf_soundness_necessary` |
| checker returning success without proving its semantics (`Valid := True`) | `AdapterSound` is **false** (`trusting_reports_unsound`), so it cannot be supplied |
| lossy compilation (drops the score obligation) | `compile_sound` is **false** (`lossy_compile_unsound`) |
| two domains registering the same tag | the second checker is shadowed. `Registered.nodup` is needed (`duplicate_tag_shadowing`) |

Design points shaped by these attempts:

* **Leaves bind their own claim.** A leaf validator is asked whether `ob` discharges *the
  leaf's own claim*, and the parent's rule check consumes exactly that claim. Without this
  binding, a weaker leaf could be presented to a parent that expects a stronger one.
* **The proposer cannot pick the meaning.** It may choose which claim id to ground, but its
  translation must equal the deterministic decoding of the signed predicate. Otherwise a
  proposer could attach a true but unrelated domain claim to a signed package.
* **Built-ins keep priority.** If domain checkers were dispatched before the built-ins, a domain
  checker claiming the `csv_disjoint` tag could change the meaning of built-in evidence.
  Dispatching built-ins first is proved semantics-preserving (`authorityValid_builtin`).
* **Domains cannot discharge a claim with zero obligations.** The AI-safety adapter refuses to
  compile a claim with an empty trace list, so no claim is vacuously "safe". Each adapter has
  to watch for vacuous decompositions like this; the generic theorem cannot detect them.

### The desired strength is false without an explicit data assumption

The pseudo-signature concludes `D.Holds c` with no world. That is **not provable** for domains
whose semantics refer to the external world (a physical protein, a deployed policy, a
laboratory). PCS only certifies properties of committed bytes. Two worlds that agree on the
committed artifacts but disagree on the external fact receive the same accepted archive, so no
acceptance-based theorem can tell them apart.

The strongest correct form is therefore the one proved here:
`D.Holds (A.world r.table) c`, where `A.world` interprets the delivered, digest-bound,
manifest-signed artifacts. Carrying this over to the external world needs an additional,
domain-specific premise (for example "the committed sequence is the sequence of protein X").
That premise is outside PCS's competence and is deliberately not assumed anywhere.

---

## 4. What remains unproved or out of scope

* **Completeness of `checkGraph`.** We do not prove that every well-formed acyclic graph is
  accepted. Acceptance is demonstrated on concrete graphs for all three witnesses
  (`bioGraph_accepted`, `aiGraph_accepted`, `mlGraph_accepted`). `evalNode` re-evaluates shared
  sub-DAGs, so its running time can be exponential in the amount of sharing. This affects
  efficiency, not soundness.
* *Status update (later runs): the two items below have since been closed. The binary
  now runs the certified extended authority (`PCS/V2/ExecutableAuthority.lean`). A real
  Ed25519-signed AI-safety archive is accepted end to end, and that acceptance is a kernel
  theorem (`PCS.V2.Golden.aiSafetyGoldenArchive_accepts`,
  `PCS.V2.Golden.pcsLeanAuthority_golden_zip_output`). See
  `PCS_AI_SAFETY_EXECUTABLE_ASSURANCE_REPORT.md` §1–2. The original text follows.*
* **The binary does not run the extended authority.** The compiled `pcs-lean-authority`
  (`PCSAuthority.lean`) still runs the production authority, which equals
  `acceptArchiveWithCheckers []`. Wiring a domain registry into the executable is not done.
  Until it is, domains whose leaves need new checkers are covered only by the
  extended-authority theorems. Domains discharged by the six built-ins (e.g. the ML witness)
  are covered on the production path today.
* **No end-to-end accepted archive.** No concrete signed archive accepted by the authority is
  constructed in this work. Non-vacuity is shown at the levels of checker run, obligation
  checker and graph.
* **External validators.** Their meaning (`hExt`) is a hypothesis, as before. No proposer or
  graph assumption is introduced.
* **Natural-language intent.** No theorem can certify that a decoded claim matches what a human
  intended. Grounding is to the signed predicate, not to informal text.
* **Witness scope.** The witnesses prove exactly their stated byte-level properties. The
  AI-safety witness proves a bounded trace invariant of committed traces, not "global AI
  safety". The biology witness proves nothing about real proteins.

---

## 5. Is it genuinely domain-independent?

* `Domain`, `DomainAdapter`, `AdapterSound`, `Graph`, `Checker`, `Strategy` and `Pipeline`
  quantify over arbitrary types. `ClaimGraph` and `WorkflowRefinement` depend only on Lean core.
* `domain_adapter_sound` and the flagship theorems are proved once, with no domain-specific
  case analysis.
* All three witnesses obtain their archive theorem as a one-line application of the generic
  flagship (`bio_archive_sound`, `ai_archive_sound`, `ml_archive_sound`):
  * they use different claim types, IR shapes (binary split, data-dependent n-ary split, fixed
    3-way split) and checker mechanisms (two new certified checkers, one new certified checker,
    one existing built-in);
  * the domain-specific work is confined to each adapter's `AdapterSound` proof;
  * that proof reduces, via `registry_valid`, to the domain checker's own soundness theorem.
* The only PCS-specific choice in the interface is that leaves are certificate evidence objects
  and the world is a function of the artifact table. This reflects what PCS actually signs.

---

## 6. How to add a new domain (e.g. computational biology or AI safety)

1. Define `D : Domain`: native claims, world, and `Holds`.
2. For each new check type, write a decidable test and its soundness proof, and wrap them with
   `specChecker tag parse test Sem hsound` (`Witnesses/Registry.lean`). Built-in checks can be
   reused directly (as in `MLEval`).
3. Define `A : DomainAdapter D`:
   * `decode` for the certificate predicate;
   * `compile` to a root IR node. Reject vacuous claims here;
   * `world` from the artifact table;
   * `sem`;
   * `leafCheck`, which decodes the check spec into the IR node it certifies;
   * `ruleCheck` for the decompositions you allow.
4. Prove `AdapterSound A (AuthorityValid (registry ks) ExtHolds)` for every registry `ks` that
   contains your checkers. Use `registry_valid` for `leaf_sound`. For a built-ins-only domain,
   prove `AdapterSound A (BuiltinHolds ExtHolds)` instead.
5. Apply `pcs_generic_domain_archive_acceptance_sound_certified` (or `…_builtin` for the
   production path). You get `D.Holds (A.world r.table) c` from a raw signed archive, with
   `NoForgery` as the only hypothesis. Theorem 3 then applies automatically to AI-proposed
   decompositions and repairs.

---

## 7. Commands and results

```
lake build                                   # default targets: PCS, pcs-lean-authority
# → Build completed successfully (157 jobs).
#   The only warning is the pre-existing `unused variable hs` in PCS/V2/SHA256.lean.
#   GenericAudit prints axioms ⊆ {propext, Classical.choice, Quot.sound} for all 56 results.

rg -n "\bsorry\b|\badmit\b|^\s*axiom |\bunsafe\b|@\[extern|\bextern\b|native_decide|implemented_by" \
   --glob '*.lean' PCS PCS.lean PCSAuthority.lean
# → no matches
```

The Mathlib-based `real/` bridge is not part of this lakefile. It was not modified and not
rebuilt.
