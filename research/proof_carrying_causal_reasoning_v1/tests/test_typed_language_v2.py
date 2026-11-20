import unittest

from research.proof_carrying_causal_reasoning_v1.external import (
    typed_language as frozen,
)
from research.proof_carrying_causal_reasoning_v1.external import (
    typed_language_v2 as current,
)


def result(bg, facts, question, parser=current):
    return parser.predict({"background": bg, "given_info": facts, "question": question})


DAG = frozen.CLOSED + "Switch has a direct effect on lamp."
ARMS = "Among switch, the probability of lamp is 85%. Among not switch, the probability of lamp is 15%."
Q = "Will switch increase the chance of lamp?"


class ClosedScope(unittest.TestCase):
    def test_reviewed_false_positives(self):
        external = ARMS.replace("lamp", "rain")
        for bg, info, q in [
            (
                DAG + " Treatment switch was randomized.",
                external,
                Q.replace("lamp", "rain"),
            ),
            (
                DAG,
                "The overall probability of rain is 85%.",
                "Is rain more likely than not rain overall?",
            ),
            (DAG, ARMS + " The overall probability of rain is 45%.", Q),
            (
                "",
                "The overall probability of not not rain is 50%. The probability of not not rain and rain is 5%. The probability of not rain and rain is 45%.",
                "Is the chance of rain larger when observing not not rain?",
            ),
        ]:
            self.assertIsNotNone(result(bg, info, q, frozen)["prediction"])
            self.assertIsNone(result(bg, info, q)["prediction"])

    def test_all_roles_checked(self):
        self.assertEqual(result(DAG, ARMS, Q)["prediction"], "yes")
        for info in (
            ARMS.replace("not switch", "not absent"),
            ARMS.replace("lamp", "rain"),
            ARMS + " The overall probability of not absent is 10%.",
        ):
            self.assertEqual(
                result(DAG, info, Q)["reason"], "undeclared_graph_variable"
            )
        self.assertEqual(
            result(DAG + " Absent is unobserved.", ARMS, Q)["reason"],
            "undeclared_graph_variable",
        )
        self.assertEqual(
            result(DAG + " Treatment not absent was randomized.", ARMS, Q)["reason"],
            "undeclared_graph_variable",
        )
        self.assertIsNone(result(DAG + " Lamp is unobserved.", ARMS, Q)["prediction"])
        self.assertIsNone(
            result(DAG + " Treatment not lamp was randomized.", ARMS, Q)["prediction"]
        )
        self.assertIsNone(
            result(DAG + " Lamp is an isolated node.", ARMS, Q)["prediction"]
        )

    def test_isolated_and_polarity(self):
        bg = DAG + " Rain is an isolated variable."
        marg = "The overall probability of not rain is 85%."
        a = result(bg, marg, "Is not rain more likely than rain overall?")
        self.assertEqual(a["prediction"], "yes")
        self.assertIn({"variable": "rain", "positive": False}, a["bindings"])
        self.assertIn("rain", a["declared_nodes"])
        self.assertEqual(
            result(bg, ARMS.replace("lamp", "rain"), Q.replace("lamp", "rain"))[
                "reason"
            ],
            "graph_probability_conflict",
        )
        a = result(
            DAG + " Treatment switch was randomized.",
            ARMS,
            Q.replace("Will switch", "Will not switch"),
        )
        self.assertEqual(a["prediction"], "no")
        self.assertEqual(
            result(
                frozen.CLOSED + "Not switch has a direct effect on switch.", ARMS, Q
            )["reason"],
            "invalid_graph",
        )

    def test_reject_qualifiers_and_inconsistent_distractors(self):
        for word in ("sometimes", "probably", "assuming fog", "when wet", "does not"):
            name = "switch " + word
            self.assertIsNone(
                result(
                    "Treatment " + name + " was randomized.",
                    ARMS.replace("switch", name),
                    Q.replace("switch", name),
                )["prediction"]
            )
        self.assertIsNone(
            result(
                "Treatment switch was randomized.",
                ARMS
                + " The overall probability of rain is 85%. The overall probability of not rain is 75%.",
                Q,
            )["prediction"]
        )
        self.assertIsNone(
            result(DAG + " Switch affects lamp only on Tuesday.", ARMS, Q)["prediction"]
        )
        self.assertIsNone(
            result(DAG + " Switch has a direct effect on lamp when wet.", ARMS, Q)[
                "prediction"
            ]
        )
