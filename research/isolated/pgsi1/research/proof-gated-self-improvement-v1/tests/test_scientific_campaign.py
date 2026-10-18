"""Reproducibility, information separation and gate invariants for proposal search."""

import itertools
import random
import unittest
from unittest.mock import patch
from proof_gate import Model, check
from scientific_campaign import learn, proposal, run_rollout, ARMS, SEED


class ProposalEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.models = [
            Model(*p)
            for p in itertools.product((False, True), range(-3, 5), range(-3, 5))
        ]
        cls.policy = {
            (a, b): check(a, b).accepted
            for a, b in itertools.product(cls.models, repeat=2)
        }

    def test_deterministic_learning_and_frozen_counts(self):
        a = learn(self.models, list(range(12)), self.policy)
        b = learn(self.models, list(range(12)), self.policy)
        self.assertEqual(a, b)
        self.assertGreater(a["training_proposals"], 0)
        self.assertGreater(sum(abs(x - y) for x, y in a["beta_counts"]), 0)

    def test_operator_bounds_and_exact_candidate_types(self):
        rng = random.Random(SEED)
        for m in self.models:
            for arm in ARMS:
                candidate = proposal(m, arm, rng, self.models)
                self.assertIn(candidate, self.models)

    def test_heldout_metric_cannot_change_proposals_or_accepted_path(self):
        args = (
            Model(True, 0, 0),
            self.models,
            self.policy,
            [[2, 9]] * 5,
            "trained_online",
            SEED,
            80,
        )
        original = run_rollout(*args)
        with patch("scientific_campaign.heldout", return_value=-123456789):
            changed = run_rollout(*args)
        self.assertEqual(original["events"], changed["events"])
        self.assertEqual(original["final"], changed["final"])

    def test_every_strategy_obeys_fixed_gate_after_prior_modifications(self):
        for strategy in [
            "local_coordinate",
            "random_model",
            "uniform_operators",
            "trained_frozen",
            "trained_online",
            "shuffled_credit",
        ]:
            for start in self.models[::17]:
                result = run_rollout(
                    start, self.models, self.policy, [[1, 1]] * 5, strategy, SEED, 50
                )
                current = start
                for event in result["events"]:
                    from sealed_inference import decode_sealed_model

                    candidate = decode_sealed_model(event["candidate"].encode("ascii"))
                    self.assertEqual(event["accepted"], self.policy[current, candidate])
                    if event["accepted"]:
                        current = candidate
                self.assertEqual(result["final"], vars(current))
                self.assertLessEqual(result["accepted"], 7)

    def test_negative_control_rejects_every_update(self):
        reject = {pair: False for pair in self.policy}
        start = Model(True, 0, 0)
        r = run_rollout(
            start, self.models, reject, [[1, 1]] * 5, "trained_online", SEED, 40
        )
        self.assertEqual(r["accepted"], 0)
        self.assertEqual(r["rejected"], 40)
        self.assertEqual(r["final"], vars(start))

    def test_single_coordinate_obstruction_is_not_a_lack_of_joint_improvement(self):
        zero = Model(True, 0, 0)
        single = [
            Model(True, -1, 0),
            Model(True, 1, 0),
            Model(True, 0, -1),
            Model(True, 0, 1),
            Model(False, 0, 0),
        ]
        self.assertTrue(all(not self.policy[zero, m] for m in single))
        self.assertTrue(self.policy[zero, Model(True, 1, 1)])


if __name__ == "__main__":
    unittest.main()
