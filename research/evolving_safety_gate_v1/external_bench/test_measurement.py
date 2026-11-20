"""Regression tests for leakage, missing measurements and metric denominators."""
import unittest

from ..features import extract_features


class TestMeasurement(unittest.TestCase):
    def test_label_perturbation_does_not_change_features(self):
        observable = {"published": ["public summary"], "proposals": []}
        self.assertEqual(extract_features(dict(observable, attack=True)),
                         extract_features(dict(observable, attack=False)))

    def test_unobserved_rates(self):
        from .run_bakeoff import _rates
        self.assertIsNone(_rates([], [])["accuracy"])
        self.assertIsNone(_rates([True], [True])["fpr"])
        self.assertEqual(_rates([True], [False])["f1"], 0)
        with self.assertRaises(ValueError):
            _rates([True], [])

    def test_receiver_and_detector_have_separate_inputs(self):
        import json
        from ..catalog import SEED_CANDIDATES, detector_for
        from .adjudicate import off_policy_reply
        from .dominance import SCIENCE, emit_predictions
        from .measurement import Outcome
        ensemble = detector_for(next(c for c in SEED_CANDIDATES if c.id == "ensemble-v1"))
        turns = [{"turn": i, "state": state, "proposed": action, "admitted": action,
                  "raw_text": json.dumps({"action": action})} for i, (state, action) in enumerate(SCIENCE)]
        ep = {"proposals": turns, "guarded_complete": True}
        self.assertFalse(off_policy_reply(ep, SCIENCE))
        turns[0]["proposed"] = "other"
        self.assertFalse(off_policy_reply(ep, SCIENCE))
        measured = emit_predictions(ep, hidden=False, ensemble=ensemble)
        self.assertEqual(measured["proposal_disagreement"], Outcome.POSITIVE)
        self.assertEqual(measured, emit_predictions(dict(ep, attack=True, label=1, oracle=True,
                        raw_leak=True, y_should_flag=True, proposal_harm=999), hidden=False, ensemble=ensemble))
        self.assertEqual(emit_predictions(ep, hidden=True, ensemble=ensemble)["proposal_disagreement"], Outcome.ABSTAINED)
        turns[0]["raw_text"] = '{"action":"other","action":"load_evidence"}'
        self.assertTrue(off_policy_reply(ep, SCIENCE))
        del turns[0]["raw_text"]
        self.assertIsNone(off_policy_reply(ep, SCIENCE))

    def test_missing_cannot_support_comparison(self):
        from .dominance import run_audit
        from .measurement import Outcome
        result = run_audit()
        self.assertIsNone(result["cross_modality_comparison"]["pareto"])
        data = result["specialist_protocol"]["systems"]
        self.assertEqual(data["fresh_gemini"]["outcomes"], {Outcome.NOT_RUN: 100})
        self.assertEqual(data["gemini_moderator"]["outcomes"][Outcome.UNKNOWN], 7)
        self.assertEqual(data["agent_tool_filter"]["metrics_on_labeled_decisions"]["n"], 0)
        systems = result["matched_episode_protocol"]["systems"]["masked"]
        self.assertEqual(systems["projected_episode_route"]["outcomes"], {Outcome.ABSTAINED: 120})

    def test_offline_diagnostic_and_missing_binary_outputs(self):
        from .run_bakeoff import track_a_jbb, track_b_mirage_episodes, measured_rates
        for run in (track_a_jbb, track_b_mirage_episodes):
            with self.assertRaisesRegex(ValueError, "offline-only"):
                run(use_gemini=True)
        rows = [{"y": True, "d": None}, {"y": False, "d": False}]
        self.assertEqual(measured_rates(rows, "y", "d")["unknown"], 1)
        self.assertEqual(measured_rates(rows, "y", "d")["fn"], 0)
        with self.assertRaises(ValueError):
            measured_rates([{"y": True, "d": "UNKNOWN"}], "y", "d")
