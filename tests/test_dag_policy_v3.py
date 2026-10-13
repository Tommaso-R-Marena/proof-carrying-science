"""DAG semantics, actual gradients and untrusted checkpoint rejection."""
import hashlib
import json
import pytest

torch = pytest.importorskip("torch")
from pcs.experimental.prover.dag_policy_v3 import DAGPolicy, tensors
from pcs.experimental.prover.state_graph import encode_state, decode_state


def node(kind, value="", *children):
    return {"kind": kind, "value": value, "children": list(children)}


def state():
    # Real Lean expression schema: the second argument refers to its binder.
    expression = node("forall", "hygienic", node("constant", "Nat:[]"),
                      node("application", "", node("constant", "Nat.succ:[]"), node("bound", "0")))
    return {"goals": [{"expression": expression, "target": "∀ n : Nat, Nat.succ n", "locals": []}]}


def test_lossless_dag_and_binder_edge():
    original = state()
    assert decode_state(encode_state(original)) == original
    values, edges = tensors(original)
    assert any(relation == 8 for _, _, relation in edges)
    assert any(relation == 9 for _, _, relation in edges)
    assert any(relation == 0 for _, _, relation in edges)
    assert any(relation == 1 for _, _, relation in edges)
    assert len(values) > 0


def test_actual_trainable_message_and_edge_gradients():
    torch.manual_seed(43)
    model = DAGPolicy()
    before = {n: p.detach().clone() for n, p in model.named_parameters()}
    options = [{"kind": "intro", "argument": "h0"}, {"kind": "assumption", "argument": None}]
    optimizer = torch.optim.Adam(model.parameters(), lr=.01)
    logits, value, uncertainty = model(state(), options)
    loss = torch.nn.functional.cross_entropy(logits[None], torch.tensor([0])) + value.square() + uncertainty.square()
    optimizer.zero_grad(); loss.backward(); optimizer.step()
    for name in ["tokens.weight", "edge_types.weight", "message.weight", "update.weight"]:
        assert not torch.equal(before[name], dict(model.named_parameters())[name])
    assert len(model.rank(state(), options)) == len(options)


def test_json_round_trip_and_digest_boundary(tmp_path):
    model = DAGPolicy()
    path = tmp_path / "checkpoint.json"
    sha = model.save(path, {"authority": False})
    loaded = DAGPolicy.load(path, sha)
    options = [{"kind": "intro", "argument": "h0"}]
    assert loaded.rank(state(), options) == model.rank(state(), options)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="integrity"):
        DAGPolicy.load(path, sha)


def test_forged_checkpoint_shape_and_nan(tmp_path):
    model = DAGPolicy()
    path = tmp_path / "checkpoint.json"
    model.save(path, {})
    payload = json.loads(path.read_text())
    payload["weights"]["tokens.weight"] = [[1.0]]
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="tensor"):
        DAGPolicy.load(path, hashlib.sha256(path.read_bytes()).hexdigest())
    model.save(path, {})
    payload = json.loads(path.read_text()); payload["weights"]["tokens.weight"][0][0] = float("nan")
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="tensor"):
        DAGPolicy.load(path, hashlib.sha256(path.read_bytes()).hexdigest())


def test_arbitrary_tactic_and_malformed_binding_rejected():
    with pytest.raises(ValueError):
        DAGPolicy().rank(state(), [{"kind": "exact", "argument": "by sorry"}])
    bad = state(); bad["goals"][0]["expression"]["children"][1]["children"][1]["value"] = "99"
    with pytest.raises(ValueError, match="unbound"):
        DAGPolicy().rank(bad, [])
