# PCS Next isolated Lean workspace

- Toolchain: Lean 4.28.0 (matches production pin; does not modify root `lean-toolchain`)
- Namespace: `PcsNext.*`
- No `sorry` / `admit` / axioms / `unsafe` / `implemented_by`

Build (when `lake`/`elan` available):

```bash
cd incubation/pcs_next_v1/formal
lake build
```
