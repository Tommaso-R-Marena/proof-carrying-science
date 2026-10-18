=== Noninterference Audit ===
repo: /agent/repos/proof-carrying-science
branch: feature/pcs-causal-laboratory-v1-4972
head: fabc704efdbda4c8822881366e4db3d3e31f066a
remote:
origin	https://x-access-token:ghs_1210556_eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRobmQiLCJjdHgiOiJrZEJRODk1d2RaTHcydGtxMEJ0TXo4c1JBQngyM3VSQk55bFB0OXZucUg1a3VtQ05EVTY4MV9HMkJuUzcxcU0iLCJleHAiOjE3OTIyODU0MTYsImlhdCI6MTc5MjI4MTgxNiwiaXNzIjoiZ2l0aHViIiwianRpIjoiOWRhNzVjOGEtM2I4NS00ODM2LWJhMWItMThhOTVmOTc0MjA5IiwidmVyIjozfQ.2-XEU6R_wcp_3g3MiE0IG-FDBg-uKA0F33eTkyhLCNEbpcII6j2R4VcJdGLg0I3o_rlkvIdPMe6lcvmJgNIRAg@github.com/tommaso-r-marena/proof-carrying-science (fetch)
origin	https://x-access-token:ghs_1210556_eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJhdXRobmQiLCJjdHgiOiJrZEJRODk1d2RaTHcydGtxMEJ0TXo4c1JBQngyM3VSQk55bFB0OXZucUg1a3VtQ05EVTY4MV9HMkJuUzcxcU0iLCJleHAiOjE3OTIyODU0MTYsImlhdCI6MTc5MjI4MTgxNiwiaXNzIjoiZ2l0aHViIiwianRpIjoiOWRhNzVjOGEtM2I4NS00ODM2LWJhMWItMThhOTVmOTc0MjA5IiwidmVyIjozfQ.2-XEU6R_wcp_3g3MiE0IG-FDBg-uKA0F33eTkyhLCNEbpcII6j2R4VcJdGLg0I3o_rlkvIdPMe6lcvmJgNIRAg@github.com/tommaso-r-marena/proof-carrying-science (push)

status:
## feature/pcs-causal-laboratory-v1-4972...origin/main
?? incubation/

changed files vs origin/main:
  incubation/pcs_causal_laboratory_v1/.gitignore
  incubation/pcs_causal_laboratory_v1/NONINTERFERENCE_BASELINE.md
  incubation/pcs_causal_laboratory_v1/README.md
  incubation/pcs_causal_laboratory_v1/certificates/examples/backdoor_z.json
  incubation/pcs_causal_laboratory_v1/certificates/examples/nonident_witness.json
  incubation/pcs_causal_laboratory_v1/ci/github-actions-workflow.yml
  incubation/pcs_causal_laboratory_v1/docs/COUNTEREXAMPLE_LIBRARY.md
  incubation/pcs_causal_laboratory_v1/docs/FORMAL_STATUS.md
  incubation/pcs_causal_laboratory_v1/docs/INTEROPERABILITY_PROPOSAL.md
  incubation/pcs_causal_laboratory_v1/docs/TECHNICAL_REPORT.md
  incubation/pcs_causal_laboratory_v1/lean/PcsCausal.lean
  incubation/pcs_causal_laboratory_v1/lean/PcsCausal/Basic.lean
  incubation/pcs_causal_laboratory_v1/lean/PcsCausal/Graph.lean
  incubation/pcs_causal_laboratory_v1/lean/PcsCausal/Identification.lean
  incubation/pcs_causal_laboratory_v1/lean/PcsCausal/NonIdent.lean
  incubation/pcs_causal_laboratory_v1/lean/PcsCausal/Probability.lean
  incubation/pcs_causal_laboratory_v1/lean/lakefile.toml
  incubation/pcs_causal_laboratory_v1/lean/lean-toolchain
  incubation/pcs_causal_laboratory_v1/pyproject.toml
  incubation/pcs_causal_laboratory_v1/reports/NONINTERFERENCE_AUDIT.md
  incubation/pcs_causal_laboratory_v1/results/adversarial.json
  incubation/pcs_causal_laboratory_v1/results/backdoor_demo.json
  incubation/pcs_causal_laboratory_v1/results/drug_case.json
  incubation/pcs_causal_laboratory_v1/results/lean_axioms.txt
  incubation/pcs_causal_laboratory_v1/results/performance.json
  incubation/pcs_causal_laboratory_v1/results/witness.json
  incubation/pcs_causal_laboratory_v1/scripts/noninterference_audit.sh
  incubation/pcs_causal_laboratory_v1/scripts/run_tests.sh
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/benchmarks/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/benchmarks/adversarial.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/benchmarks/synthetic.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/cases/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/cases/biology_synth.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/certificates/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/certificates/format.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/certificates/verifier.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/cli.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/discovery/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/discovery/ci_tests.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/discovery/pc.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/estimation/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/estimation/estimators.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/estimation/positivity.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/experiments/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/experiments/design.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/graphs/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/graphs/admg.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/graphs/d_separation.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/graphs/dag.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/hypothesis/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/hypothesis/engine.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/hypothesis/states.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/identification/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/identification/backdoor.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/identification/do_calculus.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/identification/estimands.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/identification/frontdoor.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/nonident/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/nonident/witness_search.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/nonident/witness_verifier.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/probability/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/probability/rational_pmf.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/scm/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/scm/finite_scm.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/scm/interventions.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/sensitivity/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/sensitivity/bounds.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/sensitivity/confounding.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/ui/__init__.py
  incubation/pcs_causal_laboratory_v1/src/pcs_causal/ui/app.py
  incubation/pcs_causal_laboratory_v1/tests/test_certificates.py
  incubation/pcs_causal_laboratory_v1/tests/test_estimation_discovery.py
  incubation/pcs_causal_laboratory_v1/tests/test_experiments_cases.py
  incubation/pcs_causal_laboratory_v1/tests/test_graphs.py
  incubation/pcs_causal_laboratory_v1/tests/test_identification.py
  incubation/pcs_causal_laboratory_v1/tests/test_nonident.py
  incubation/pcs_causal_laboratory_v1/tests/test_probability.py
  incubation/pcs_causal_laboratory_v1/tests/test_scm_intervention.py

symlinks under lab:
incubation/pcs_causal_laboratory_v1/lean/.lake/packages/batteries/docs/README.md
incubation/pcs_causal_laboratory_v1/lean/.lake/packages/mathlib/scripts/bench/build/fake-root/bin/lean.py
incubation/pcs_causal_laboratory_v1/lean/.lake/packages/mathlib/scripts/bench/size/run.py
incubation/pcs_causal_laboratory_v1/.venv/lib64
incubation/pcs_causal_laboratory_v1/.venv/bin/python3.12
incubation/pcs_causal_laboratory_v1/.venv/bin/python
incubation/pcs_causal_laboratory_v1/.venv/bin/python3
AUDIT OK: all changes under incubation/pcs_causal_laboratory_v1/
