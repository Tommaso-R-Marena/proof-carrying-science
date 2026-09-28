# Formal Semantics Draft — Proof-Carrying Scientific Workflows

This is the design document for the Lean kernel. The current source encodes the core judgment as `Assures Γ L C E`; machine-checked status still awaits an actual Lean build.

## 1. Universes

Let:

- `A` be content-addressed artifacts;
- `Gamma` be a finite set of explicit assumptions;
- `C` be scoped claims;
- `E` be evidence objects;
- `K` be checkers;
- `W` be a typed workflow DAG.

Each evidence object records a checker, a finite dependency set of artifacts/evidence, an evidence class, and a purported outcome.

## 2. Evidence classes

Keep at least these classes distinct:

- `Formal(e)`: evidence intended to establish a mathematical/program property through an independently checkable proof object;
- `Computational(e)`: executable tests/checks over a finite computation or dataset;
- `Empirical(e)`: observational/experimental evidence concerning the world/model context;
- `Provenance(e)`: evidence about identity, lineage, environment, or integrity.

No inference rule should silently promote `Computational` or `Provenance` evidence into `Formal` or `Empirical` evidence.

## 3. Checker soundness interface

For a formal adapter `k`, the desired interface is not “k returned PASS.” It is a theorem of the form:

```text
forall p, Check_k(p) = true -> Semantics(Decode_k(p))
```

or a domain-specific refinement theorem that connects accepted proof objects to the intended semantic property.

This is the reusable CertiForge principle: a large/untrusted producer may search for evidence, while the acceptance boundary is a smaller checker whose soundness is itself established.

## 4. Scientific support judgment

Use a graded judgment rather than one overloaded word “verified”:

```text
Gamma ; E |- C @ L
```

where `L` is an assurance level/class such as formal, computational, empirical, or mixed.

A formal claim should be admitted only when a required formal evidence object is accepted by a checker with a soundness theorem for the relevant semantics. A computational claim may be supported by replayable finite checks. An empirical claim requires empirical/statistical evidence and remains scoped to context of use.

## 5. Assumptions

The semantics must make conditionality visible:

```text
Gamma |- C
```

is not presented as unconditional `C`. Certificates should expose `Gamma` in machine-readable and human-readable form.

## 6. Composition theorem target

Suppose subworkflow `W1` produces claim `C1` and evidence `E1`, and `W2` is justified assuming `C1` plus assumptions `Gamma2`. Under explicit compatibility and sound-adapter hypotheses, target a theorem of the form:

```text
Gamma1 ; E1 |- C1
Gamma2 ∪ {C1} ; E2 |- C2
--------------------------------
Gamma1 ∪ Gamma2 ; E1 ∪ E2 |- C2
```

The theorem must specify when evidence classes compose and when they do not.

## 7. Invalidation theorem target

Let `G` be a complete dependency graph containing all artifact-to-workflow, artifact-to-evidence, evidence-to-claim, and assumption-to-claim dependencies.

If artifact `a` changes, define `Reach_G(a)` as all downstream nodes reachable from `a`.

Target:

```text
if evidence e depends on a and a changes,
then e is not reusable without replay;
therefore every claim requiring e must be downgraded until e is re-established.
```

A stronger non-impact theorem (“unreachable claims remain valid”) requires a **dependency-completeness assumption**: hidden dependencies would otherwise make that inference unsound. This caveat should be explicit in the paper.

## 8. Authenticity vs validity

Content hashes establish integrity relative to recorded bytes; they do not establish who authored/approved a certificate. A production system therefore needs digital signatures/identity and possibly an append-only transparency mechanism. Formal semantics should distinguish:

- internal consistency/replay validity;
- artifact integrity;
- signer authenticity/authorization;
- scientific/empirical adequacy.

## 9. First theorem targets in Lean

1. Formal acceptance implies presence of passing formal evidence.
2. No evidence with outcome `UNVERIFIED` can discharge a required obligation.
3. Failing required evidence prevents accepted claim status.
4. Claim status is a deterministic function of normalized claim/evidence state.
5. Workflow DAG acceptance excludes cycles and ambiguous producers (once workflow semantics move into Lean).
6. Evidence composition preserves support under stated adapter-soundness hypotheses.
7. Invalidation reachability soundly identifies claims that must be reopened, under dependency-completeness assumptions.
