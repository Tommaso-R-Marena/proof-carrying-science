# PCS–CertiForge research adapter v1

The public-facing protocol is independently implemented in `pcs/certiforge_adapter_v1.py`. CertiForge's implementation remains in its separately private repository; no optimizer, interpreter, or formalization is copied into PCS. Publication rights for both repositories remain OPEN. Lean workspaces stay separate: PCS 4.28.0 and CertiForge 4.16.0.

## Protocol and acceptance boundary

A `pcs-certiforge-proposal-v1` binds a stable claim ID, source repository and full commit, disclosure category, exactly seven named semantic package artifacts with SHA-256, and the AST-node-count objective. The caller supplies a separately reviewed checker executable, its SHA-256 and source commit. Producer-controlled paths cannot select the trusted checker. The adapter rejects unsafe paths, symlinks, missing/duplicate members, changed bytes, failed/oversized checker output, unsupported domains, contract drift and unmet cost objectives.

The package is snapshotted before the actual Rust checker runs. Both the snapshot and checker are checked again for mutation. An accepted result means exhaustive replay for supported pure Bool/u8/u16 Cartesian domains of at most 65,536 inputs. It includes the exact artifact/checker identities, domain size, cost and residual obligations. It is `COMPUTATIONALLY_REPLAYED_NOT_FORMALLY_PROVED`, with `pcs_authority=false` and `lean_kernel_checked=false`. Source-to-binary correspondence and the Rust implementation are external trust assumptions. Source provenance is reported, not authenticated by a signature.

Bundled Lean text and LRAT placeholder files cannot grant authority. Large domains, effects, unrestricted languages, native executables, and formal certificate admission are unsupported. The external checker is **not registered as a PCS authoritative scientific verifier**.

`research_claim_graph` binds replay evidence into the existing `pcs-claim-ir-v1` and proof-obligation graph formats. It rechecks delivered bytes and leaves all four formal/intent/native obligations OPEN_BLOCKING. The claim's closure remains BLOCKED. A stale graph or artifact digest is not reusable evidence. This graph is a research/reporting interface, not a new authoritative predicate.

## Reproduce the actual local demo

Activate the environment, commit the separately retained CertiForge checkout, and build its pinned Rust and Lean workspaces:

```bash
source /workspace/.onboarding/activate.sh
cd /workspace/certiforge
cargo build --workspace --locked
cargo test --workspace --locked
(cd formal && lake build && lake env lean CertiForge/AxiomAudit.lean)
cd /workspace/proof-carrying-science
python scripts/run_certiforge_integration_v1.py --checkout /workspace/certiforge --output /tmp/pcs-demo-new
```

The output directory must not exist. Inspect `result.json`, `proposal.json`, `claim-graph.json`, `authorized-result.json` and the local interactive `evidence.html`. The independently specified toy proposal is not claimed to have been produced by an LLM. With seed 42 and SOURCE_DATE_EPOCH=0, the optimizer proposes OR in place of AND-plus-XOR; the checker exhaustively replays 65,536 input pairs and admits AST nodes 7→3. A malicious replacement is rehashed in both the proposal and manifest and still rejected semantically.

The bounded control monitor treats untrusted input as JSON proposals. Only its trusted constructor holds the effect callback. It serializes concurrent requests, consumes replay nonces and budget before effects, supports revocation and records a hash-consistent audit. The demo performs one actual file write and rejects forged approvals, wrong operations, stale policy, replay and post-revocation proposals. It is not a sandbox for arbitrary Python code. Exclusive mediation, OS isolation, faithful observations, and trusted callback implementation remain assumptions. Hash-chain consistency is not a signature or authentication of real-world events.

## Separate formal result

CertiForge's `formal/CertiForge/Examples/BoundDemo.lean` binds complete original/optimized u8 ASTs to typed-input equivalence and the OR output specification in Lean semantics. The equivalence theorem relies on `propext`, `Classical.choice`, `Lean.ofReduceBool`, and `Quot.sound`; the specification theorem uses `propext` and `Quot.sound`. The actual build emits this inventory. These proofs do not prove Rust/Lean refinement, parse arbitrary package certificates, or justify automatic promotion of a computational receipt.
