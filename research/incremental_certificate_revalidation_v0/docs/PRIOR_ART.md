# Prior art for PCS incremental certificate revalidation

## Scope and standard of comparison

This survey asks a narrow question: what is already known about reusing a
previously accepted result after a computation graph changes, and what—if
anything—is distinctive about doing so for proof-carrying scientific
computations?

The PCS Incremental Certificate Revalidation (PCS ICR) target considered here
has:

- a finite computation DAG;
- a certificate and output at each node;
- an exact obligation key
  `(id, op, policy, version, evidence, depOutputs)`;
- three deliberately separate judgments:
  **lookup**, **eligibility** (exact key equality), and **authority** (the entry
  was previously accepted under the applicable trust policy);
- a declared change set whose affected region is downstream reachability in
  the **updated** graph; and
- a Lean 4 result of the form
  `IncrementalAccept premises -> FreshValid`.

The intended optimization is to avoid expensive local certificate checks at
unaffected nodes while obtaining the same node-wise validity proposition as a
fresh verification.

Three notions that are often conflated must be kept separate in the literature:

1. **From-scratch consistency:** an incremental computation returns the same
   value as re-executing the program.
2. **Cache identity/integrity:** a retrieved artifact is the artifact associated
   with a particular input description or digest.
3. **Certificate authority:** an artifact is entitled to discharge a logical
   obligation under a named policy and checker version.

Self-adjusting computation is strongest on (1), content-addressed systems on
(2), and proof-carrying code on the local form of (3). PCS ICR is best viewed as
an attempt to compose all three for an evolving certificate DAG. It should not
claim any one of these ingredients as new.

### Reading the comparison

For each strong prior system, “TCB” means the assumptions whose failure can
invalidate the stated guarantee, not merely the smallest executable kernel.
“Dynamic graph” distinguishes systems that can discover or replace dependency
edges while executing from those that only schedule a predeclared DAG.
“Verified” is reserved for machine-checked results; a mathematical proof in a
paper is described as such.

## Summary comparison

| Work or system | Principal guarantee | Graph/change model | Reuse unit | Formal status | Closest connection to PCS ICR |
|---|---|---|---|---|---|
| Acar et al., adaptive functional programming | Change propagation agrees with ordinary evaluation | Dynamic dependence graph updated during re-execution | Recorded reads and reader closures | Paper proof for a core language | Ancestor of affected-region re-execution |
| Adapton | From-scratch consistency for demand-driven incremental computation | Mutable demanded-computation graph | Memoized thunks/traces | Paper proof for a core calculus | Strong semantic baseline for incremental correctness |
| Build Systems à la Carte | Final store is consistent with task semantics | Static or dynamic task dependencies | Task values/traces | Executable mathematical framework; paper argument | Abstract analogue of fresh-result correspondence |
| Shake | Correct, minimal practical rebuilding with dynamic dependencies | Dependencies declared while rules run | Rule results and dependency traces | Algorithmic correctness argument, not machine-checked | Practical updated-dependency tracking |
| pluto | Sound and optimal rebuilding under explicit assumptions | Dynamic required/provided-file and builder graph | Build units and summaries | Formal paper proof, not machine-checked | Closest build-system precedent |
| Bazel | Conditional reuse of action outputs with hermetic action keys | Analyzed action DAG; declared inputs | Whole action result in CAS | Engineering contract, not a theorem | Exact obligation keys and environmental completeness |
| Proof-carrying code | Untrusted code accepted only with a checker-validated policy proof | Code plus verification-condition/proof structure | Proof object | Formal adequacy arguments | Certificates, policy, and a small consumer-side checker |
| Coq STM / Isabelle PIDE | Sound kernel checking with asynchronous, versioned document processing | Edited document DAG/version family | Proof tasks, states, compiled artifacts | Kernel soundness plus system design; no general ICR theorem | Real proof-assistant incremental execution |
| Authenticated data structures | Query answer authenticated against a trusted digest | Dynamically updated data structure | Authentication paths/proofs | Cryptographic security arguments | Explicit authority and anti-tampering, but not semantic validity |
| Nix / Bazel CAS / Docker layers | Artifact identity and safe reuse conditional on complete inputs | Build/action/layer dependency graphs | Store objects, actions, layers | Engineering design | Content identity is not acceptance authority |
| CompCert | Compiler output preserves source semantics | Fixed compiler-pass pipeline | Not principally a cache | Machine-checked compiler proof | Model for end-to-end refinement, not direct cache prior art |
| Nextflow / Snakemake | Reproducible execution and resumable/cross-workflow caching | Scientific workflow DAG/dataflow | Task outputs | Engineering guarantees, no semantic proof | Direct application domain; lacks certificate authority |

## 1. Self-adjusting and incremental computation

### 1.1 Acar, Blelloch, and Harper: adaptive functional programming

**Primary sources.** Acar, Blelloch, and Harper introduced adaptive functional
programming at POPL 2002 [1] and developed the account further in TOPLAS in
2006 [2].

**Core guarantee.** The formal change-propagation algorithm is proved correct
with respect to the dynamic semantics of the adaptive language AFL: after input
changes, propagation produces the result that reevaluation should produce.
This is a genuine from-scratch semantic result, not just an argument that a
cache key is likely to be unchanged.

**Mathematical model.** AFL is a call-by-value functional language extended
with modifiables, writes, and reads. Evaluation records a trace; the
implementation uses a dynamic dependence graph (DDG). A node represents a
modifiable and an edge represents a read, annotated with the reader closure and
ordering information. A modal type system constrains use of the adaptive
operations.

**Execution model.** When a modifiable changes, the runtime finds affected reads,
reexecutes their reader closures in timestamp order, and repairs both values and
the DDG. Reexecution can take a different conditional branch. The algorithm
therefore inserts newly observed reads and removes obsolete nested reads. This
last point is important for PCS: an old graph is not a complete invalidation
topology after an edit that introduces a new dependency.

**TCB and invalidation assumptions.** Correctness depends on all relevant
mutable inputs entering through the adaptive interface, on the operational
semantics accurately modeling execution, and on correct trace/DDG maintenance.
The paper proves properties of the formal algorithm. The ML library and runtime
remain implementation code and enforce some restrictions dynamically rather
than by AFL's static type system. Hidden I/O, undeclared mutation, or a bad
foreign function escapes the model.

**Reuse mechanism.** The system reuses prior computation traces and values,
reexecuting only recorded readers invalidated by changed modifiables. It does
not reuse a proof that an independently supplied certificate satisfied a
versioned policy.

**Dynamic graph support.** Strong. Dependencies are generated by execution and
are repaired as control flow changes.

**Performance evidence.** The POPL work gives a general adaptation-time bound
and an adaptive Quicksort whose expected update time for insertion is
logarithmic rather than a full sort. The papers also report an ML
implementation. These results show that dependency maintenance can pay off,
but they do not measure proof-checking workloads.

**Limitations relative to PCS ICR.**

- The result being reused is a computed value, not an externally meaningful
  certificate with separate authority.
- Program semantics determines dependency completeness; there is no analogue
  of an adversarially incomplete scientific change declaration.
- Policy, checker version, admitted evidence identity, and prior acceptance are
  not separate dimensions.
- The proof is not a Lean-checked theorem about the production implementation.

**Relationship to PCS ICR.** The DDG repair story is foundational prior art for
updated-graph invalidation. PCS's downstream closure is a simpler conservative
special case for an explicit DAG. The potentially distinctive part is not
reachability invalidation, but connecting that invalidation to exact
certificate obligations and explicit authority in a machine-checked theorem.

### 1.2 Adapton

Hammer, Phang, Hicks, and Foster's Adapton [3] adds demand-driven computation
and composability. Its core calculus uses a demanded computation graph and
separates incremental computations from observers.

**Core guarantee and model.** The incremental semantics reuses and locally
patches traces from prior knowledge. The paper proves **from-scratch
consistency**: a patched result agrees with ordinary recomputation. This is a
particularly clear predecessor to PCS's desired “incremental acceptance implies
fresh acceptance” shape.

**Execution, TCB, and invalidation.** The OCaml library memoizes thunks and
dependency edges; mutation dirties dependent nodes and demand triggers repair.
Correctness assumes mutation and dependencies pass through the Adapton
interface and that the implementation realizes the core semantics. As with
self-adjusting computation generally, untracked effects defeat the guarantee.

**Proof reuse and dynamic graphs.** Adapton reuses computation thunks and
traces, not proof certificates. The demanded graph evolves as observations and
control flow evolve. Named variants of Adapton later made node correspondence
across runs explicit; this reinforces that stable identity is a substantive
part of reuse, not a free consequence of memoization.

**Performance evidence.** On the paper's microbenchmarks, traditional
incremental computation achieved roughly 2–20x over naive recomputation in
some lazy cases, while Adapton achieved roughly 7–2000x; the paper also reports
cases where a traditional incremental approach slowed down while Adapton
substantially sped up. These are benchmark-specific and should not be
generalized to certificate checking.

**Relationship and limitation.** Adapton already establishes the broad
semantic pattern of reusing prior graph work while matching a fresh run. It
does not model a cache entry that is structurally eligible but unauthorized, a
policy/version-sensitive proof obligation, or an untrusted certificate
producer. PCS must demonstrate that these additions are substantive rather
than a relabeling of from-scratch consistency.

## 2. Correct and incremental build systems

### 2.1 Build Systems à la Carte

Mokhov, Mitchell, and Peyton Jones [4] give a precise, executable framework for
classifying build systems. It is a theory and design space, not itself a
production build engine.

**Core guarantee.** Their correctness definition says that (i) input keys are
unchanged by the build and (ii) every reachable non-input key in the final
store equals the result of recomputing its task against that final store. This
is an extensional final-store consistency property. The framework assumes
acyclic task descriptions for the main result and notes that nondeterministic
tasks and some cloud-build models need adjusted definitions.

**Mathematical model.** The central abstractions are keys, values, a store,
tasks parameterized by a dependency-fetching interface, a build algorithm, and
optional build metadata. Applicative tasks expose static dependencies; monadic
tasks can discover dependencies dynamically. Rebuild strategies include dirty
bits, timestamps, shallow traces, and constructive traces. “Early cutoff”
skips downstream work when a rebuilt dependency's value did not change.

**Execution model and reuse.** A scheduler decides what to build; a rebuilder
uses persistent metadata to decide whether a key is current. Reuse can be based
on dependency values, hashes, timestamps, or cached constructive results.

**TCB and invalidation assumptions.** Correctness is conditional on task
descriptions and the store accurately representing all inputs and effects.
Trace-based systems require valid traces; deterministic-task assumptions
matter for constructive caches. The framework's Haskell presentation is
executable, but its correctness discussion is not a machine-checked proof of a
production engine.

**Dynamic graph support.** Explicitly modeled. Monadic tasks may choose later
dependencies based on earlier dependency values. Dynamic dependencies make
minimal rebuilding harder because discovering the graph can itself require
execution.

**Performance evidence.** The paper's contribution is comparative theory and
executable models, not a controlled benchmark claiming one implementation's
speedup.

**Limitations and relationship to PCS ICR.** The final-store consistency
definition is close in logical shape to `FreshValid`, and its separation of
scheduler from rebuilder resembles PCS's separation of affectedness from reuse
eligibility. It does not distinguish a value found under a matching key from a
logically authoritative certificate. PCS should cite this work when presenting
its abstract graph/cache model and should avoid claiming that a “fresh
equivalence” theorem is unprecedented.

### 2.2 Shake

Mitchell's Shake [5] is a practical Haskell build library whose key feature is
that a running rule may discover and declare additional dependencies.

**Core guarantee and model.** Shake aims to execute enough rules that all
requested results are correct while skipping every rule that can safely be
skipped. The paper describes a status-transition algorithm for checking and
building keys. Its persistent database records each result's observed state and
the states of dependencies from the prior run.

**Execution model.** Rules call `need` during execution, so generated files can
determine later dependencies. Rules may operate over non-file values and can
have multiple outputs. Independent rules run in parallel.

**TCB and invalidation assumptions.** A rule must declare every dependency it
reads and every relevant non-file input. The equality or metadata oracle used
for a dependency must be sound for the aspect on which the action depends.
Undeclared filesystem reads, clocks, network responses, environment variables,
and tool versions can make a build stale. The paper gives a correctness
argument and implementation design, not a machine-checked proof of Shake.

**Reuse and dynamic graph support.** Shake reuses whole rule results when the
stored dependency observations still match. Dynamic dependencies are
first-class, including dependencies discovered from generated files. This is
stronger operational support than computing downstream closure on a wholly
supplied updated graph.

**Performance evidence.** The paper reports production use on a build with
more than a million lines of source and a million lines of generated code and
over 30,000 build objects. Replacing Make reportedly made the build description
ten times shorter and builds about twice as fast. That case study supports
practicality, not a proof-checking cost model.

**Relationship to PCS ICR.** Shake establishes that dynamic dependency
discovery and trace validation are standard build-system techniques. PCS's
stronger intended claim is that reusing an *accepted certificate* under an
exact logical obligation is formally sufficient for fresh validity. Shake has
no authority bit, policy transition rule, or proof-kernel theorem.

### 2.3 pluto: a sound and optimal incremental build system

Erdweg, Lichter, and Weiel's pluto [6] is the closest single build-system
precedent and must be treated as such.

**Core guarantee.** The paper defines soundness as returning build units that
are totally consistent with the final filesystem. It also proves an optimality
property: subject to its ordering of objectives, the algorithm minimizes
builder executions and internal-consistency checks. These are mathematical
proofs in the paper, not machine-checked proofs of the Java implementation.

**Mathematical model.** A filesystem state is mapped through builders to build
units. A build unit records its builder and input, required files or other
build units, provided files, and stamps. Internal consistency checks the unit
against its own summary; total consistency recursively includes its build
requirements.

**Execution model.** Builders dynamically call `require`, `provide`, and request
other builders. Dependency analysis and builder execution are interleaved.
pluto supports timestamps, content hashes, whole contents, existence tests,
and domain-specific stamps. It automatically records a metadependency on a
builder's implementation. It can detect cycles and delegate them to explicit
cycle handlers.

**TCB and invalidation assumptions.** The soundness theorem assumes each
builder returns an internally consistent unit, builders satisfy a stability
condition needed for optimality, and the build system has exclusive access to
relevant files during a build. A custom stamper is trusted to retain every
aspect of a file that can affect the builder. The Java runtime, builder API
instrumentation, filesystem observations, and implementation are outside the
paper proof.

**Reuse mechanism.** A prior build unit is reused when its stored requirements,
products, builder metadata, and selected stamps remain consistent. Otherwise,
the interleaved traversal rebuilds the necessary unit and repairs the graph.

**Dynamic graph support.** Strong. Requirements and products are discovered at
runtime, and builder dependencies can be cyclic under a handler. A changed
builder may reveal a different graph.

**Performance evidence.** In the Spoofax case study, a clean pluto build took
31.3 seconds. A no-change rebuild took 0.027 seconds (reported 1160x ratio to
clean); representative edits took 1.2–16.0 seconds (1.9–26.1x). The study used
23 builders, 108 supplied files, and 243 generated files. These numbers are a
single application case study and compare incremental runs to pluto's clean
run, not certificate checking to full verification.

**Limitations relative to PCS ICR.**

- “Consistent output” is not “valid certificate under policy P.”
- A custom stamp can deliberately ignore content; its adequacy is an assumption,
  whereas PCS's exact key is intended to avoid projection-based eligibility.
- There is no distinction between obtaining a prior unit and establishing that
  a trusted verifier accepted a proof object.
- The formal proof does not refine the production Java implementation.

**Relationship to PCS ICR.** pluto already combines dynamic graph repair,
fine-grained dependency identity, sound incremental rebuilding, and explicit
assumptions. PCS novelty cannot rest on those features alone. The plausible
advance is a machine-checked composition theorem for certificate validity that
adds authority, evidence, policy, and checker-version sensitivity.

### 2.4 Bazel and hermetic action caching

Bazel's official remote-caching and hermeticity documentation [7, 8] is an
important industrial reference, although it is not a peer-reviewed formal
correctness proof.

**Core guarantee and model.** Bazel divides a configured build into actions.
An action has a command, arguments, declared inputs and tools, environment, and
declared outputs. The remote cache maps an action digest to result metadata and
stores output blobs in a content-addressable store. Reuse is valid only under
the engineering contract that these fields completely determine the action
result.

**Execution and reuse.** Bazel analyzes targets into an action graph, checks
local and remote caches, executes misses, and uploads results. Hermetic builds
pin tools and dependencies and isolate actions from the host. Input contents
are represented by digests. Tools must be declared as executable inputs;
selected environment variables are part of the action definition.

**TCB and invalidation assumptions.** Rules must declare every semantic input;
actions must be deterministic enough for sharing; sandboxing and remote
execution must enforce the declared boundary; digests must be collision
resistant; and a remote cache must not be allowed to inject unauthenticated
results beyond its trust policy. Undeclared `/usr/bin` tools, network access,
host state, or omitted environment variables break hermeticity.

**Dynamic graph support.** Bazel's principal action graph is produced during
analysis before action execution. Some language rules perform input discovery,
but arbitrary execution-driven graph mutation is not the basic model. A new
dependency must be visible to analysis or a supported discovery mechanism.

**Performance evidence.** Remote caching is deployed specifically to avoid
repeated action execution across users and machines, but the cited
documentation does not provide a controlled universal speedup. Any performance
claim is workload and cache-hit dependent.

**Relationship to PCS ICR.** A Bazel action key is an industrial analogue of an
obligation key. Bazel also illustrates why exact-looking keys are only as
complete as the rule boundary. PCS adds a semantic checker and explicit prior
acceptance. Conversely, Bazel's mature hermetic execution and distributed-cache
security expose deployment concerns that the local PCS v0 trust model does not
solve.

## 3. Proof-carrying code and proof reuse

### 3.1 Necula's proof-carrying code

Necula's proof-carrying code (PCC) [9] establishes the basic producer/consumer
architecture for proof-bearing artifacts.

**Core guarantee.** An untrusted producer supplies machine code and a proof that
the code satisfies a consumer-defined safety policy. The consumer generates or
checks the relevant verification condition and validates the proof. Acceptance
therefore depends on a small checker rather than trust in the producer, without
requiring an online external authority.

**Mathematical and execution model.** The policy is represented as logical
predicates over machine states. A verification-condition generator connects
the concrete program to those predicates, and a proof representation witnesses
the resulting formula. The 1997 paper gives adequacy arguments for the policy,
proof representation, and validator in case studies.

**TCB.** The consumer trusts the safety policy, machine semantics, loader and
decoder assumptions, verification-condition generator, proof checker, and
their implementations. PCC minimizes producer trust; it does not remove the
need to trust that the checked policy is the intended one.

**Invalidation and reuse.** Classical PCC checks a code/proof pair presented to
the consumer. It does not supply a general algorithm for reusing an earlier
acceptance after code, policy, dependencies, or checker versions change.
Proof compression and efficient validation reduce checking cost but are not
the same as incremental cache reuse.

**Dynamic graph and performance evidence.** PCC is not primarily a dynamic
workflow-graph system. The paper reports feasibility through safe
assembly-language extensions and packet-filter case studies, but its main
claim is assurance and cheap consumer validation, not a graph-incremental
speedup.

**Relationship to PCS ICR.** PCC is direct prior art for node certificates,
consumer-defined policy, and the separation of an untrusted producer from a
trusted checker. PCS ICR begins after a PCC-like acceptance and asks when that
acceptance may be reused. Its exact key should be understood as binding the
certificate to the full verification condition; its authority witness records
that the PCC consumer actually accepted it.

### 3.2 Incremental theorem-prover document processing

#### Coq's State Transaction Machine

Barras, Tankink, and Tassi [10] redesigned Coq document processing around a
State Transaction Machine (STM).

**Core guarantee and model.** The document is represented as a DAG whose nodes
are system states and whose command-labeled edges are atomic transactions.
Static analysis separates opaque proofs into independently schedulable tasks.
Logical soundness still comes from Coq's kernel checking proof terms; the STM
is principally a scheduling and responsiveness architecture, not a published
general theorem that arbitrary cached certificates remain fresh.

**Execution and reuse.** The system can process commands out of order,
prioritize the visible document region, postpone opaque proof checking, and
use worker processes. Because later developments use the statement of an
opaque theorem rather than reducing its proof term, proof construction/checking
can be scheduled separately.

**TCB and invalidation assumptions.** The Coq kernel and logical environment
remain central. Parsing/classification, transaction boundaries, marshalling,
worker coordination, dependency extraction, and compiled artifact versioning
must not cause an unchecked theorem to be treated as checked. The paper's
architecture preserves kernel checking; it is not a machine-checked
refinement proof of the STM implementation.

**Dynamic graph support.** The user edits document versions and the STM builds
and revises a command DAG. This is dynamic at document granularity, though the
logical dependencies of a command are governed by Coq's environment and
opacity rules.

**Performance evidence.** On the full Odd Order development, the paper reports
about tenfold lower feedback latency and about fourfold faster complete
checking on twelve cores. Its detailed example reduces latency from hours to
minutes by postponing opaque proofs; this is scheduling and parallelism as well
as reuse.

**Relationship to PCS ICR.** Coq STM demonstrates that real proof systems
already use DAG structure, versioned documents, and delayed proof checking.
PCS is narrower but potentially more explicit: it states a reusable node
obligation and authority condition and proves a graph-level fresh-validity
implication.

#### Isabelle/PIDE

Wenzel's Isabelle/PIDE [11] replaces the sequential REPL with asynchronous
processing over a family of immutable document versions. The editor sends
edits; the prover schedules checking and asynchronous tools against the
appropriate versions.

The key precedent is the versioned, persistent document model and continuous
rechecking, not a content-addressed proof cache theorem. Sound theorem
acceptance remains rooted in Isabelle's LCF-style kernel architecture.
PIDE's execution model is dynamic and cancellation-aware, but tool output and
markup need not carry theorem authority. The cited paper focuses on interaction
and multicore utilization rather than a cache-invalidation theorem or a
controlled incremental speedup table.

**PCS relationship.** PIDE warns against equating responsive incremental UI
processing with verified certificate reuse. PCS should claim the latter only
where the authority and fresh-validity path is formalized.

### 3.3 Proof reuse in deductive verification

Beckert and Klebanov [12] reuse KeY proof steps for changed Java verification
problems. A similarity measure matches locations, formulas, terms, and programs;
rule applications are replayed one at a time. Reuse may stop at a changed
region and resume later in an unaffected region.

This work is important because it distinguishes **proof-search reuse** from
**proof-checking reuse**. Replayed rule applications remain subject to the
deductive calculus; approximate similarity is a search heuristic, not
authority to accept an unmatched old proof. The method supports evolving
programs but does not provide PCS's exact obligation-key/cache-authority model.
Its performance evidence is an implementation in KeY and case experience; the
cited paper does not establish a general machine-checked graph-revalidation
theorem.

For PCS, this is adjacent rather than substitutive prior art. PCS ICR avoids
redoing an expensive local check only when exact eligibility and prior
authority hold; KeY proof reuse tries to accelerate construction of a new proof
even under merely similar obligations.

## 4. Authenticated data structures

Merkle's hash-tree construction [13] and Tamassia's authenticated-data-structure
model [14] separate data possession from trusted answer authentication.

**Core guarantee.** A trusted source commits to a current data structure with a
signed digest. An untrusted responder returns a query answer plus an
authentication proof. A user verifies the proof against the authenticated
digest. Subject to signature unforgeability and collision resistance, the
responder cannot substitute an answer inconsistent with the committed state.

**Mathematical model.** There are three parties—source, responder, and user—a
structured collection, update and query algorithms, a digest, and proofs. In a
Merkle tree, leaves commit to elements and each internal hash commits to its
children. A membership path supplies sibling hashes needed to reconstruct the
root.

**Execution, reuse, and dynamic support.** The responder reuses a maintained
structure and supplies logarithmic authentication paths for balanced trees.
Dynamic authenticated dictionaries support logarithmic updates, proof sizes,
and verification under standard constructions. More general work authenticates
graph queries, but “graph” here is authenticated data, not necessarily a
computation-dependency graph.

**TCB and assumptions.** The user trusts the source's signing key and current
digest, the verifier, canonical serialization, cryptographic assumptions, and
freshness/rollback mechanism (often a timestamp or version). Authentication
does not prove that source data is scientifically true or that a computation
was semantically correct.

**Performance evidence.** The classic balanced-tree results give
`O(log n)` proof size and verification/query cost with `O(n)` responder
storage; dynamic variants can also provide `O(log n)` update cost. These are
asymptotic authentication results, not proof-checker benchmarks.

**Relationship to PCS ICR.** Authenticated data structures provide the cleanest
prior separation between **finding bytes** and **having authority to rely on
them**. A Merkle proof can authenticate a cached certificate and its key, but
cannot show that the certificate passed PCS's local checker. PCS's
`priorAccepted` or `FreshWitness` plays a semantic-authority role analogous to,
but stronger and different from, a signed current digest. A production PCS
cache could compose both layers: cryptographic origin/integrity outside, logical
acceptance inside.

## 5. Content-addressed and memoized computation

### 5.1 Nix

Dolstra, de Jonge, and Visser's Nix paper [15] uses hash-derived store paths to
isolate component variants and make source and binary deployment safer.

**Core guarantee and model.** A Nix derivation records a builder, platform,
declared inputs, and environment bindings. Dependencies are built first and
store objects occupy unique paths derived from their build description in the
traditional input-addressed model. This prevents unrelated package variants
from overwriting one another and permits transparent binary substitution.

**Execution, reuse, and invalidation.** If a required derivation's output is
already in the store or available from a substituter, Nix reuses it. A changed
derivation input changes the input-addressed store path. Modern Nix also has
content-addressed modes, but a content digest still establishes what bytes were
received, not by itself that those bytes are the correct result of a requested
derivation.

**TCB and assumptions.** Derivations must declare all semantically relevant
inputs; sandboxing must constrain hidden host effects; builders should be
deterministic if independent reproduction is expected; hashing and
serialization must be sound. For traditional binary caches, configured public
keys explicitly authorize substituters. Nix documentation warns that a trusted
cache key can introduce arbitrary signed store objects [16]. Thus identity,
integrity, and producer authority remain distinct.

**Dynamic graph support.** The derivation dependency graph is declarative.
Runtime references may be scanned for deployment and garbage-collection
purposes, but arbitrary hidden runtime dependencies are not a sound basis for
build reuse.

**Performance evidence.** The 2004 paper motivates binary deployment as an
optimization over source deployment and describes practical sharing, but does
not provide a proof-checking-specific benchmark or a universal cache speedup.

**Relationship to PCS ICR.** Nix strongly supports PCS's three-way distinction:
a store-path lookup is not proof of correct production; input or content
identity is not authorization; a trusted signature is authorization by a
builder, not mathematical validation. PCS's exact obligation key resembles a
derivation identity, while prior acceptance resembles a semantic realization
record whose issuer is the verifier rather than merely the builder.

### 5.2 Docker layers and memoization

Docker image layers are identified by content digests and build caches reuse
earlier instruction results [17]. `COPY`/`ADD` inputs participate in cache
checks, while a `RUN` instruction is principally matched by command text and is
not automatically invalidated because a remote package repository changed.
Once a layer misses, later layers are rebuilt because they depend on the
changed filesystem state.

This is useful counter-prior-art: downstream invalidation and content-addressed
storage are commonplace, yet Docker intentionally offers only a build-cache
contract. It does not establish semantic correctness, scientific
reproducibility, or proof authority. PCS should not use “content addressed” as
a synonym for “verified.”

Ordinary function memoization is an even simpler ancestor: reuse is sound when
the key contains all arguments and the function is referentially transparent.
PCS's obligation key is a domain-specific memoization key, but certificates,
policy changes, evidence provenance, and prior authority make the proof
obligation richer than pure function memoization.

## 6. Verified compilers and certified execution

Leroy's CompCert [18] is relevant as a standard for end-to-end mechanized
assurance, not as direct incremental-cache prior art.

**Core guarantee and model.** CompCert's Coq development proves semantic
preservation from a substantial C source language through compiler passes to
assembly: observable target behaviors correspond to permitted source
behaviors, subject to the theorem's hypotheses.

**Execution model and TCB.** Compiler passes are specified and proved in Coq,
then extracted for execution. The TCB includes the Coq kernel and logical
definitions, extraction and host toolchain assumptions, source/target semantic
adequacy, and unverified surrounding tools such as preprocessing, assembling,
and linking where applicable. Later TCB analyses make these boundaries
explicit.

**Caching and dynamic graphs.** The canonical CompCert result is not a theorem
about caching compiler-pass results after graph edits. A build system may cache
CompCert outputs under exact inputs, but that adds the build system's
dependency-completeness and cache-integrity assumptions. No “CompCert-style
caching” claim should be attributed to the cited CompCert paper.

**Performance evidence and limitation.** CompCert demonstrates that a realistic
optimizing compiler can be verified while producing useful code, but this does
not quantify incremental certificate-checking speedups.

**Relationship to PCS ICR.** The methodological lesson is refinement coverage.
A Lean theorem about abstract `IncrementalAccept` premises is analogous to one
verified pass in a larger chain. To reach a CompCert-level claim, PCS must prove
that the executable invalidator, decoder, cache, and checker establish those
premises. Differential tests are valuable evidence but not a refinement proof.

## 7. Scientific workflow reproducibility and caching

### 7.1 Nextflow

Di Tommaso et al. [19] present Nextflow as a dataflow-based workflow system for
portable and reproducible computational pipelines, with containers and
distributed execution. Current official documentation specifies its resume
cache [20].

**Core guarantee and model.** A workflow consists of processes connected by
data channels. For resume, Nextflow computes a task hash over metadata including
the session, task identity, container or software environment, task inputs,
script, referenced globals, bundled scripts, and related execution properties.
A hit is reusable only if its outputs still exist and the prior exit status is
acceptable.

**Execution, TCB, and invalidation.** Processes execute in isolated work
directories and may run on local, HPC, cloud, or container backends.
Reproducibility depends on complete hashing, immutable/pinned inputs and
containers, deterministic or otherwise intentionally stable tools, and storage
integrity. External services, mutable tags, undeclared files, hardware-sensitive
numerics, and nondeterminism can escape a nominally equal task hash.

**Reuse and dynamic graph support.** Task outputs are reused whole. Nextflow's
dataflow execution can instantiate tasks dynamically as channel values arrive,
but its resume mechanism is a task-identity cache, not a theorem that
downstream closure on a revised scientific DAG is complete.

**Performance evidence.** The 2017 paper emphasizes scaling, portability,
containerization, and practical pipelines. The cited paper and cache
documentation do not establish a formal soundness theorem or a universal
resume speedup.

**Relationship to PCS ICR.** Nextflow is direct domain prior art for exact-ish
task fingerprints and expensive scientific workflow reuse. It records
successful execution, not validity of a proof certificate under a formal
policy. PCS can add value by making that semantic distinction explicit.

### 7.2 Snakemake

Köster and Rahmann [21] define a workflow DAG whose nodes are jobs and whose
edges connect produced files to consuming jobs. Later Snakemake work [22]
describes provenance and between-workflow caching using recursively composed
hashes over code, parameters, software, raw inputs, and upstream jobs.

**Core guarantee and model.** Snakemake schedules the job DAG and ordinarily
reruns jobs whose inputs or provenance indicate staleness. Its cross-workflow
cache uses a Merkle-tree-like job hash to identify prior outputs. The
documentation explicitly conditions meaningful caching on deterministic result
generation.

**TCB, invalidation, and authority.** Rules must expose all parameters and
inputs through captured mechanisms; tools and environments must be pinned;
cache storage and hash functions must be trusted. Some direct uses of globals
or configuration are restricted precisely because they would not be captured
in the cache key. A cache hit says that an output was generated under matching
recorded provenance, not that a scientific claim is true or a proof checker
accepted it.

**Dynamic graph and performance.** Snakemake generates a concrete job DAG from
rules and wildcard bindings and can checkpoint to reevaluate graph structure
after data-dependent steps. Its publications demonstrate portability and
scalability, but the cited sources do not provide a formal fresh-equivalence
theorem for cache reuse.

**Relationship to PCS ICR.** Snakemake is especially close to PCS's application
setting and recursively dependency-sensitive keys. PCS's contribution would
be the added certificate semantics, authority boundary, and mechanized
fresh-validity theorem—not DAG execution, Merkle-style keys, or provenance
caching themselves.

## 8. Cross-cutting conclusions

### What is established prior art

The following should be treated as established:

1. **Downstream invalidation.** Recomputing dependents of changed inputs is
   basic incremental computation and build-system practice.
2. **Graph repair under changing dependencies.** Acar-style DDGs, Shake, and
   pluto already handle dependencies discovered during execution. Using the
   updated graph when edges change is necessary, but not itself novel.
3. **From-scratch consistency.** Self-adjusting computation and Adapton prove
   that incrementally repaired results agree with fresh evaluation in formal
   core languages.
4. **Exact fingerprints and hermeticity.** Bazel, Nix, Snakemake, and Nextflow
   bind reuse to commands, inputs, dependency outputs, environments, and tools.
   Their failures show that omitted inputs are the central hazard.
5. **Proof-bearing artifacts.** PCC establishes that an untrusted producer can
   supply a certificate checked against a consumer policy.
6. **Authenticated reuse.** Merkle structures and signed binary caches
   distinguish artifact integrity/origin from computation and semantic truth.
7. **Incremental proof environments.** Coq and Isabelle process changing proof
   documents as versioned dependency structures and exploit task independence.
8. **The bookkeeping/performance tradeoff.** Prior work repeatedly finds that
   incremental machinery wins only when avoided work is expensive and changes
   are sufficiently sparse. PCS's own cheap-operation slowdown is therefore
   expected, not anomalous.

### Where PCS ICR may make a real contribution

A defensible differentiation is the **verified composition** of these ideas for
certificate revalidation:

- an obligation identity that includes node semantics, policy, checker version,
  evidence identity, and resolved dependency outputs;
- a formal distinction between locating an entry, proving it matches the
  current obligation, and establishing authority from prior acceptance;
- an affected relation over the revised DAG, including newly introduced edges;
- a conservative handling of incomplete change declarations and new nodes;
- a theorem deriving node-wise fresh validity from rechecks of affected nodes
  and authoritative eligible reuse of unaffected nodes; and
- an end-to-end refinement argument connecting the executable invalidator and
  cache implementation to that theorem.

No surveyed system appears to present exactly that combination for scientific
certificate DAGs. That is a combination claim, not a claim that any individual
ingredient is new.

### Required honesty about the present theorem boundary

The logical strength of `IncrementalAccept -> FreshValid` depends on what
`IncrementalAccept` assumes. If it already assumes, for every affected node,
that the node checks and, for every unaffected node, that an authoritative
eligible entry checks, then the final theorem is a useful composition lemma
but not yet an algorithm-correctness theorem. Change-set completeness and
updated-graph reachability matter operationally to *constructing* those
premises; after the per-node premises are assumed, they may be logically
redundant in the final case split.

Accordingly, the strongest future claim requires a proved chain such as:

```
serialized prior state + updated graph + declared changes
        |
        v
executable incremental verifier returns accept
        |
        v  (refinement / correspondence theorem)
Lean IncrementalAccept premises
        |
        v  (kernel-checked composition theorem)
FreshValid on the updated graph
```

Without the first implication, the appropriate statement is “machine-checked
soundness of the abstract acceptance premises, with an unverified executable
refinement boundary,” not “a fully verified incremental verifier.” This
distinction mirrors the implementation gaps in self-adjusting computation,
pluto, and build systems, and the end-to-end standard set by CompCert.

## PCS differentiation checklist

PCS ICR is more than a reimplementation of known ideas only if the answer is
“yes” to most of the following:

- [ ] Is authority represented and enforced separately from cache lookup and
      key equality?
- [ ] Does the obligation key cover every semantic input, including policy,
      checker version, admitted evidence, and ordered dependency outputs?
- [ ] Is affectedness computed on the updated graph, with a proved treatment of
      new edges, removed edges, new nodes, and complete change seeding?
- [ ] Is certificate reuse tied to a previously kernel-justified acceptance,
      not merely successful execution, a digest match, or a trusted producer
      signature?
- [ ] Is `IncrementalAccept -> FreshValid` non-circular and explicit about which
      premises already contain local validity?
- [ ] Is the executable closure/key/cache/checker pipeline proved to refine the
      Lean model, including decoding and serialization?
- [ ] Are cryptographic integrity, rollback/freshness, concurrency, and
      cross-host authority either formally covered or clearly excluded?
- [ ] Do adversarial tests remove each assumption in turn, including hidden
      inputs, forged authority, stale policy/version, incomplete changes, and
      graph rewiring?
- [ ] Do benchmarks isolate cache bookkeeping, certificate checking, and full
      recomputation, and retain negative results where checks are cheap?
- [ ] Is the empirical contribution demonstrated on real expensive certificate
      checkers rather than only synthetic delays?

If the work stops at downstream invalidation plus exact memoization, it is
standard incremental-build technology. If it stops at an abstract per-node
case split without executable refinement, it is a useful specification lemma.
The stronger research contribution is an end-to-end, machine-checked bridge
from evolving scientific DAGs and authoritative caches to fresh certificate
validity.

## References

1. Umut A. Acar, Guy E. Blelloch, and Robert Harper. “Adaptive Functional
   Programming.” *POPL 2002*, pp. 247–259.
   <https://doi.org/10.1145/503272.503296>
2. Umut A. Acar, Guy E. Blelloch, and Robert Harper. “Adaptive Functional
   Programming.” *ACM Transactions on Programming Languages and Systems*,
   2006. <https://doi.org/10.1145/1186632.1186634>
3. Matthew A. Hammer, Khoo Yit Phang, Michael Hicks, and Jeffrey S. Foster.
   “Adapton: Composable, Demand-Driven Incremental Computation.” *PLDI 2014*,
   pp. 156–166. <https://doi.org/10.1145/2594291.2594324>
4. Andrey Mokhov, Neil Mitchell, and Simon Peyton Jones. “Build Systems à la
   Carte.” *Proceedings of the ACM on Programming Languages* 2 (ICFP), Article
   79, 2018. <https://doi.org/10.1145/3236774>
5. Neil Mitchell. “Shake Before Building: Replacing Make with Haskell.”
   *ICFP 2012*. <https://doi.org/10.1145/2398856.2364538>
6. Sebastian Erdweg, Moritz Lichter, and Manuel Weiel. “A Sound and Optimal
   Incremental Build System with Dynamic Dependencies.” *OOPSLA 2015*,
   pp. 89–106. <https://doi.org/10.1145/2814270.2814316>
7. Bazel. “Remote Caching.” Official documentation.
   <https://bazel.build/remote/caching>
8. Bazel. “Hermeticity.” Official documentation.
   <https://bazel.build/basics/hermeticity>
9. George C. Necula. “Proof-Carrying Code.” *POPL 1997*, pp. 106–119.
   <https://doi.org/10.1145/263699.263712>
10. Bruno Barras, Carst Tankink, and Enrico Tassi. “Asynchronous Processing of
    Coq Documents: From the Kernel up to the User Interface.” *ITP 2015*,
    LNCS 9236, pp. 51–66.
    <https://doi.org/10.1007/978-3-319-22102-1_4>
11. Makarius Wenzel. “Asynchronous User Interaction and Tool Integration in
    Isabelle/PIDE.” *ITP 2014*, LNCS 8558, pp. 515–530.
    <https://doi.org/10.1007/978-3-319-08970-6_33>
12. Bernhard Beckert and Vladimir Klebanov. “Proof Reuse for Deductive Program
    Verification.” *SEFM 2004*, pp. 77–86.
    <https://doi.org/10.1109/SEFM.2004.33>
13. Ralph C. Merkle. “A Digital Signature Based on a Conventional Encryption
    Function.” *CRYPTO '87*, pp. 369–378.
    <https://doi.org/10.1007/3-540-48184-2_32>
14. Roberto Tamassia. “Authenticated Data Structures.” *Algorithms—ESA 2003*,
    LNCS 2832, pp. 2–5.
    <https://doi.org/10.1007/978-3-540-39658-1_2>
15. Eelco Dolstra, Merijn de Jonge, and Eelco Visser. “Nix: A Safe and
    Policy-Free System for Software Deployment.” *LISA 2004*, pp. 79–92.
    <https://www.usenix.org/legacy/events/lisa04/tech/full_papers/dolstra/dolstra_html/>
16. Nix documentation. “Configure Nix to use a custom binary cache.”
    <https://nix.dev/guides/recipes/add-binary-cache.html>
17. Docker documentation. “Build cache invalidation.”
    <https://docs.docker.com/build/cache/invalidation/>
18. Xavier Leroy. “Formal Verification of a Realistic Compiler.”
    *Communications of the ACM* 52(7), 2009, pp. 107–115.
    <https://doi.org/10.1145/1538788.1538814>
19. Paolo Di Tommaso et al. “Nextflow Enables Reproducible Computational
    Workflows.” *Nature Biotechnology* 35, 2017, pp. 316–319.
    <https://doi.org/10.1038/nbt.3820>
20. Nextflow documentation. “Caching and resuming.”
    <https://docs.seqera.io/nextflow/cache-and-resume>
21. Johannes Köster and Sven Rahmann. “Snakemake—a Scalable Bioinformatics
    Workflow Engine.” *Bioinformatics* 28(19), 2012, pp. 2520–2522.
    <https://doi.org/10.1093/bioinformatics/bts480>
22. Felix Mölder et al. “Sustainable Data Analysis with Snakemake.”
    *F1000Research* 10:33, 2021.
    <https://doi.org/10.12688/f1000research.29032.2>

Official web documentation in references 7, 8, 16, 17, and 20 describes
version-evolving production behavior and was checked on 2026-11-17. It should
be cited with an access date or pinned revision in a publication artifact.
