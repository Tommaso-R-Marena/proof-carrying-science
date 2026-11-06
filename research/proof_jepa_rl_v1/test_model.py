"""Neural-contract unit tests, not affirmative Lean-authorization tests."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import torch
from research.proof_jepa_rl_v1.model import ProofJEPA


def state(name="P"):
    expr = {"kind": "constant", "value": name + ":[]", "children": []}
    return {"goals": [{"expression": expr, "target": name,
                       "locals": [{"name": "h0", "type": name, "expression": expr}]}]}


def records():
    action = {"kind": "exact", "argument": "h0"}
    return [{"state": state(name), "action": action, "next_state": {"goals": []},
             "valid": True, "remaining": 1, "trajectory_id": name, "step": 0,
             "equivalent_state": {"goals": []}, "equivalence_receipt_sha256": "a" * 64,
             "future": [{"action": {"kind": "rfl", "argument": None}, "next_state": {"goals": []}}]}
            for name in ("P", "Q", "R", "Nat")]


class ModelTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(17)
        torch.set_num_threads(1)
        self.model = ProofJEPA()

    def test_predictive_learning_updates_online_not_target(self):
        before = {k: v.clone() for k, v in self.model.named_parameters()}
        optimizer = torch.optim.Adam(self.model.parameters(), lr=.005)
        loss = self.model.predictive_loss(records())
        self.assertTrue(torch.isfinite(loss))
        loss.backward()
        for key in ("online.tokens.weight", "online.message.0.weight", "online.pool.weight", "predictor.0.weight"):
            self.assertGreater(float(dict(self.model.named_parameters())[key].grad.abs().sum()), 0, key)
        self.assertTrue(all(p.grad is None and not p.requires_grad for p in self.model.target.parameters()))
        optimizer.step()
        for key in ("online.tokens.weight", "online.message.0.weight", "predictor.0.weight"):
            self.assertFalse(torch.equal(before[key], dict(self.model.named_parameters())[key]), key)
        for key, p in self.model.named_parameters():
            if key.startswith("target."):
                self.assertTrue(torch.equal(before[key], p), key)
        self.model.update_target(.9)
        online = next(self.model.online.parameters())
        target = next(self.model.target.parameters())
        old = before["target.tokens.weight"]
        self.assertTrue(torch.allclose(target, .9 * old + .1 * online))
        self.assertGreater(self.model.last_predictive_metrics["embedding_std"], 0)

    def test_ordered_expression_and_alpha_normalization(self):
        def constant(name):
            return {"kind": "constant", "value": name, "children": []}
        ordered = {"kind": "application", "value": "", "children": [constant("Nat"), constant("Int")]}
        swapped = copy.deepcopy(ordered)
        swapped["children"].reverse()
        left = {"goals": [{"expression": ordered, "target": "", "locals": []}]}
        right = {"goals": [{"expression": swapped, "target": "", "locals": []}]}
        self.assertFalse(torch.allclose(self.model.encode(left), self.model.encode(right)))
        first = {"goals": [{"expression": {"kind": "local", "value": "_uniq.1", "children": []},
                             "target": "h0", "locals": [{"id": "_uniq.1", "name": "h0", "type": "Pretty h0", "expression": constant("Prop")}]}]}
        renamed = copy.deepcopy(first)
        renamed["goals"][0]["expression"]["value"] = "_uniq.99"
        renamed["goals"][0]["target"] = "h33"
        renamed["goals"][0]["locals"][0].update(id="_uniq.99", name="h33", type="Other h33")
        self.assertTrue(torch.equal(self.model.encode(first), self.model.encode(renamed)))

    def test_action_conditioning_changes_prediction(self):
        s = state()
        h = self.model.encode(s)
        a = self.model.predict(h, s, {"kind": "exact", "argument": "h0"})
        b = self.model.predict(h, s, {"kind": "assumption", "argument": None})
        self.assertFalse(torch.equal(a, b))

    def test_guidance_is_explicit_ablation(self):
        self.model.predictive_loss(records(), proof_guided=False)
        plain = self.model.last_predictive_metrics
        self.assertEqual(plain["multistep_targets"], 0)
        self.assertEqual(plain["equivalence_pairs"], 0)
        self.model.predictive_loss(records(), proof_guided=True)
        self.assertEqual(self.model.last_predictive_metrics["multistep_targets"], 4)
        self.assertEqual(self.model.last_predictive_metrics["equivalence_pairs"], 4)
        bad = records()
        del bad[0]["equivalence_receipt_sha256"]
        with self.assertRaises(ValueError):
            self.model.predictive_loss(bad, proof_guided=True)

    def test_invalid_records_do_not_become_successor_targets(self):
        record = records()[0]
        record.update(valid=False, next_state={"malformed": True}, remaining=None)
        loss = self.model.predictive_loss([record], proof_guided=True)
        self.assertTrue(torch.isfinite(loss))
        self.assertEqual(self.model.last_predictive_metrics["valid_predictions"], 0)
        self.assertGreater(self.model.last_predictive_metrics["invalid_bce"], 0)

    def test_rank_contract_and_no_authorization(self):
        actions = [{"kind": "exact", "argument": "h0"}, {"kind": "assumption", "argument": None}]
        scores = self.model.rank(state(), actions)
        self.assertEqual(len(scores), 2)
        self.assertTrue(all(type(score) is float for score in scores))
        self.assertEqual(self.model.rank(state(), []), [])
        logits, value, invalid = self.model(state(), actions)
        self.assertEqual(tuple(logits.shape), (2,))
        self.assertEqual(tuple(value.shape), ())
        self.assertTrue(((0 <= invalid) & (invalid <= 1)).all())

    def test_checkpoint_roundtrip_and_strict_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            sha = self.model.save(path, {"source": "unit-contract-only"})
            restored = ProofJEPA.load(path, sha)
            for key, value in self.model.state_dict().items():
                self.assertTrue(torch.equal(value, restored.state_dict()[key]))
            payload = json.loads(path.read_text())
            self.assertEqual(payload["authority"], "NONE")
            path.write_bytes(path.read_bytes() + b" ")
            with self.assertRaises(ValueError):
                ProofJEPA.load(path, sha)

    def test_rehashed_malformed_checkpoints_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.json"
            self.model.save(path, {})
            original = json.loads(path.read_text())
            for mutate in (
                lambda p: p.update(authority="PRODUCTION"),
                lambda p: p.update(width=True),
                lambda p: p["weights"].update({"invented.weight": [1.]}),
                lambda p: p["weights"].update({"online.tokens.weight": [1.]}),
                lambda p: p["weights"]["online.tokens.weight"][0].__setitem__(0, True),
                lambda p: p["weights"]["online.tokens.weight"][0].__setitem__(0, float("nan")),
                lambda p: p["weights"]["online.tokens.weight"][0].__setitem__(0, 1e300),
            ):
                payload = json.loads(json.dumps(original))
                mutate(payload)
                raw = json.dumps(payload).encode()
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    ProofJEPA.load(path, hashlib.sha256(raw).hexdigest())
            raw = b'{"format":"one","format":"two"}'
            path.write_bytes(raw)
            with self.assertRaises(ValueError):
                ProofJEPA.load(path, hashlib.sha256(raw).hexdigest())

    def test_empty_and_bad_training_inputs_fail(self):
        with self.assertRaises(ValueError):
            self.model.predictive_loss([])
        bad = records()[0]
        bad["valid"] = 1
        with self.assertRaises(ValueError):
            self.model.predictive_loss([bad])
        for momentum in (-1, 1, float("nan")):
            with self.assertRaises(ValueError):
                self.model.update_target(momentum)
        with self.assertRaises(ValueError):
            self.model.rank(state(), [{"kind": "exact", "argument": "h0; admit"}])


if __name__ == "__main__":
    unittest.main()
