import math
from pcs_next_v1.demos.nca import trapezoidal_auc, cmax_tmax
from pcs_next_v1.demos.oral_pk import bateman
from pcs_next_v1.oracles.nca_oracle import oracle_trapezoidal_auc, oracle_cmax_tmax
from pcs_next_v1.oracles.bateman_oracle import oracle_bateman, oracle_michaelis_menten
from pcs_next_v1.oracles.canonical_diff import compare_to_production

def test_nca_matches_oracle():
    times = [0.0, 0.5, 1.0, 2.0, 4.0]
    concs = [0.0, 1.2, 2.0, 1.1, 0.4]
    assert abs(trapezoidal_auc(times, concs) - oracle_trapezoidal_auc(times, concs)) < 1e-12
    assert cmax_tmax(times, concs) == oracle_cmax_tmax(times, concs)

def test_bateman_matches_oracle():
    for t in [0.0, 0.25, 1.0, 3.0, 10.0]:
        a = bateman(t, dose=4.0, v=0.5, ka=1.5, ke=0.1)
        b = oracle_bateman(t, 4.0, 0.5, 1.5, 0.1)
        assert abs(a - b) < 1e-12

def test_mm_saturation():
    # as conc -> inf, rate -> vmax
    assert abs(oracle_michaelis_menten(1e9, 200, 0.05) - 200) < 1e-6
    assert oracle_michaelis_menten(0.05, 200, 0.05) == 100.0

def test_canonical_diff_runs():
    r = compare_to_production({"a": 1, "b": [True, None]})
    assert r["status"] in {"COMPUTATIONALLY_TESTED", "SKIPPED", "OPEN", "REFUTED"}
