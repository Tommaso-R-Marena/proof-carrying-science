# Start using PCS Model Assurance Studio v0.7

**Windows:** Extract the ZIP to a folder and double-click `launch_windows.bat`. Wait for the browser to open at `http://127.0.0.1:8765`. The first launch installs the core Python dependencies. No cloud upload or PCS repository change is required.

**Mac/Linux:** Extract the ZIP and run `sh launch_mac_linux.sh`.

## Try the strongest new demonstrations

- **Check binary32 rounding:** Click the example button. The app creates an exact rational interval for the specified sequential float32 arithmetic model and identifies its limits. A download includes the proposed reviewer policy and a reproducible receipt.
- **Prove FP32 model update:** Click the example button. The app loads the trained Iris classifier and its updated weights, independently checks the exact-real margin and change certificates, and adds a conservative float32 rounding allowance under declared IEEE assumptions. The updated model's guaranteed class margin remains at least 0.37 **in the selected local input box under those assumptions**.
- **Drag in your own small dense ONNX network:** Use the upload area. For a single model, choose **Check selected model in float32**; for a pair (original first), choose **Check selected model update in FP32**. Set output coefficients, input bounds, and the acceptance threshold. Unsupported models and claims remain OPEN.

To replay the included saved receipts and source files without ML solvers, double-click `run_v07_validation_windows.bat` or run `sh run_v07_validation_mac_linux.sh`.

## Important boundaries

The v0.7 Lean files are uncompiled source examples, not verified Lean proofs. The optional official ONNX Runtime adapter is not installed and was not executed in the release environment. The float32 bounds assume a specified IEEE arithmetic contract and do **not** certify every ONNX runtime, hardware backend or AI system. User-interface generated policies need independent reviewer confirmation. No arbitrary model code is executed by drag-and-drop; the separate optional native ONNX Runtime command must only be used on trusted models or inside properly hardened isolation.

See `docs/LEAN_AND_FLOAT32_V07.md` for the full mathematical specification, commands, and remaining milestones.
