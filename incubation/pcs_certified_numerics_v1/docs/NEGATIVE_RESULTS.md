# Negative results / limitations

1. **Mean-value form is not always tighter** than natural extension (identity / monotone linear cases). Benchmark `mv_not_always_tighter` records this.
2. **Interval Euler** without remainder does **not** enclose the true ODE flow for nonlinear `f`; we refuse to advertise it as validated integration.
3. **Multivariate coverage checking** in the Python checker is weaker than 1D abutment checking; BnB provenance is required.
4. **Private repo creation** blocked by token scopes — isolation fallback used.
5. **Abs/min/max derivatives** are not classically unique at kinks; v1 AD rejects symbolic min/max derivatives.
