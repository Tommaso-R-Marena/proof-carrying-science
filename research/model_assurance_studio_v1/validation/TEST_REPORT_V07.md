# PCS Model Assurance Studio — v0.7 validation

Date: November 4, 2026. Test platform: Python 3.13, Linux x86_64, local NumPy, SciPy, PyTorch CPU, pytest, FastAPI and Chromium.

**239 collected pytest cases passed when run in seven separate cleanly terminated groups:**

| Test group | Result |
|---|---|
| Activation, agent policy, campaign, dense models, intake, new float32, guard | 109 passed, 77 subtests passed |
| Relational certificate v0.6 | 21 passed, 10 subtests passed |
| Biological/scientific research checks | 20 passed, 17 subtests passed |
| Update certificates v0.6 | 20 passed |
| v0.3 regression | 22 passed, 6 subtests passed |
| v0.5 regression | 33 passed, 6 subtests passed |
| MILP adversarial challenger | 14 passed, 6 subtests passed |

Total: **239 primary tests; 122 additional nested subtests**. The monolithic run timed out in this environment even after its test-progress output reached 100%; the above independently terminated batches supplied the usable exit statuses. A clean-extraction rerun of the new release evidence is required at packaging.

New numerical checks include 2,500 NumPy float32 rounding comparisons plus additional random rational rounding checks, signed/subnormal/overflow boundaries, float32 execution against exact interval enclosures for three serialized ONNX networks, 100 comparisons against explicitly rounded NumPy scalar operations on the trained Iris model, 100 random inputs checked against ideal-reality rounding error allowances, and 80 PyTorch CPU evaluations of updated Iris weights checked against those error allowances. The assertions exercise the released formulas; they do not constitute a Lean proof or IEEE-standard compliance audit.

Security/adversarial checks include: model/policy SHA-256 substitutions, altered exact witnesses, invalid output bounds, damaged updated weights, malformed model bytes, prohibited HTTP Origin and Host headers, optional-runtime absence, and real HTTP upload with independent local replay. No arbitrary model code or custom ONNX operator is run by the drag-and-drop inspection API.

Browser test: Chromium exercised both v0.7 binary32 demo flows and selected-file controls using genuine precomputed results over mocked HTTP transport; no JS errors were observed. Actual local TCP/HTTP upload and receipt replay were tested separately. No complete Chromium-to-local-server navigation claim is made.

**LEAN STATUS: NOT RUN / NOT KERNEL VERIFIED.** `lean` and `lake` were absent and cannot be downloaded. The generated Lean 4 source is a *proposed* Farkas proof obligation script with independently rechecked input numeric certificates; its validity and its correspondence to the ONNX source still require checking in a trusted Lean environment.

**OFFICIAL ONNX RUNTIME STATUS: NOT RUN.** Python `onnxruntime` and `onnx` packages were unavailable and could not be downloaded. The optional command truthfully reports NOT_RUN; its implementation has not been tested with a real installed ORT session. Actual NumPy and PyTorch comparisons are genuine but do not substitute for it.

The exact rational floating-point analysis is conditional on finite, correctly rounded IEEE operations as documented in `docs/LEAN_AND_FLOAT32_V07.md`, with no FTZ, lower-precision execution or unmodeled transformations. Its arithmetic proof obligations are currently checked by Python, not Lean.

The original PCS GitHub repository was not changed.
