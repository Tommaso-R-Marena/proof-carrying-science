# PCS Operating Envelope v0.9 — proof-gated selective inference (research)

**Status:** experimental Python evidence / conditional operation. **NOT** a Lean-checked PCS certificate, an actual ONNX Runtime conformance proof, a hostile-file sandbox, a biological validation result, or a deployment authorization.

## The central claim

Given a pre-approved original model `f`, an updated model `g`, and a reviewer-pinned finite collection of closed input boxes `B_r`, this experiment attempts to establish **which model inputs may be processed at all**, rather than making a general safety declaration about the model.

For each region `B_r`, reviewer-selected winning output `w`, and **every** competitor `j != w`, PCS checks two separate rational Farkas certificates reconstructed against the exact model bytes:

1. `∀ x ∈ B_r: f_j(x) - f_w(x) ≤ β_r` (baseline margin);
2. `∀ x ∈ B_r: (g_j(x)-g_w(x)) - (f_j(x)-f_w(x)) ≤ δ_r` (same-input model-update drift).

Thus, in the screened **ideal-real ONNX subset**, `g_j(x) - g_w(x) ≤ β_r + δ_r` for every `x` in the entire box. The existing v0.7 arithmetic lift adds a model- and box-specific conservative allowance `ε_r,j` for **finite, sequential, non-fused, correctly rounded binary32 value operations**; it must establish `β_r + δ_r + ε_r,j ≤ -m_r` with reviewer-chosen `m_r > 0` for **every** competitor.

Only then does the host-owned `OperatingEnvelopeGate` admit an input whose **exact IEEE binary32 words** place it in one of the verified boxes. Input words outside every region, malformed/nonfinite inputs, absent proof branches, mismatched hashes, wrong independently pinned policy, or inconclusive arithmetic result in `ABSTAIN`. An admitted request is **conditional**, not universally safe. The checked inequality is for logits/class margin, not alignment, robustness to arbitrary data transformations, or scientific correctness.

## Genuine tested-model experiment

The bundled trained PyTorch Iris MLP (serialized to screened ONNX bytes) and its modified-weight successor yield **six** independently replayed baseline-and-drift proof pairs over **three** four-dimensional regions, with a reviewer-requested minimum binary32 class margin `1/4` for the winner over **both** alternative classes. Three regions were broadened *only where fresh certificates could be checked*; in the demonstration source Iris dataset, **27 of 150** normalized input vectors fall inside those regions. For these inputs the gate admits; it abstains on the other 123. The region anchors and radii were selected while examining this same dataset: **27/150 is not a blind evaluation, a population coverage estimate, or a generalization claim**. The mathematical certificates concern every idealized input in the boxes, not just the 150 measured flowers.

For the three bundled anchor inputs, `studio.guarded_reference_infer_v09` executes the specified scalar float32 interpreter **only after gate acceptance** and checks that its observed output class matches the certificate. Inputs outside the boxes are not executed. This is real computation by the screened software interpreter, but **not** official ONNX Runtime, CUDA, a trusted hardware execution engine, or an OS security boundary.

## How to reproduce, without a solver installed

From `research/model_assurance_studio_v1/`:

```sh
python -S -m unittest tests.test_operating_envelope_v09 -q
python -S -m studio.operating_envelope_v09 \
  samples/demo_trained_iris_mlp.onnx \
  samples/demo_trained_iris_updated.onnx \
  validation/v09_demo_envelope_evidence.json \
  validation/v09_demo_envelope_reviewer_policy.json \
  --trusted-policy-sha256 aec03cc456c9f6c77e548cffa1dc1503d795c1934d97d114afe4b4a0d7418c6d \
  --input-bits bfc3a730 3f9bceb1 bfc8e86a bfa96601
```

Expected conditional class: `0`. Other sample input bit words are recorded in `validation/v09_demo_input_words.json`. Re-run with `00000000` for all four words: the gate returns `ABSTAIN` and exit status `2`. `python -S` is intentional: the **reviewer** needs neither SciPy nor NumPy nor torch; it recomputes every claimed proof with Python's standard-library fractions. The fixture policy and digest live in the same research repository for ease of demonstration; **production reviewer independence is not established by that placement**.

For a local browser demonstration, run `python -m uvicorn studio.server:app --host 127.0.0.1 --port 8765`, open the page, and click **Run proof-gated inference**. Only bundled training artifacts are involved, not arbitrary uploads into the optional native runtime.

## Source, evidence, and threat boundary

- `studio/operating_envelope_v09.py`: policy and artifact byte-identity validation, complete-competitor proof checks, exact binary32 input membership, all-or-nothing reviewer validation and abstention.
- `studio/envelope_proposer_v09.py`: **untrusted** SciPy numerical proposer for all baseline and drift certificates; no solver outcome establishes proof acceptance.
- `studio/guarded_reference_infer_v09.py`: input gating before software reference execution, same-model SHA-256 recheck, observed-result consistency check, no native inference runtime.
- `validation/v09_demo_envelope_reviewer_policy.json`: example policy, not a real external reviewer decision; must be pinned outside the producer's control in a real use case.
- `validation/v09_demo_envelope_evidence.json`: all model-update certificate pairs; includes the policy identity but does not make the policy trustworthy.
- `tests/test_operating_envelope_v09.py`: adversarial policy, hash, model, incomplete-coverage, proof rehash and malformed IEEE word rejection cases, plus no-inference-on-abstention and HTTP demo checks.

The trust boundary still includes Python/Fraction, screened ONNX wire parsing, rational outer-polytope construction, Farkas checker, float32 error calculation, SHA-256 input custody, and host enforcement. A Python object is **not** a security enclave; untrusted code in the same process could bypass or monkeypatch it. The production caller must supply/lock the approved model bytes, independently administered policy hash, and exact input byte words, and must enforce the gate result *before* dispatch to a separately isolated runtime. A host cannot simply trust an attacker-controlled `PROVED_CONDITIONALLY` JSON field.

The assurance is also **not** a verification of all floating-point execution environments: the mathematical lift assumes finite RN-even operations under a fixed non-fused ordering, excludes FTZ/DAZ, reassociation, exceptions and hardware-specific algorithm substitutions, and has not been proven in Lean. A receiver with different numeric semantics cannot use this evidence to authorize execution. Zero/nonfinite values are treated according to the documented numeric model and accepted-input constraints.

## Required next milestones

1. Formalize and compile the narrowly scoped relational/activation certificate checker **and semantic model binding** in the pinned Lean 4.28.0 authority. No uncompiled `.lean` source may claim kernel acceptance.
2. Run actual official ONNX Runtime CPU in OS-isolated independent workers, measure divergence and revise numerical contracts or reject unsupported kernels. Finite empirical crosschecks cannot establish universal equivalence.
3. Implement host-owned model/input immutability, independent policy key custody, authenticated runtime dispatch/receipts, proper malicious-file isolation, time/memory budgets, and platform security review.
4. Evaluate on independently selected models and strictly held-out use cases; measure rejection/coverage tradeoff, scientific relevance and failure modes; do not promote this public example to general AI safety.

**Merge posture:** research-only draft. Additive to PCS, with no changes to the production `pcs` or `formal` authority or existing signed verification formats.

## Optional PyTorch CPU empirical crosscheck (not a proof)

If `torch` and `scikit-learn` are installed locally, run from this folder:

```sh
PYTHONPATH=. python scripts/crosscheck_v09_torch_cpu.py
```

It executes all **150** published Iris measurement vectors through the actual PyTorch CPU interpretation of the screened, updated graph, and separately through the deterministic software binary32 interpreter, then uses the reviewer-pinned operating gate to identify the **27** admitted vectors. In the recorded local run (`torch 2.10.0+cpu`), no admitted example violated the 0.25 class-margin requirement; the smallest *observed* admitted margin was approximately **6.3406**; maximum absolute output disagreement between the two numerical interpreters across all 150 vectors was **3.8147 × 10⁻⁶**. This is **finite empirical agreement** of two interpretations; it does not establish ONNX Runtime semantics, formal soundness of Python, input-distribution guarantees, or a statistically independent evaluation. The recorded observation is in `validation/v09_torch_cpu_observation.json` and may vary with hardware/compiler/backend versions.
