"""Authored examples for bounded scientific extraction; no benchmark labels."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from .interpretation import Unsupported, interpret, parse_expression, render_expression


class InterpretationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def inventory(self, files):
        artifacts = []
        for index, (name, content) in enumerate(files.items()):
            raw = content.encode() if isinstance(content, str) else content
            path = self.root / str(index)
            path.write_bytes(raw)
            artifacts.append({"id": "artifact-" + str(index), "path": name, "size": len(raw),
                              "sha256": hashlib.sha256(raw).hexdigest(), "snapshot_path": str(path),
                              "segments": [{"text": "forged source not present in bytes", "kind": "text_line", "locator": {"line": 1}}]})
        return {"artifacts": artifacts}

    def assert_bound(self, result, inventory):
        artifacts = {artifact["id"]: artifact for artifact in inventory["artifacts"]}
        for category in result.values():
            for item in category:
                self.assertFalse(item["authority"])
                self.assertEqual(item["status"], "CANDIDATE_INTERPRETATION")
                self.assertEqual(item["meaning_status"], "MEANING_REVIEW_REQUIRED")
                source = item["source"]
                self.assertEqual(source["sha256"], artifacts[source["artifact_id"]]["sha256"])
                raw = Path(artifacts[source["artifact_id"]]["snapshot_path"]).read_text(encoding="utf-8-sig")
                self.assertEqual(raw[source["locator"]["char_start"]:source["locator"]["char_end"]], source["quote"])

    def test_arithmetic_ir_never_evaluates_calls(self):
        expression = "sum(100*(x[1:]-x[:-1]**2)**2+(1-x[:-1])**2)"
        ir = parse_expression(expression)
        self.assertEqual(ir["op"], "call")
        self.assertEqual(ir, parse_expression(render_expression(ir)))
        for bad in ("__import__('os').system('touch /tmp/forbidden')", "open('x')", "x.__class__", "[x for x in y]", "lambda: 3", "1e9999", "f(**x)"):
            with self.subTest(bad=bad), self.assertRaises(Unsupported):
                parse_expression(bad)

    def test_python_returns_and_document_doctests(self):
        inventory = self.inventory({"objective.py": "import numpy as np\ndef objective(x):\n    return np.sum(100*(x[1:]-x[:-1]**2)**2+(1-x[:-1])**2, axis=0)\n",
                                    "tutorial.rst": "Example::\n\n    >>> def energy(x):\n    ...     return x**2 + 3*x\n\nCurrent function value: 0.0001\nIterations: 7\n"})
        result = interpret(inventory)
        equations = result["equations"]
        self.assertEqual({equation["function"] for equation in equations}, {"objective", "energy"})
        self.assertEqual(equations[0]["rhs"]["keywords"], {"axis": 0})
        self.assertTrue(all(equation["execution"] == "NEVER" for equation in equations))
        self.assertEqual(result["dependencies"][0]["module"], "numpy")
        self.assertTrue(any(claim["kind"] == "numerical_result" for claim in result["claims"]))
        self.assert_bound(result, inventory)

    def test_tables_source_values_and_unknown_units(self):
        inventory = self.inventory({"data.csv": "time (s),signal [mM],mass (furlongs)\n0,1.2,3\n2,2.4,5\n",
                                    "notes.md": "| Time (s) | Signal (µM) |\n| --- | --- |\n| 1 | 2.5 |\n"})
        result = interpret(inventory)
        self.assertEqual(result["tables"][0]["row_count"], 2)
        self.assertEqual(result["tables"][0]["rows"][1]["values"]["signal [mM]"], "2.4")
        unknown = [quantity for quantity in result["quantities"] if quantity["name"] == "mass"]
        self.assertEqual(unknown[0]["unit_status"], "UNKNOWN")
        self.assertTrue(any(quantity["unit"] == "uM" for quantity in result["quantities"]))
        self.assert_bound(result, inventory)
        # The output changes with source bytes; forged adapter observations do
        # not supply the numeric value or preserve the previous interpretation.
        altered = self.inventory({"data.csv": "time (s),signal [mM]\n0,9.9\n"})
        new_result = interpret(altered)
        self.assertEqual([q["value"] for q in new_result["quantities"] if q["name"] == "signal"], ["9.9"])
        self.assertNotEqual(result["tables"][0]["id"], new_result["tables"][0]["id"])

    def test_uncertainty_approximation_and_causal_abstention(self):
        inventory = self.inventory({"results.md": "The measured concentration was approximately 2.4 ± 0.2 μM.\nTreatment causes recovery.\n$$dx/dt = -k*x$$\nThe reported value was 4 blorgs.\n"})
        result = interpret(inventory)
        quantity = next(q for q in result["quantities"] if q["value"] == "2.4")
        self.assertTrue(quantity["approximate"])
        self.assertEqual(quantity["uncertainty"]["value"], "0.2")
        self.assertEqual(quantity["unit"], "uM")
        self.assertTrue(any("Causal" in unresolved["reason"] for unresolved in result["unresolved"]))
        self.assertTrue(any(equation["lhs"]["op"] == "derivative" for equation in result["equations"] if equation["lhs"]))
        self.assertEqual(next(q for q in result["quantities"] if q["unit"] == "blorgs")["unit_status"], "UNKNOWN")
        self.assert_bound(result, inventory)

    def test_sbml_parameters_rules_kinetics_stoichiometry_and_units(self):
        sbml = '''<?xml version="1.0"?>
<sbml xmlns="http://www.sbml.org/sbml/level3/version2/core" level="3" version="2">
 <model id="toy" timeUnits="second" substanceUnits="mole">
  <listOfUnitDefinitions><unitDefinition id="per_second"><listOfUnits><unit kind="second" exponent="-1" scale="0" multiplier="1"/></listOfUnits></unitDefinition></listOfUnitDefinitions>
  <listOfCompartments><compartment id="cell" size="2" units="litre" constant="true"/></listOfCompartments>
  <listOfSpecies><species id="S" compartment="cell" initialAmount="3" hasOnlySubstanceUnits="true"/><species id="P" compartment="cell" initialAmount="0" hasOnlySubstanceUnits="true"/></listOfSpecies>
  <listOfParameters><parameter id="k" value="0.5" units="per_second" constant="true"/></listOfParameters>
  <listOfRules><rateRule variable="S"><math xmlns="http://www.w3.org/1998/Math/MathML"><apply><minus/><apply><times/><ci>k</ci><ci>S</ci></apply></apply></math></rateRule></listOfRules>
  <listOfReactions><reaction id="r" reversible="false"><listOfReactants><speciesReference species="S" stoichiometry="2"/></listOfReactants><listOfProducts><speciesReference species="P"/></listOfProducts><kineticLaw><math xmlns="http://www.w3.org/1998/Math/MathML"><apply><times/><ci>k</ci><ci>S</ci></apply></math><listOfLocalParameters><localParameter id="a" value="5"/></listOfLocalParameters></kineticLaw></reaction></listOfReactions>
 </model>
</sbml>'''
        inventory = self.inventory({"toy.sbml": sbml})
        result = interpret(inventory)
        self.assertEqual(len(result["equations"]), 2)
        derivative = next(equation for equation in result["equations"] if equation["origin"] == "sbml_rateRule")
        self.assertEqual(derivative["lhs"], {"op": "derivative", "state": "S", "variable": "time"})
        self.assertEqual(derivative["symbol_units"]["k"], "s**-1")
        self.assertEqual(derivative["symbol_units"]["S"], "mol")
        self.assertEqual(result["tables"][0]["rows"][1]["coefficient_origin"], "SBML_default_one")
        self.assertEqual(next(q for q in result["quantities"] if q["name"] == "a")["unit_status"], "UNSPECIFIED")
        self.assert_bound(result, inventory)

    def test_no_silent_unit_invention_or_summation_scope(self):
        inventory = self.inventory({"unknown.sbml": '<sbml><model id="m"><listOfSpecies><species id="S" initialAmount="2"/></listOfSpecies></model></sbml>',
                                    "formula.rst": '.. math::\n\n    f(x) = \\sum_{i=1}^{n} x_i^2 + b\n\n'})
        result = interpret(inventory)
        self.assertIsNone(next(q for q in result["quantities"] if q["name"] == "S")["unit"])
        self.assertTrue(any(equation["parse_status"] == "UNRESOLVED" for equation in result["equations"]))
        self.assertTrue(any("scope" in unresolved["reason"] for unresolved in result["unresolved"]))

    def test_invalid_syntax_entities_and_changed_source(self):
        inventory = self.inventory({"bad.py": "def x(:\n", "unsafe.xml": '<!DOCTYPE a [<!ENTITY x "expanded">]><sbml>&x;</sbml>',
                                    "bad.csv": "x,x\n1,2\n"})
        result = interpret(inventory)
        self.assertGreaterEqual(len(result["unresolved"]), 3)
        self.assertFalse(result["equations"])
        changed = self.inventory({"changed.md": "mass = 1 kg\n"})
        Path(changed["artifacts"][0]["snapshot_path"]).write_text("mass = 2 kg\n")
        result = interpret(changed)
        self.assertFalse(result["quantities"])
        self.assertIn("changed", result["unresolved"][0]["reason"])

    def test_deterministic_ids_and_json_values(self):
        inventory = self.inventory({"math.md": "$E = m*c^2$\nMeasured mass: 2 kg\n"})
        result = interpret(inventory)
        self.assertEqual(result, interpret(inventory))
        json.dumps(result, allow_nan=False)

    def test_html_mathml_compound_units_and_reported_interval(self):
        inventory = self.inventory({"paper.html": '<p>The measured rate was 2.0 s^-1 (95% CI [1.7, 2.3]).</p>\n<math xmlns="http://www.w3.org/1998/Math/MathML"><apply><eq/><ci>E</ci><apply><times/><ci>m</ci><apply><power/><ci>c</ci><cn>2</cn></apply></apply></apply></math>'})
        result = interpret(inventory)
        rate = next(q for q in result["quantities"] if q["value"] == "2.0")
        self.assertEqual(rate["unit"], "s^-1")
        self.assertEqual(rate["uncertainty"]["kind"], "reported_confidence_interval")
        self.assertEqual(rate["uncertainty"]["confidence_level_percent"], "95")
        self.assertEqual(rate["relation"], "uncertainty_interval")
        equation = next(e for e in result["equations"] if e["origin"] == "html_mathml")
        self.assertEqual(equation["lhs"], {"op": "symbol", "name": "E"})
        self.assertEqual(equation["relation"], "eq")
        self.assert_bound(result, inventory)

    def test_xml_resource_bounds_and_duplicate_symbol_scope(self):
        too_deep = '<sbml>' + '<a>' * 50 + '</a>' * 50 + '</sbml>'
        duplicate = '<sbml><model><listOfParameters><parameter id="k" value="1"/><parameter id="k" value="2"/></listOfParameters></model></sbml>'
        inventory = self.inventory({"deep.xml": too_deep, "duplicate.sbml": duplicate})
        result = interpret(inventory)
        self.assertTrue(any("resource bound" in item["reason"] for item in result["unresolved"]))
        self.assertTrue(any("Duplicate global" in item["reason"] for item in result["unresolved"]))
        self.assertFalse(result["quantities"])

    def test_document_findings_have_canonical_types_without_invented_dimensions(self):
        inventory = self.inventory({"findings.rst": "The minimum value of this function is 0 which is achieved at x=1.\nCurrent function value: approximately 2.0 ± 0.1\nIterations: 12 # may vary\nFunction evaluations: 25\nGradient evaluations: 3 # may differ\nThe minimum value of temperature is 273 K.\n"})
        result = interpret(inventory)
        quantities = {q["name"]: q for q in result["quantities"] if q.get("role") == "document_numerical_result"}
        self.assertEqual(quantities["minimum_objective"]["raw_name"], "minimum value of this function")
        self.assertEqual(quantities["minimum_objective"]["quantity_type"], "objective_value")
        self.assertIsNone(quantities["minimum_objective"]["unit"])
        objective = quantities["reported_objective"]
        self.assertTrue(objective["approximate"])
        self.assertEqual(objective["uncertainty"]["value"], "0.1")
        self.assertIsNone(objective["unit"])
        for name in ("iterations", "function_evaluations", "gradient_evaluations"):
            self.assertEqual(quantities[name]["unit"], "count")
            self.assertEqual(quantities[name]["quantity_type"], "count")
            self.assertTrue(quantities[name]["version_sensitive"])
        self.assertTrue(quantities["iterations"]["reported_variability"]["may_vary"])
        self.assertFalse(quantities["function_evaluations"]["reported_variability"]["may_vary"])
        self.assertEqual(quantities["reported_minimum"]["unit"], "K")
        self.assert_bound(result, inventory)

    def test_findings_retain_only_unique_local_solver_context(self):
        text = "    >>> from scipy.optimize import minimize as fit\n    >>> result = fit(objective, x0, method='nelder-mead',\n    ...              options={'xatol': 1e-8})\n    Current function value: 0.000000\n    Iterations: 42 # may vary\n\nAn unrelated paragraph.\nFunction evaluations: 99\n\n    >>> other = fit(objective, x0, method=selected_method)\n    Iterations: 43\n\n    >>> result = fit(f, x0) + fit(g, x1)\n    Iterations: 44\n"
        inventory = self.inventory({"context.rst": text})
        result = interpret(inventory)
        findings = [q for q in result["quantities"] if q.get("role") == "document_numerical_result"]
        first = next(q for q in findings if q["name"] == "iterations" and q["value"] == "42")
        context = first["solver_context"]
        self.assertEqual(context["solver"], "scipy.optimize.minimize")
        self.assertEqual(context["method"], "nelder-mead")
        self.assertEqual(context["objective_or_rhs"], "objective")
        self.assertIn("xatol", context["keyword_expressions"][1]["expression"])
        self.assertIn("fit(objective", context["source"]["quote"])
        self.assertIsNone(next(q for q in findings if q["value"] == "99")["solver_context"])
        self.assertIsNone(next(q for q in findings if q["value"] == "43")["solver_context"]["method"])
        self.assertIsNone(next(q for q in findings if q["value"] == "44")["solver_context"])
        self.assert_bound(result, inventory)

    def test_reported_count_uncertainty_is_not_exact_equality(self):
        inventory = self.inventory({"counts.txt": "Iterations: about 10 ± 2 # may vary\nFunction evaluations: 20 (95% CI [18, 23])\n"})
        result = interpret(inventory)
        quantities = {q["name"]: q for q in result["quantities"] if q.get("role") == "document_numerical_result"}
        self.assertEqual(quantities["iterations"]["relation"], "approximate")
        self.assertEqual(quantities["iterations"]["uncertainty"], {"kind": "plus_minus", "value": "2", "unit": "count"})
        interval = quantities["function_evaluations"]
        self.assertEqual(interval["relation"], "uncertainty_interval")
        self.assertEqual(interval["uncertainty"]["lower"], "18")
        self.assertEqual(interval["uncertainty"]["unit"], "count")
        self.assertTrue(all(q["conditions"] for q in quantities.values()))


if __name__ == "__main__":
    unittest.main()
