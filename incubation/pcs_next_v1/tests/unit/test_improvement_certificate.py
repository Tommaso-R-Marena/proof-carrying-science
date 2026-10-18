from pcs_next_v1.research.proof_gated.models import (
    ScalarIntModel,
    TinyReluNet,
    improvement_certificate,
    relu_net_no_forgetting,
)


def test_certificate_accept_and_reject():
    old = ScalarIntModel(0, 0)
    new = ScalarIntModel(2, 0)
    data = [(1, 2), (2, 4), (3, 6)]
    ok = improvement_certificate(old, new, data, range(-1, 2), max_pointwise_increase=10**9)
    assert ok["accepted"] and ok["improves_on_data"]
    tight = improvement_certificate(old, new, data, range(0, 3), max_pointwise_increase=0)
    assert tight["accepted"] is False
    assert tight["preserves_on_domain"] is False


def test_relu_guard():
    old = TinyReluNet(w1=((1,),), b1=(0,), w2=(1,), b2=0)
    new = TinyReluNet(w1=((1,),), b1=(0,), w2=(1,), b2=3)
    ok, bad = relu_net_no_forgetting(old, new, [(0,), (1,), (2,)], max_pointwise_increase=0)
    assert ok is False and bad
