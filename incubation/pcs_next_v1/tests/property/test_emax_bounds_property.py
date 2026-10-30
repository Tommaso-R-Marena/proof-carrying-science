from pcs_next_v1.adapters.pd import predict_emax


def test_emax_bounds_mirror_lean():
    for e0 in (0.0, 1.0, 5.0):
        for emax in (0.0, 10.0, 100.0):
            for ec50 in (0.5, 2.0, 8.0):
                for c in (0.0, 0.1, 1.0, 10.0, 100.0):
                    e = predict_emax(c, e0, emax, ec50)
                    assert e0 - 1e-12 <= e <= e0 + emax + 1e-12
                assert abs(predict_emax(0.0, e0, emax, ec50) - e0) < 1e-12
