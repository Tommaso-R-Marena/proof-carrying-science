"""Grounded signature influence, actual graph training, safe resumable Adam."""
import hashlib
import json
import pytest

torch = pytest.importorskip("torch")
from pcs.experimental.prover.premise_policy_v4 import PremisePolicy, save_training_checkpoint, load_training_checkpoint


def expression(name):
    return {"kind": "constant", "value": name + ":[]", "children": []}


def fixture():
    catalog = [{"name": "Alpha", "type": "P", "expression": expression("P"), "module": "Tests", "universes": []},
               {"name": "Beta", "type": "Q", "expression": expression("Q"), "module": "Tests", "universes": []}]
    state = {"goals": [{"target": "P", "expression": expression("P"), "locals": [
        {"name": "h0", "id": "local0", "type": "P", "expression": expression("P")}
    ]}]}
    actions = [{"kind": "exact_lemma", "argument": "Alpha"}, {"kind": "exact_lemma", "argument": "Beta"}]
    return catalog, state, actions


def step(model, optimizer, state, actions):
    model.train()
    scores, value, uncertainty = model(state, actions)
    loss = torch.nn.functional.cross_entropy(scores[None], torch.tensor([0])) + .01 * value.square() + .01 * uncertainty.square()
    optimizer.zero_grad(); loss.backward(); optimizer.step()


def test_real_signatures_influence_rank_without_name_embeddings():
    catalog, state, actions = fixture()
    torch.manual_seed(31); model = PremisePolicy(catalog)
    scores = model.rank(state, actions)
    assert scores[0] != scores[1]
    renamed = [{**e, "name": "Renamed" + e["name"]} for e in catalog]
    other = PremisePolicy(renamed); other.load_state_dict(model.state_dict())
    assert other.rank(state, [{"kind": "exact_lemma", "argument": e["name"]} for e in renamed]) == scores
    assert model.signature(state, {"kind": "exact_local", "argument": "h0"}) == state["goals"][0]["locals"][0]["expression"]
    with pytest.raises(ValueError, match="unknown"):
        model.rank(state, [{"kind": "exact_lemma", "argument": "invented"}])


def test_message_parameters_really_train():
    catalog, state, actions = fixture()
    model = PremisePolicy(catalog)
    before = {n: p.detach().clone() for n, p in model.named_parameters()}
    optimizer = torch.optim.Adam(model.parameters(), lr=.01)
    step(model, optimizer, state, actions)
    for name in ["tokens.weight", "message.weight", "update.weight", "edge_types.weight"]:
        assert not torch.equal(before[name], dict(model.named_parameters())[name])


def test_safe_json_checkpoint_catalog_binding(tmp_path):
    catalog, state, actions = fixture(); model = PremisePolicy(catalog)
    path = tmp_path / "weights.json"; sha = model.save(path, {"authority": False})
    assert PremisePolicy.load(path, sha, catalog).rank(state, actions) == model.rank(state, actions)
    with pytest.raises(ValueError, match="different theorem catalog"):
        PremisePolicy.load(path, sha, catalog[::-1])
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="integrity"):
        PremisePolicy.load(path, sha, catalog)


def test_resume_adam_matches_uninterrupted_next_gradient(tmp_path):
    catalog, state, actions = fixture(); torch.manual_seed(79)
    model = PremisePolicy(catalog); optimizer = torch.optim.Adam(model.parameters(), lr=.002)
    step(model, optimizer, state, actions)
    path = tmp_path / "resume.json"; sha = save_training_checkpoint(path, model, optimizer, {"step": 1})
    expected_random = torch.randperm(10)
    step(model, optimizer, state, actions)
    resumed, resumed_optimizer, progress = load_training_checkpoint(path, sha, catalog)
    assert progress == {"step": 1}
    assert torch.equal(torch.randperm(10), expected_random)
    step(resumed, resumed_optimizer, state, actions)
    assert all(torch.equal(v, resumed.state_dict()[k]) for k, v in model.state_dict().items())


def test_forged_optimizer_moment_rejected(tmp_path):
    catalog, state, actions = fixture(); model = PremisePolicy(catalog)
    optimizer = torch.optim.Adam(model.parameters()); step(model, optimizer, state, actions)
    path = tmp_path / "resume.json"; save_training_checkpoint(path, model, optimizer, {})
    payload = json.loads(path.read_text()); payload["optimizer"]["state"]["0"]["exp_avg"] = [float("nan")]
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="moment"):
        load_training_checkpoint(path, hashlib.sha256(path.read_bytes()).hexdigest(), catalog)


def test_rewrite_direction_and_occurrence_are_action_features():
    catalog, state, _ = fixture(); torch.manual_seed(97)
    model = PremisePolicy(catalog)
    actions = [{"kind": "rewrite_lemma", "argument": {"name": "Alpha", "direction": direction, "occurrence": occurrence}}
               for direction, occurrence in [("forward", 1), ("backward", 1), ("forward", 2)]]
    scores = model.rank(state, actions)
    assert scores[0] != scores[1]
    assert scores[0] != scores[2]


def test_actual_conjunction_projections_resolve_grounded_types():
    catalog, state, _ = fixture(); model = PremisePolicy(catalog)
    p, q = expression("P"), expression("Q")
    application = lambda fn, arg: {"kind": "application", "value": "", "children": [fn, arg]}
    state["goals"][0]["locals"][0]["expression"] = application(application(expression("And"), p), q)
    assert model.signature(state, {"kind": "exact_local", "argument": "h0.1"}) == p
    assert model.signature(state, {"kind": "apply_local", "argument": "h0.2"}) == q
    with pytest.raises(ValueError, match="unknown"):
        model.signature(state, {"kind": "exact_local", "argument": "h0.3"})
