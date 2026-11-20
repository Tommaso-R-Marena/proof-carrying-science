import copy
import unittest

from research.proof_carrying_causal_reasoning_v1.external import (
    typed_language_scoped as checked,
)
from research.proof_carrying_causal_reasoning_v1.external import (
    typed_language_v2 as interim,
)
from research.proof_carrying_causal_reasoning_v1.external.typed_language import CLOSED


class Feasibility(unittest.TestCase):
    def test_choke_point_marginal(self):
        story = {
            "background": CLOSED
            + "Rain has a direct effect on flow. Flow has a direct effect on lamp.",
            "given_info": "The overall probability of rain is 50%. The probability of rain and lamp is 40%. The probability of not rain and lamp is 10%. The overall probability of flow is 0%.",
            "question": "Is the chance of lamp larger when observing rain?",
        }
        self.assertEqual(interim.predict(story)["prediction"], "yes")
        self.assertEqual(
            checked.predict(story)["reason"], "additional_probability_constraints"
        )

    def test_independent_replay_witness_routing_and_mutations(self):
        source = {
            "background": "",
            "given_info": "The overall probability of rain is 50%. The probability of rain and not lamp is 40%. The probability of not rain and not lamp is 10%.",
            "question": "Is the chance of not lamp larger when observing rain?",
        }
        for bg in [
            "",
            CLOSED
            + "Lamp has a direct effect on flow. Flow has a direct effect on rain.",
            CLOSED
            + "Rain has a direct effect on flow. Flow has a direct effect on lamp.",
            CLOSED
            + "Season has a direct effect on storm and current. Current has a direct effect on rain. Storm has a direct effect on lamp. Season is unobserved.",
        ]:
            story = {**source, "background": bg}
            answer = checked.predict(story)
            self.assertEqual(answer["prediction"], "yes")
            claim = interim.interpret(story)
            rows = answer["feasibility_witness"]
            self.assertTrue(checked.verify_model(claim, rows))
            wrong = copy.deepcopy(rows)
            for r in wrong:
                r["p1"] = ["0"] * len(r["p1"])
            self.assertFalse(checked.verify_model(claim, wrong))
            self.assertFalse(checked.verify_model(claim, rows[1:]))
            self.assertFalse(
                checked.verify_model(claim, [dict(r, unknown=1) for r in rows])
            )

    def test_independent_mixture_and_signed_randomization(self):
        story = {
            "background": CLOSED
            + "Cold is an isolated node. Rain is an isolated node.",
            "given_info": "The overall probability of cold is 30%. Among cold, the probability of rain is 80%. Among not cold, the probability of rain is 80%.",
            "question": "Is rain more likely than not rain overall?",
        }
        self.assertEqual(checked.predict(story)["prediction"], "yes")
        bad = {
            **story,
            "given_info": story["given_info"].replace(
                "is 80%. Among not", "is 60%. Among not"
            ),
        }
        self.assertIsNone(checked.predict(bad)["prediction"])
        story = {
            "background": "Treatment cold was randomized.",
            "given_info": "Among cold, the probability of rain is 67%. Among not cold, the probability of rain is 43%.",
            "question": "Will not cold increase the chance of rain?",
        }
        self.assertEqual(checked.predict(story)["prediction"], "no")
        self.assertIsNone(
            checked.predict(
                {
                    **story,
                    "background": story["background"]
                    + " Treatment rain was randomized.",
                }
            )["prediction"]
        )
