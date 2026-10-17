import unittest
from global_falsification import run
from proof_gate import Model, check, target
from universal_relu import single_neuron

class UniversalCampaignTests(unittest.TestCase):
    def test_model_lattice_and_partition_counts(self):
        result = run()
        self.assertEqual(result["models"], 128)
        self.assertEqual(result["transitions_checked"], 16384)
        self.assertEqual(result["original_accepted"], 4081)
        self.assertEqual(result["lost_previously_correct_integer_prediction"], 76)
        self.assertEqual(result["increased_worst_error_on_minus20_to20"], 441)
        self.assertEqual(result["failed_both_stronger_guards"], 12)
        self.assertEqual(result["passed_both_stronger_guards"], 3576)
        self.assertEqual(
            result["original_accepted"],
            result["passed_both_stronger_guards"]
            + result["lost_previously_correct_integer_prediction"]
            + result["increased_worst_error_on_minus20_to20"]
            - result["failed_both_stronger_guards"]
        )

    def test_campaign_witness_is_real_loss_of_correctness(self):
        witness = run()["lost_correct_witness"]
        old = Model(**witness["old"])
        candidate = Model(**witness["candidate"])
        x = witness["lost_correct_input"]
        self.assertTrue(check(old, candidate).accepted)
        self.assertEqual(single_neuron(old.relu, old.weight, old.bias).predict(x),
                         target(x))
        self.assertNotEqual(single_neuron(candidate.relu, candidate.weight,
                                          candidate.bias).predict(x), target(x))

if __name__ == "__main__":
    unittest.main()
