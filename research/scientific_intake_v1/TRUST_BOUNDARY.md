# Evidence and trust boundaries

| Layer | Established here | Boundary still open |
| --- | --- | --- |
| Original files | Exact captured bytes, SHA-256/size, source inventory, portable snapshots and archive-member correspondence | Authenticity of upstream origin requires independent trusted provenance; a self-hashed archive is not an attestation |
| Extraction | Bounded real format readers, exact span references, isolated parser process and no imported code execution by design | Parser correctness, native PDF decoder vulnerabilities, complete document understanding and hostile-host confinement |
| Interpretation | Source/interpretation separation, closed directive/typed fragment, blocking meaning obligations | Expert intent, scientific validity, causal inference, units and general scientific semantics |
| Computation | Repeated exact rational observations, normal-equation/SSE certificates; independent numerical fit comparison | General implementation refinement, rank/uniqueness unless separately checked, dataset representativeness |
| Formal mathematics | Actual Lean 4.28 closed-proof acceptance and axiom audit; five conditional dependency theorems | Python–Lean refinement, complete automatic dependency discovery, scientific applicability |
| Learned proposals | Existing hash-pinned checkpoints run on their native states; no training on imported data | Scientific schema compatibility, generalization and best-baseline improvements |
| Cache | Exact source/payload/context bindings, authenticated host-local receipts and atomic writes | Same-user/host compromise, key extraction, trusted storage, library/toolchain integrity and hash collision resistance |
| Independent replay | Re-extracts snapshots, rebuilds graph/route/display/aggregates, reruns actual checks without cached verdicts | Independent implementation or external auditor; historical latency/proposal origin is not attested |

The learned components cannot select executable paths, checker imports, trusted registration, reward labels, production policy or deployment. Production `pcs/`, root `formal/`, frozen #199/#200 sources/evidence and protected source-census contracts are unchanged.

## Threat model

Imported files, claim directives, model metadata, notebook outputs, uploaded proofs, archive paths and embedded instructions are untrusted. Instructions inside those files never become operational instructions. Only host-owned code constructs closed supported checks. Imported Lean `#eval`, tactics, macros and proof bodies never reach Lean; an approved typed proposition is reconstructed and proved with fixed allowed actions through the existing PCS research Lean interface. A successful proof says only that this reconstructed proposition holds under its explicit formal assumptions.

Bounds cover input files, aggregate bytes, archive expansion, directory entries, extraction output/segments, graph claims, parser CPU/memory, PDF output/pages and replay package size. Malformed input yields an extraction error or `UNKNOWN`, not a positive verification verdict. Partial outputs after an interrupted intake are not successful evidence packages.

The parser subprocess inherits a stripped environment and a trusted working directory, and receives already captured bytes over stdin. Its limits and process separation do not establish privilege separation: there is no protected service identity, credential root, network sandbox or immutable storage. Native tools and Lean libraries depend on host integrity. POSIX permissions and HMAC do not protect against a compromised owner process.

## Conditional Lean results

`PCSScientificIntake.projection_congr`, `fixed_checker_reuse`, `policy_bound_reuse`, `closed_contains_reachable`, and `closed_dependency_reuse` are ordinary conditional consequences of equality and dependency closure. They are useful specifications for incremental checking, not new foundational mathematics. All five have empty axiom lists.

The complete input projection, fixed pure checker, equal policy and genuine named-byte equality are explicit premises. Hash equality is not silently equated with byte equality. The theorem does not prove that Python discovers a complete dependency set or faithfully implements that checker.

## Promotion and integration

Every scientific result remains a research sidecar with `authority: false`. No scientific or neural model is promoted. The prior proof-gated and Safety-JEPA promotion experiments remain frozen and undeployed. No Aristotle development trace becomes training data.

This branch is stacked on exact #200 head `3f257ac1e2d197a420da5a79b90822e09c2374e5`; #199/#200 remain draft/unmerged. Main adoption requires a separate reviewed source-admission successor where the existing frozen census applies, a Python refinement strategy, scientific annotation/evaluation review, and production UX/authority integration. Those requirements are not bypassed by a green experimental workflow.
