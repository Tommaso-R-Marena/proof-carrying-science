# PCS Model Assurance Studio — v0.6 validation record

**2026-11-04.** Source artifact is a **standalone local research prototype**, with no modifications to the main Proof-Carrying Science GitHub repository. Results are scoped to the exact tested source tree and generated small demo models. `SOURCE_MANIFEST_V06.json` lists per-file SHA-256 for audit convenience; it is **not externally signed**.

## Automated regression and independent checks

- `python -m unittest discover -q` → **225 tests passed**, about **70.1 s**. This includes the previous 166-test suite and 59 new tests (21 relational, 18 activation-case, 20 proof-gated model-update).
- `python -m tests.live_http_v06` → **PASS**: actual Uvicorn local HTTP training-model upload → exact rational certificate → independently verified against separate reviewer policy; nonlinear identity via HTTP; simultaneous old/new ONNX binary upload → baseline certificate + update drift → independent conditional composition; invalid model pair and cross-origin/Host attacks rejected.
- `python -S -m studio.verify_relational ...` → **PASS** on relational demonstration, nonlinear activation-case, and two distinct trained-Iris class margins, with no numerical solver or third-party Python packages loaded.
- `python -S -m studio.verify_update drift ...` → **PASS** old/new models for exact `1/8` drift with pinned model SHA-256 and policy.
- `python -S -m studio.verify_update compose ... --required-new-upper=-3/8` → **PASS** for baseline `-1/2` relation and `1/8` drift, yielding `-3/8` updated relation.
- Negative control replacing the proposed updated model with an altered-bias adversarial model → **REJECTED**, as required.
- `python -m studio.verify_receipt validation/v06_iris_full_assessment.json samples/demo_trained_iris_mlp.onnx --replay` → **MATCH**. Exact local replay is neither an external signature nor an independently proven mathematical theorem.
- `python -m tests.browser_smoke_v06` → **PASS** Chromium UI actions for relational, activation, trained-Iris and proof-gated update workflows using genuine analyzer responses and **mocked HTTP transport**; no JS page errors. Direct Chromium-to-localhost navigation was not available in this environment. `node --check studio/app.js` also passed.
- ZIP integrity and clean-extraction recheck performed separately before release.

## Real training/data result

- Small learned PyTorch model: 4 inputs → 8 hidden ReLU → 3 output logits, supervised training on real Iris flower measurement data (105 train, 45 held-out test); held-out accuracy 41/45 = **91.1%**.
- Trained weight matrices serialized as screened ONNX protobuf. Independent screened NumPy float32 interpreter vs fresh PyTorch inference on **all 150** actual samples: maximum absolute output difference **3.814697265625e-6**, average absolute difference **3.931919733683268e-7**, 81/150 output vectors bit-identical. Not official ONNX Runtime equivalence.
- Exactly checked two separately specified local class-margin requirements on a **single four-dimensional bounded box** around a correctly classified held-out sample.
- Updated classifier changes one float32 output bias by exact rational `1/8`; new drift certificate proves `c·f_new(x) − c·f_old(x) ≤ 1/8` and composes a baseline `c·f_old(x) ≤ −1/2` into `c·f_new(x) ≤ −3/8`, for every point in the **same chosen box under exact-real screened semantics**.

## Nonclaims and open gates

The project uses **classical** LP/Farkas duality, polyhedral ReLU relaxation, and exhaustive activation state splitting. These techniques are not novel; the integration into a drag/drop inspector + independent proof-gated update workflow is the engineering research contribution. No Lean compiler was available for this Studio experiment. A reviewer relying on a `python -S` verifier still trusts the Python interpreter, `Fraction`, restricted ONNX decode and constraint reconstruction. No formal proof of the verifier itself exists in this release. No official `onnx` or `onnxruntime` package was available; attempted downloads failed due network restrictions, so official execution was **not** tested. No full floating-point numerical soundness, hardware equivalence, frontier-LLM results, generalized AI safety, adversarial network security, biological validity, clinical claims or proof of user-intended requirements is established. The trained model and margin region are narrow, intentionally small, and partly selected to give an illustrative demonstration.

The generated reviewer policy files are **examples**; true acceptance requires a separately trusted reviewer to pin the original model SHA-256, updated SHA-256, claims, exact input region and thresholds. Without that independent governance, a malicious developer could supply an overly permissive policy while presenting a valid mathematical certificate.
