# PCS real-study replay evidence campaign

**Execution date:** 2026-09-30  
**Purpose:** stress the new realized-environment / deterministic-replay semantics on real scientific and ML workloads, with positive and adversarial controls.

## Executive result

- **11/11** substantive workflows were byte-identical across 3 independent runs.
- **5/5** representative workloads remained byte-identical across 10 runs: PK, XGBoost, deterministic PyTorch, JAX, and an executed Jupyter notebook.
- A three-stage breast-cancer pipeline regenerated **5/5 artifacts identically across 10 runs** after stale outputs were deliberately removed first.
- **3/3** nondeterministic controls diverged across 3 runs and produced **10/10 unique hashes** across 10-run stress tests.
- **12/12** adversarial/perturbation cases were detected by hash/contract/determinism semantics.

## Realized host environment

- Python: `3.13.5` (CPython)
- Interpreter SHA-256: `17b78e0a93175e86f9ac03141924fd7a7f0c0c52e66b34bfa0de20ffef989df1`
- OS/architecture: `Linux 6.18.44 / x86_64`
- Installed distributions: **507**
- Full dependency-tree fingerprint: `c2c2f4935e59bdcafc91794a39f25c80b375f70fe3bd69e4d128eee3db855173`
- Docker/Podman: unavailable in this execution runtime
- Rscript: unavailable in this execution runtime

## Three-run substantive matrix

| Workload | System/model | Unique hashes / 3 | Representative result |
|---|---|---:|---|
| `pk_one_compartment` | SciPy one-compartment IV PK | **1 / 3** | CL=5.2065352342046625, V=30.834638580863142, cost=0.003852852326507019 |
| `pk_oral_bateman` | SciPy oral Bateman PK | **1 / 3** | CL=4.803624666878333, V=27.9980245603593, ka=1.2638525313266684 |
| `pd_emax_hill` | SciPy Hill/Emax PD | **1 / 3** | E0=5.089378817271006, Emax=81.86196217881245, hill=1.4049977542974736 |
| `breast_cancer_logreg` | scikit-learn logistic regression | **1 / 3** | accuracy=0.972027972027972, auc=0.9958071278825996 |
| `diabetes_ridge` | scikit-learn ridge regression | **1 / 3** | r2=0.5158952893072868, rmse=54.437972942307155 |
| `wine_xgboost` | XGBoost multiclass classifier | **1 / 3** | accuracy=0.8888888888888888, logloss=0.27341171555611676 |
| `digits_pytorch` | PyTorch deterministic CPU MLP | **1 / 3** | accuracy=0.7333333492279053, final_loss=1.9274230003356934 |
| `jax_linear_system` | JAX x64 linear solve | **1 / 3** | rmse=0.04423052104178822, coef_norm=4.341370851291037 |
| `arima_nile` | statsmodels ARIMA | **1 / 3** | aic=1267.6233969877317, bic=1278.00387638827 |
| `sympy_reaction_ode` | SymPy symbolic reaction ODE | **1 / 3** | solution=A0*exp(-k*t), integral=A0/k |
| `iris_notebook` | Jupyter + PCA/logistic regression | **1 / 3** | accuracy=0.9333333333333333 |

## Ten-run stress

| Workload | Runs | Unique output hashes | Result |
|---|---:|---:|---|
| `pk_one_compartment` | 10 | **1** | stable |
| `wine_xgboost` | 10 | **1** | stable |
| `digits_pytorch` | 10 | **1** | stable |
| `jax_linear_system` | 10 | **1** | stable |
| `iris_notebook` | 10 | **1** | stable |
| `clock_nondeterminism` | 10 | **10** | divergence detected |
| `entropy_nondeterminism` | 10 | **10** | divergence detected |
| `unseeded_torch` | 10 | **10** | divergence detected |

### Multi-stage pipeline

The breast-cancer pipeline performs deterministic split → preprocessing/model fit → report generation. Before every run, stale copies of the declared outputs were created and then deleted, mirroring the PCS stale-output defense.

| Artifact | Runs | Unique hashes |
|---|---:|---:|
| `split.npz` | 10 | **1** |
| `model.npz` | 10 | **1** |
| `preprocess.json` | 10 | **1** |
| `train.json` | 10 | **1** |
| `final_report.json` | 10 | **1** |

Representative final report: `{"accuracy": 0.972027972027972, "auc": 0.9958071278825996, "n": 143}`

## Adversarial evidence

Detected cases: output byte tamper; signed-input mutation; stale output not regenerated; symlink output substitution; undeclared extra output; impossible exact dependency pin; interpreter-version mismatch; dependency-tree perturbation; interpreter-binary perturbation; wall-clock nondeterminism; entropy nondeterminism; unseeded PyTorch nondeterminism.

All **12/12** produced the expected mismatch/rejection/divergence signal. See `attacks.json` for exact hashes and fields.

## GitHub-hosted execution probe

A second workflow using `ubuntu-slim` was added to test whether a different GitHub-hosted runner pool would execute the exact PCS regression suite. It failed before checkout exactly like `ubuntu-latest`: run `36664893472`, job `109727349086`, `runner_id=0`, `steps=[]`. This is a pre-execution runner-provisioning failure, not an observed PCS test failure.

## What this does and does not establish

**Established on this host:** deterministic scientific outputs across multiple numerical/ML ecosystems; reproducible notebook and multi-stage execution; realized interpreter/dependency fingerprints; clean discrimination of deterministic vs clock/entropy/unseeded workloads; output/input/environment drift detection.

**Not yet established here:** actual Docker/Podman sandbox execution, offline digest-pinned container rebuilds, R execution, or cross-OS/cross-architecture equivalence. Those require an OCI-capable external machine/runner. The PCS code for those boundaries exists, but this host cannot execute them.
