"""Information-set and replay controls, runnable without the external dataset."""

import copy
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from research.proof_carrying_causal_reasoning_v1.external import blind_eval as evaluator
from research.proof_carrying_causal_reasoning_v1.external import (
    blind_predict as predictor,
)
from research.proof_carrying_causal_reasoning_v1.external import finite_replay as replay


def fixture():
    question = {
        "question_id": 17,
        "answer": "yes",
        "given_info": (
            "The overall probability of treatment is 50%. "
            "For patients not receiving treatment, the probability of recovery is 63%. "
            "For patients receiving treatment, the probability of recovery is 87%."
        ),
        "question": "Is recovery more likely than non-recovery overall?",
        "meta": {
            "query_type": "ate",
            "model_id": 3,
            "treated": True,
            "polarity": True,
            "result": True,
            "groundtruth": 1,
        },
    }
    model = {
        "background": "A binary world.",
        "structure": "X->Y",
        "equation_type": "bernoulli",
        "params": {"p(X)": 0.5, "p(Y | X)": [0.2, 0.7]},
        "groundtruth": {"ATE": 1},
    }
    return question, model


class BlindTests(unittest.TestCase):
    def test_backdoor_witness_order_independent_of_hash_seed(self):
        code = """from research.proof_carrying_causal_reasoning_v1.kernel.dag import CausalDAG
from research.proof_carrying_causal_reasoning_v1.kernel.backdoor import verify_backdoor_set
graph = CausalDAG.from_parents({'X':['M','N'], 'Y':['M','N'], 'M':[], 'N':[]})
print(verify_backdoor_set(graph,'X','Y',[]).reasons)
"""
        outputs = {
            subprocess.check_output(
                [sys.executable, "-c", code],
                env=dict(os.environ, PYTHONHASHSEED=str(seed)),
            )
            for seed in range(6)
        }
        self.assertEqual(len(outputs), 1)

    def test_closed_form_confounder_ate(self):
        # Independent formula for confounding: weight two stratum differences
        # by P(Z), not by treatment-specific P(Z|X).
        q, m = fixture()
        m.update(
            structure="Z->X,Z->Y,X->Y",
            params={
                "p(Z)": [0.25],
                "p(X | Z)": [0.9, 0.1],
                "p(Y | X, Z)": [[0.125, 0.5], [0.625, 0.25]],
            },
        )
        problem = evaluator.project(q, m, "B")
        cert = predictor.predict("B", 17, problem)["certificate"]
        self.assertEqual(cert["effect"], "5/16")
        self.assertTrue(replay.verify(17, problem, replay.canonical(cert)))
        for key, value in (
            ("assumptions", "unqualified"),
            ("direction", "decrease"),
            ("outcome", "Z"),
            ("treatment", "Z"),
        ):
            self.assertFalse(
                replay.verify(17, dict(problem, **{key: value}), replay.canonical(cert))
            )

    def test_hidden_fields_never_enter_wire_or_change_prediction(self):
        q, m = fixture()
        for protocol in ("A", "B"):
            public = evaluator.project(q, m, protocol)
            altered = copy.deepcopy(q)
            altered.update(answer="SENTINEL", reasoning={"private": "SENTINEL"})
            altered["meta"]["groundtruth"] = {"nested": ["SENTINEL"]}
            self.assertEqual(
                public,
                evaluator.project(altered, dict(m, groundtruth="SENTINEL"), protocol),
            )
            del altered["meta"]["groundtruth"]
            self.assertEqual(public, evaluator.project(altered, m, protocol))
            self.assertNotIn("SENTINEL", repr(public))
            self.assertEqual(
                predictor.predict(protocol, 17, public)["prediction"], "yes"
            )

    def test_missing_or_extra_structure_abstains(self):
        q, m = fixture()
        for change in (
            {"params": {}},
            {"structure": "X->Y,Y->X"},
            {"params": {"p(X)": 0.4, "p(Y | X)": [0.2, {"hidden": "label"}]}},
            {"structure": "X->Y,garbage"},
            {"params": {"p(X)": 0.1, "p(Y)": 0.7}},
        ):
            public = evaluator.project(q, dict(m, **change), "B")
            self.assertIsNone(predictor.predict("B", 17, public)["prediction"])
        q["given_info"] = {"hidden": "label"}
        self.assertIsNone(
            predictor.predict("A", 17, evaluator.project(q, m, "A"))["prediction"]
        )

    def test_legitimate_input_changes_decision(self):
        q, m = fixture()
        m["params"]["p(Y | X)"] = [0.9, 0.2]
        self.assertEqual(
            predictor.predict("B", 17, evaluator.project(q, m, "B"))["prediction"], "no"
        )
        q["given_info"] = q["given_info"].replace("63%", "16%").replace("87%", "24%")
        self.assertEqual(
            predictor.predict("A", 17, evaluator.project(q, m, "A"))["prediction"], "no"
        )

    def test_oracle_depends_on_hidden_counterfactual_bit(self):
        from research.proof_carrying_causal_reasoning_v1.external.cladder_certified_solver import (
            solve_question,
        )

        q, m = fixture()
        q["meta"]["query_type"] = "det-counterfactual"
        q["meta"]["groundtruth"] = 1
        self.assertEqual(solve_question(q, m)["pred"], "yes")
        q["meta"]["groundtruth"] = 0
        self.assertEqual(solve_question(q, m)["pred"], "no")

    def test_complete_structured_replay_rejects_dropped_rows(self):
        q, m = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            public, rows = Path(tmp) / "input", Path(tmp) / "predictions"
            evaluator.prepare([q], {3: m}, "B", public)
            digest = predictor.freeze(public, rows)
            import hashlib
            import json

            p = public.read_bytes()
            h = replay.digest(json.loads(p))
            self.assertEqual(
                replay.replay_frozen(p, rows.read_bytes(), h, digest)[
                    "accepted_certificates"
                ],
                1,
            )
            forged = json.loads(rows.read_bytes())
            forged["rows"] = []
            raw = replay.canonical(forged) + b"\n"
            with self.assertRaises(ValueError):
                replay.replay_frozen(p, raw, h, hashlib.sha256(raw).hexdigest())

    def test_strict_certificate_binding(self):
        q, m = fixture()
        problem = evaluator.project(q, m, "B")
        cert = predictor.predict("B", 17, problem)["certificate"]
        frozen = replay.canonical(cert)
        self.assertTrue(replay.verify(17, problem, frozen))
        self.assertFalse(replay.verify(18, problem, frozen))
        for change in (
            {"effect": "1/2", "p_do0": "0"},
            {"theorem": "fake"},
            {"schema": "other"},
            {"p_do1": 0.7},
            {"prediction": "no"},
            {"source_sha256": "0" * 64},
        ):
            self.assertFalse(
                replay.verify(17, problem, replay.canonical(dict(cert, **change)))
            )
        for replacement in (
            {"structure": "Y->X"},
            {"params": {"p(X)": 0.6, "p(Y | X)": [0.2, 0.7]}},
        ):
            self.assertFalse(
                replay.verify(
                    17, evaluator.project(q, dict(m, **replacement), "B"), frozen
                )
            )
        self.assertFalse(replay.verify(17, problem, b'{"x":0,"x":1}'))
        self.assertFalse(replay.verify(17, problem, frozen + b" "))

    def test_freeze_before_scoring(self):
        q, m = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            public, rows = Path(tmp) / "input", Path(tmp) / "predictions"
            evaluator.prepare([q], {3: m}, "A", public)
            digest = predictor.freeze(public, rows)
            self.assertEqual(
                evaluator.score([q], {3: m}, public, rows, digest)["overall"][
                    "correct"
                ],
                1,
            )
            self.assertEqual(
                evaluator.score([dict(q, answer="no")], {3: m}, public, rows, digest)[
                    "overall"
                ]["incorrect"],
                1,
            )
            with self.assertRaises(ValueError):
                evaluator.score(
                    [dict(q, question="different")], {3: m}, public, rows, digest
                )
            with self.assertRaises(FileExistsError):
                predictor.freeze(public, rows)
            rows.write_bytes(rows.read_bytes() + b" ")
            with self.assertRaises(ValueError):
                evaluator.score([q], {3: m}, public, rows, digest)
