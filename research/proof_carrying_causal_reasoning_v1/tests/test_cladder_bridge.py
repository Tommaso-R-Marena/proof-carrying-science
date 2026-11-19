"""External CLadder bridge unit tests (synthetic mini-models; no zip required)."""

from __future__ import annotations

import unittest

from research.proof_carrying_causal_reasoning_v1.external.cladder_bridge import (
    compute_ate,
    compute_correlation_diff,
    compute_ett,
    evaluate_models,
    scm_from_cladder_params,
)


class TestCladderBridge(unittest.TestCase):
    def test_confounder_ate_ett_separation(self):
        structure = "V1->X,V1->Y,X->Y"
        params = {
            "p(V1)": 0.5,
            "p(X | V1)": [0.25, 0.75],
            "p(Y | V1, X)": [[0.2, 0.4], [0.5, 0.8]],
        }
        scm = scm_from_cladder_params(structure, params)
        ate = compute_ate(scm)
        ett = compute_ett(scm)
        # Confounding ⇒ ETT need not equal ATE.
        self.assertAlmostEqual(ate, 0.25, places=9)  # 0.5*((0.4-0.2)+(0.8-0.5))
        self.assertNotAlmostEqual(ate, ett, places=9)

    def test_no_confounder_ett_equals_ate(self):
        structure = "X->Y"
        params = {"p(X)": 0.5, "p(Y | X)": [0.25, 0.75]}
        # parse needs both nodes — structure X->Y only has X,Y; add via edges
        scm = scm_from_cladder_params("X->Y", {"p(X)": 0.5, "p(Y | X)": [0.25, 0.75]})
        ate = compute_ate(scm)
        ett = compute_ett(scm)
        self.assertAlmostEqual(ate, 0.5, places=9)
        self.assertAlmostEqual(ett, ate, places=9)

    def test_evaluate_models_matches_injected_gt(self):
        structure = "V1->X,V1->Y,X->Y"
        params = {
            "p(V1)": 0.4,
            "p(X | V1)": [0.3, 0.8],
            "p(Y | V1, X)": [[0.1, 0.3], [0.55, 0.9]],
        }
        scm = scm_from_cladder_params(structure, params)
        ate = compute_ate(scm)
        ett = compute_ett(scm)
        models = [
            {
                "model_id": 1,
                "graph_id": "confounding",
                "structure": structure,
                "equation_type": "bernoulli",
                "params": params,
                "groundtruth": {"ATE(Y | X)": ate, "ETT(Y | X)": ett},
            }
        ]
        out = evaluate_models(models, atol=1e-9)
        self.assertTrue(out["ok"])
        self.assertEqual(out["n_ok"], 1)

    def test_correlation_contrast(self):
        scm = scm_from_cladder_params("X->Y", {"p(X)": 0.5, "p(Y | X)": [0.2, 0.7]})
        self.assertAlmostEqual(compute_correlation_diff(scm), 0.5, places=9)


if __name__ == "__main__":
    unittest.main()
