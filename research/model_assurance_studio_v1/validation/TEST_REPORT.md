# PCS Model Assurance Studio v0.3 — local validation report

- **Unit/integration/adversarial tests:** 78 passed (`python -m unittest discover -v`).
- **Reference environment:** Python 3.13.5, NumPy 2.3.5; no official ONNX checker or ONNX Runtime installed.
- **Numerical experiment:** a real serialized one-node FLOAT32 ONNX ReLU graph was parsed by the Studio, searched for an idealized policy violation, and evaluated using allowlisted NumPy float32 primitive operations in a separate child process. Required output interval `[0, 0.5]`; witnessed input `1.0`; resulting output `1.0`, with float32 little-endian bytes `00 00 80 3f`. This establishes **only** the scoped reference-operator violation, not ONNX Runtime model behavior.
- **Backend HTTP integration:** an actual local Uvicorn process at `127.0.0.1:8765` accepted `/api/status` and `/api/analyze`, returning `VIOLATION_REPRODUCED` in the latter report. Local Host-header and cross-origin denial tests also pass.
- **Browser rendering:** Chromium loaded the actual HTML/JS and rendered both the ONNX and agent-guard views using actual engine-produced report objects without JS page errors. Browser localhost navigation is administratively blocked in the reference environment, so this was **not** a browser-to-server HTTP test; that remains a portability task.
- **Receipt replay:** `python -m studio.verify_receipt validation/v03_relu_reference_receipt.json samples/demo_relu_violation.onnx --replay` matched the full deterministic assessment. A forged report with its digest recalculated is rejected by reanalysis, but this process is not independently cryptographically authenticated.
- **Chemistry:** existing exact stoichiometric reaction-only invariants; elemental stoichiometry good/bad fixtures; new charge annotated good/bad/missing tests. No full SBML dynamics or biological validity is implied.
- **Agent gate:** synthetic fixed reviewer-owned policy, pure preflight authorizer, and synthetic allowed/blocked/misreported execution trace scenarios. No actual tool execution occurred; the uploaded trace does not authenticate what happened in an external runtime.

All test fixtures included in this package are synthetic or simple locally generated example artifacts. The full test suite should be re-run after extraction, on every supported platform and dependency version before further development.
