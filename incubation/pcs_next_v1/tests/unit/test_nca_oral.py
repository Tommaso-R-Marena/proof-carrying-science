import math
from pcs_next_v1.demos.oral_pk import bateman
from pcs_next_v1.demos.nca import cmax_tmax, log_linear_terminal_half_life

def test_bateman_positive_and_peak():
    ts = [i * 0.25 for i in range(0, 40)]
    cs = [bateman(t, dose=4.0, v=0.5, ka=1.5, ke=0.1) for t in ts]
    assert all(c >= -1e-12 for c in cs)
    cmax, tmax = cmax_tmax(ts, cs)
    assert cmax > 0 and tmax > 0

def test_half_life_known():
    ke = 0.2
    times = [1, 2, 3, 4, 5]
    concs = [math.exp(-ke * t) for t in times]
    th = log_linear_terminal_half_life(times, concs, n_terminal=5)
    assert th is not None
    assert abs(th - math.log(2) / ke) < 1e-6
