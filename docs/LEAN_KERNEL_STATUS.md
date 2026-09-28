# Lean kernel status

## Current verdict

**SOURCE COMPLETE FOR V0.2; MACHINE-CHECKED STATUS NOT YET ESTABLISHED.**

Target toolchain: `leanprover/lean4:v4.16.0`.

The repository contains a small Lean assurance kernel defining typed claims, assumptions, evidence classes, outcomes, machine-readable predicates, explicit claim/evidence binding, and the indexed judgment `Assures Γ L C E`, representing `Γ ; E ⊢ C @ L`. The central design rule is that assurance constructors carry successful evidence explicitly rather than accepting a user-supplied status label.

Theorem targets currently encoded include:

- the explicit assumption context covers every assumption ID declared by an assured claim;
- formal assurance contains passing formal-proof evidence;
- computational assurance is bound to the claim's machine-readable predicate;
- computational assurance cannot be constructed from unverified evidence;
- empirical assurance requires empirical/statistical evidence;
- mixed assurance requires both formal and empirical classes;
- canonical one-compartment IV PK units are dimensionally valid;
- canonical direct-Emax PD units are dimensionally valid.

`PCS.PKPD` intentionally formalizes the **representation/unit contract**, not the real-exponential PK equation or empirical drug adequacy. Numeric equation replay currently lives in the independently rerun Python adapter. Formalizing the analytic equation, code generation, and numerical error bounds is a later refinement.

## Compilation attempts on 2026-09-28

The current local execution environment has no `lean`, `lake`, or `elan`, and outbound installation is unavailable. To avoid touching the publication line, a private, non-merged branch of the existing private CertiForge repository was used only as an isolated compilation harness:

`pcs-kernel-compile-2026-09-28`

The harness targets Lean 4.16.0, matching CertiForge's existing toolchain, invokes `lake build`, and rejects any occurrence of `sorry` in the PCS sources.

GitHub Actions did **not** reach the Lean build step. The latest diagnostic job completed with `runner_id = 0`, an empty runner name, and `steps = []`. Therefore these failed runs are runner/provisioning failures and provide neither positive nor negative evidence about Lean source correctness.

No claim that this kernel is machine checked should be made until a real Lean process returns `lake build` success and the no-`sorry` audit passes.

## Reproduction command

Once Lean 4.16.0 is available:

```bash
./scripts/verify_lean.sh
```

The script fails if Lean/Lake are absent, if `lake build` fails, or if `sorry` appears in the formal sources.

## Publication boundary

The Lean kernel is an independent synthesis artifact. It contains no CertiForge optimizer semantics, CASMI/QFD algorithms, unpublished biological results, or proof-carrying-agent implementation details. See `PUBLICATION_FIREWALL.md`.

A direct attempt to bootstrap the official Lean 4.16.0 Linux release in the current sandbox also failed at the environment/download boundary before the toolchain was installed; this does not provide evidence for or against source correctness.
