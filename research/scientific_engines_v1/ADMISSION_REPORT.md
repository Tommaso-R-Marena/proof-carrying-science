# Aristotle scientific-engine admission, 2026-10-23

## Source state and scope

The integration branch is `research/pcs-aristotle-scientific-engines-v1-20261023`, stacked on PR #178's exact head `b025ad4297252c0601b7b9c9a85859267a89c1fb`. That base has 6,456 tracked files. A dedicated preservation check requires every predecessor blob and file mode to remain unchanged. Additions are restricted to this directory and its dedicated workflow. Neither this branch nor PR #178 is a production deployment.

The protected branches independently inspected during this integration were:

| Repository | Protected main commit |
| --- | --- |
| proof-carrying-science | `fabc704efdbda4c8822881366e4db3d3e31f066a` |
| proof-carrying-science-site | `dd9f47798f572d37cea54574b3de5f9d00de4877` |
| certiforge | `c71e8575db2800b015a9d444f8ed572490f3a871` |

No site, Cloudflare deployment, production authority or protected branch is modified. The upload does not contain a new PGSI codec migration and is not treated as one.

## Intake and exact changes

`source_gate.py` verifies the two original archive hashes, every admitted vendor file against its archive, the six exact allowed patches, and the absence of active Lean admission or escape-hatch tokens. It checks 57 PRISM files and 49 AION files. Archives are retained unchanged. Upstream documents are reports to audit; their instructions are not adopted as user instructions, and proof-development traces are not used as training data.

PRISM's sole vendor correction makes the emitter handle zero experiments instead of calling `max` on an empty sequence. AION's four numerical example proof commands and emitter use ordinary kernel evaluation in place of compiler-trusted evaluation. All theorem statements are preserved. The separate PCS emitters replace descriptive identifiers with safe deterministic index labels before producing Lean; mathematical observations, costs, rates and certificate numbers retain their original indices and exact values.

Strict boundary checks reject duplicate JSON keys, nonfinite or floating-point values, Boolean/integer coercions, noncanonical rationals, unknown fields, ambiguous state-table coordinates and unsupported robust or finite-horizon claims. Canonical evidence binds input bytes, generated policy bytes, reviewed source hashes, dependency revisions, Lean executable hash, exact claims, proof source and audited theorem assumptions. Rehashing a forged scientific claim does not make it replay successfully. Receipt hashes do not authenticate authors or provide an immutable root.

## What is added beyond existing PCS mathematics

Existing `PcsCausal.nonidentifiable_of_witness` proves observational nonidentification from a pair of abstract models. PRISM adds checked finite version spaces, sharp attained query bounds, complete two-model impossibility, and matching policy/adversary certificates for global minimax experiment cost over all adaptive policies. This extends the executable research surface; it does not invalidate or replace the earlier witness theorem.

Existing `PCSReal.Calibration` contains exact regression, response perturbation and minimax estimator-radius results. Those concern an estimator under a fixed observation model. The present experiment-design result concerns costs of adaptive observations over a declared finite model class. The word “minimax” alone does not make them the same theorem.

AION adds infinite-state mass-action jump-chain hitting functionals, explicit finite path sums, barrier and escape-certificate soundness, a symbolic birth-death result, relative-error transfer, and abstract robust/compositional results. These are mathematical formalizations. Literature novelty has not been established. The executable Python robust checker is not promoted to a verified checker.

Six PCS bridge theorems explicitly preserve event alignment, actual-model membership, interval bounds and classifier correspondence. Eight additional concrete theorems prove the following integrated example:

* Birth rate 1, death rate 2: risk of hitting 20 before extinction from state 1 is exactly `1/1048575`.
* Birth rate 1, death rate 3/2: risk is exactly `524288/3485735825`.
* These lie on opposite sides of threshold `1/100000`.
* With two stipulated model-identifying assays costing 1 and 7, the cost-1 policy is globally minimax optimal.
* With uninformative assays, every adaptive policy fails to identify the risk class and optimal identification cost is infinite.

The Python exact-fraction oracle independently reproduces both risk fractions through a geometric-series expression. The Lean proofs establish the risk and experiment statements under declared mathematical models; the oracle is an implementation check, not empirical evidence.

## Admission and resource limitations

The routine authority rebuilds 21 core modules and audits 107 named headline theorem closures. All 14 new PCS theorems are included. The entire original PRISM library independently built, including its generated biochemical/causal examples and its 73-name upstream axiom audit. Generic AION checker, composition, path semantics, negative results and symbolic birth-death modules independently built.

The provided AION `BDcert` numerical module independently compiled with ordinary kernel proofs (193 seconds). Its numerical claims must be distinguished from the three larger examples. Ordinary-kernel retries of `XYsmall`, `GeneCert`, and `XYmain` each exited 137 under the 8 GiB execution limit, after approximately 40.5, 46.4 and 48.9 seconds respectively. Earlier concurrent attempts and interruptions are retained too. These are resource failures, not disproved mathematical statements. The three numerical modules are excluded from routine authority imports and their reported intervals are **not admitted numerical evidence**. In particular, the uploaded two-species rare-event headline is not claimed as independently kernel-verified here.

The core authority and every accepted generated instance require actual Lean success and exact assumption inventories. No Python checker result, supplied log or mock affirmative verdict substitutes for that. Large certificates can fail closed on time or memory limits. A compiled Mathlib cache and trusted host remain explicit dependencies; source revisions alone do not attest every cached object.

## Scientific and security limits

The results concern synthetic declared models. They establish neither observed biological behavior nor AI-model safety. No new model weights or real-world experiments were run for this integration. Prior model experiments remain historical evidence and are not relabeled as validation of these theorems.

No continuous-time path-space measure or finite-time reachability bound is proved. Translating eventual jump-chain hitting probabilities into a continuous-time physical claim requires additional assumptions and proof. Actual model membership and assay accuracy remain separate scientific obligations.

The Lean executable runs as a subprocess, but the host controls Python, source emission, storage and dependency objects. This is not an independently administered verifier service. Neither Python privacy, content hashes nor filesystem permissions establish an unconditionally immutable boundary. The interface accepts typed numeric evidence, not caller-specified verifier executables or raw proof-source payloads.

The next priorities are a proved byte-to-model decoder, scalable ordinary-kernel checking for the quarantined numerical instances, a formally constructed continuous-time correspondence, and empirical assay/model validation on an independently selected dataset. Production authority integration should follow a separate review after those boundaries are resolved.

## Final local qualification

The source snapshot at `12fd9acc361533ded972034b0e4902f87c46b37b` passed all **53 tests**, with zero failures and zero skips, in 395.61 seconds. This includes 12 real-Lean integration tests, 38 parser/semantic tests, one exact provenance test and two storage publication tests. A fresh child process rebuilt all admitted libraries and rederived the joint scientific evidence. False Lean propositions and a numerically false AION certificate were actually rejected; no mock affirmative verifier is used. Forged replay claims leave no accepted output package.

Additional independent checks accepted six honest PRISM certificates and rejected their six tampered counterparts in both Python and Lean, with zero disagreements. The five provided `BDcert` results (`upper_ok`, `lower_ok`, `upper_val`, `lower_val`, `sandwich`) were audited separately and use only the three standard assumptions.

The upstream baseline reproduced 400 finite-model instances: 177 impossible and 223 optimal, 134 brute-force comparisons, 21 greedy failures, 19 adaptivity gaps, and 1,122 tamper rejections with zero false accepts. All 38 upstream serialization rejection cases and all 18 AION unit tests passed. These counts describe separate campaigns and are not added together as independent scientific discoveries.

Machine-readable results and the exact code-source snapshot are in `evidence/intake-20261023/qualification.json`; full theorem closures are in `core-build.json`, and actual compiler invocations and rejection diagnostics are in `authority-executions.json`. Initial failures and memory-limited attempts remain alongside the passing results. GitHub CI runs the final source and retains fresh proof packages and compiled artifacts; its current status is visible in PR #179.

This interface is qualified on the reviewed Linux x86_64 Lean binary and Python 3.12.14. Other host platforms are not qualified by these runs. It is suitable for expert research review of the declared model claims; production scientific or AI-safety deployment requires the outstanding correspondence and empirical obligations above.
