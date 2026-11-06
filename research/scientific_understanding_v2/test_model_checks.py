"""Independent authored checks of bounded model computations; DEV sources only.

These tests establish exact finite algebra/static correspondence, never a
biological verdict, authority, source-program execution or global ODE theorem.
"""
from __future__ import annotations

from fractions import Fraction
from importlib.util import find_spec
from itertools import combinations, permutations, product
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from . import model_checks as checks

DEV = Path(__file__).with_name("fixtures") / "upstream"
NS = "http://www.sbml.org/sbml/level2/version4"


def toy_raw() -> bytes:
    return b'''<sbml xmlns="http://www.sbml.org/sbml/level2/version4" level="2" version="4"><model id="toy"><listOfCompartments><compartment id="cell" size="2" constant="true"/><compartment id="other" size="3" constant="true"/></listOfCompartments><listOfSpecies><species id="A" compartment="cell" initialConcentration="1"/><species id="B" compartment="other" initialConcentration="2"/></listOfSpecies><listOfParameters><parameter id="k" value="3" constant="true"/></listOfParameters><listOfReactions><reaction id="r" reversible="false"><listOfReactants><speciesReference species="A" stoichiometry="1"/></listOfReactants><listOfProducts><speciesReference species="B" stoichiometry="1"/></listOfProducts><kineticLaw><math xmlns="http://www.w3.org/1998/Math/MathML"><apply><times/><ci>cell</ci><ci>k</ci><ci>A</ci></apply></math></kineticLaw></reaction></listOfReactions></model></sbml>'''


def mutate(change):
    root = ET.fromstring(toy_raw())
    change(root)
    return ET.tostring(root)


def nodes(root, name):
    return [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == name]


def determinant(matrix):
    """Leibniz enumeration, deliberately unrelated to checker elimination."""
    size = len(matrix)
    total = 0
    for order in permutations(range(size)):
        inversions = sum(order[i] > order[j] for i in range(size) for j in range(i + 1, size))
        term = (-1) ** inversions
        for row, column in enumerate(order):
            term *= matrix[row][column]
        total += term
    return total


def rank_by_minors(matrix):
    if not matrix or not matrix[0]:
        return 0
    for size in range(min(len(matrix), len(matrix[0])), 0, -1):
        for rows in combinations(range(len(matrix)), size):
            for columns in combinations(range(len(matrix[0])), size):
                if determinant([[matrix[r][c] for c in columns] for r in rows]):
                    return size
    return 0


def authored_matlab():
    return b'''function xdot=f(x,t)
compartment_cell=2;
compartment_other=3;
reaction_r_k=3;
reaction_r=compartment_cell*reaction_r_k*x(1);
xdot(1)=-reaction_r/compartment_cell;
xdot(2)=reaction_r/compartment_other;
end
'''


class ExactModelChecksTests(unittest.TestCase):
    def assert_rejected(self, raw):
        with self.assertRaises((ValueError, KeyError, ZeroDivisionError, OverflowError)):
            model = checks.SBMLModel(raw)
            model.rhs(Fraction(), model.dynamic_initial)

    def test_left_nullspace_against_independent_bruteforce_and_minors(self):
        matrices = [list(map(list, zip(values[:2], values[2:])))
                    for values in product((-1, 0, 1), repeat=4)]
        matrices += [[list(values[i:i + 2]) for i in range(0, 6, 2)]
                     for index, values in enumerate(product((-1, 0, 1), repeat=6))
                     if index % 31 == 0]
        matrices += [[[0, 0], [0, 0], [0, 0]]]
        for matrix in matrices:
            with self.subTest(matrix=matrix):
                basis = checks.left_nullspace([[Fraction(x) for x in row] for row in matrix])
                kernel = [list(vector) for vector in product(range(-2, 3), repeat=len(matrix))
                          if any(vector) and all(sum(vector[r] * matrix[r][c] for r in range(len(matrix))) == 0
                                                 for c in range(len(matrix[0])))]
                expected_dimension = len(matrix) - rank_by_minors(matrix)
                self.assertEqual(rank_by_minors(kernel), expected_dimension)
                self.assertEqual(len(basis), expected_dimension)
                self.assertEqual(rank_by_minors(basis + kernel), expected_dimension)
                self.assertTrue(all(all(sum(v[r] * matrix[r][c] for r in range(len(matrix))) == 0
                                       for c in range(len(matrix[0]))) for v in basis))

    def test_ragged_nullspace_matrix_is_rejected(self):
        with self.assertRaises(ValueError):
            checks.left_nullspace([[Fraction(1)], [Fraction(1), Fraction(2)]])
        with self.assertRaises(ValueError):
            checks.left_nullspace([[], []])

    def test_volume_weighted_conservation_and_altered_stoichiometry(self):
        model = checks.SBMLModel(toy_raw())
        certificate = checks.conservation(model)
        self.assertEqual(certificate["certificates"][0]["amount_weights"], [1, 1])
        self.assertEqual(certificate["certificates"][0]["concentration_weights"], ["2", "3"])
        self.assertEqual(certificate["certificates"][0]["initial_total"], "8")
        self.assertEqual(model.rhs(0, model.dynamic_initial), [Fraction(-3), Fraction(2)])
        changed = checks.SBMLModel(mutate(lambda root: nodes(root, "speciesReference")[1].set("stoichiometry", "2")))
        self.assertNotEqual(checks.conservation(changed)["certificates"][0]["amount_weights"], [1, 1])
        derivative = changed.rhs(0, changed.dynamic_initial)
        self.assertNotEqual(sum(volume * rate for volume, rate in zip((2, 3), derivative)), 0)
        self.assertIn("finite algebra", certificate["scope"].lower())

    def test_duplicate_and_colliding_ids_fail_closed(self):
        mutations = {
            "duplicate_compartment": lambda root: nodes(root, "listOfCompartments")[0].append(ET.fromstring('<compartment id="cell" size="4"/>')),
            "duplicate_parameter": lambda root: nodes(root, "listOfParameters")[0].append(ET.fromstring('<parameter id="k" value="9"/>')),
            "species_parameter_collision": lambda root: nodes(root, "parameter")[0].set("id", "A"),
            "duplicate_reaction": lambda root: nodes(root, "listOfReactions")[0].append(ET.fromstring(ET.tostring(nodes(root, "reaction")[0]))),
        }
        for label, change in mutations.items():
            with self.subTest(label=label):
                self.assert_rejected(mutate(change))

    def test_wrong_sbml_namespace_is_rejected(self):
        self.assert_rejected(mutate(lambda root: setattr(root, "tag", "{urn:fake:sbml}sbml")))

    def test_unknown_references_and_math_symbols_fail_closed(self):
        self.assert_rejected(mutate(lambda root: nodes(root, "speciesReference")[0].set("species", "missing")))
        self.assert_rejected(mutate(lambda root: setattr(nodes(root, "ci")[-1], "text", "missing")))

    def test_unmodeled_sbml_semantics_fail_closed(self):
        def add_feature(root, name):
            nodes(root, "model")[0].append(ET.Element(name))
        for name in ("event", "rateRule", "algebraicRule", "initialAssignment", "functionDefinition", "stoichiometryMath"):
            with self.subTest(feature=name):
                self.assert_rejected(mutate(lambda root, name=name: add_feature(root, name)))
        self.assert_rejected(mutate(lambda root: nodes(root, "reaction")[0].set("fast", "true")))
        self.assert_rejected(mutate(lambda root: nodes(root, "species")[0].set("conversionFactor", "k")))
        self.assert_rejected(mutate(lambda root: root.set("{urn:unknown:sbml-package}required", "true")))

    def test_compartment_amount_and_conflicting_initialization_restrictions(self):
        self.assert_rejected(mutate(lambda root: nodes(root, "compartment")[0].set("constant", "false")))
        self.assert_rejected(mutate(lambda root: nodes(root, "compartment")[0].set("size", "0")))
        self.assert_rejected(mutate(lambda root: nodes(root, "species")[0].set("hasOnlySubstanceUnits", "true")))
        self.assert_rejected(mutate(lambda root: nodes(root, "species")[0].set("initialAmount", "6")))
        def amount_only(root):
            species = nodes(root, "species")[0]
            species.attrib.pop("initialConcentration")
            species.set("initialAmount", "6")
        model = checks.SBMLModel(mutate(amount_only))
        self.assertEqual(model.dynamic_initial[0], Fraction(3))

    def test_duplicate_assignment_targets_and_unknown_rule_targets_fail_closed(self):
        for unknown in (False, True):
            def add_rules(root):
                rules = ET.SubElement(nodes(root, "model")[0], "listOfRules")
                for _ in range(1 if unknown else 2):
                    rule = ET.SubElement(rules, "assignmentRule", variable="missing" if unknown else "A")
                    math = ET.SubElement(rule, "math")
                    ET.SubElement(math, "cn").text = "1"
            with self.subTest(unknown=unknown):
                self.assert_rejected(mutate(add_rules))

    def test_assignment_to_fixed_compartment_or_constant_species_is_rejected(self):
        for target in ("cell", "A"):
            def add_assignment(root):
                if target == "A":
                    nodes(root, "species")[0].set("constant", "true")
                rules = ET.SubElement(nodes(root, "model")[0], "listOfRules")
                rule = ET.SubElement(rules, "assignmentRule", variable=target)
                math = ET.SubElement(rule, "math")
                ET.SubElement(math, "cn").text = "7"
            with self.subTest(target=target):
                self.assert_rejected(mutate(add_assignment))

    def test_matlab_finite_exact_correspondence_and_altered_expression(self):
        model = checks.SBMLModel(toy_raw())
        good = checks.matlab_correspondence(model, authored_matlab(), samples=5)
        bad = checks.matlab_correspondence(model, authored_matlab().replace(b"xdot(2)=reaction_r/", b"xdot(2)=2*reaction_r/"), samples=5)
        self.assertEqual(good["status"], "MATCHED_FINITE_RATIONAL_SAMPLES")
        self.assertEqual(bad["status"], "CONTRADICTED")
        self.assertFalse(good["code_executed"])
        self.assertIn("finite", good["scope"].lower())
        self.assertIn("not a proof", good["scope"].lower())

    def test_matlab_scalar_injection_never_executes(self):
        with tempfile.TemporaryDirectory(dir="/dev/shm") as temporary:
            sentinel = Path(temporary) / "executed"
            expression = "__import__('pathlib').Path(" + repr(str(sentinel)) + ").touch()"
            with self.assertRaises(ValueError):
                checks.scalar_ast(expression, {})
            raw = authored_matlab().replace(b"reaction_r_k=3;", ("reaction_r_k=" + expression + ";").encode())
            with self.assertRaises(ValueError):
                checks.matlab_correspondence(checks.SBMLModel(toy_raw()), raw, samples=1)
            self.assertFalse(sentinel.exists())

    def test_unknown_matlab_executable_lines_are_rejected_or_explicitly_reported(self):
        for line in (b"unexpected_executable_statement();", b"t=unexpected_executable_statement();",
                     b"plot(unexpected_executable_statement());", b"x0unexpected_executable_statement();",
                     b"xdot=zeros(2,1);unexpected_executable_statement();"):
            with self.subTest(statement=line):
                raw = authored_matlab().replace(b"end\n", line + b"\nend\n")
                try:
                    result = checks.matlab_correspondence(checks.SBMLModel(toy_raw()), raw, samples=1)
                except ValueError:
                    continue
                self.assertFalse(result.get("full_program_semantics_checked", False))
                unparsed = result.get("unparsed_lines", result.get("unsupported_lines", []))
                self.assertTrue(unparsed, "unknown executable lines were silently dropped")
                self.assertIn("unexpected_executable_statement", json.dumps(unparsed))

    def test_zero_negative_and_extreme_sample_counts_fail_before_loop(self):
        model = checks.SBMLModel(toy_raw())
        for count in (0, -1, 1000000000):
            with self.subTest(samples=count):
                # A missing preflight bound must not make this test loop forever.
                if count > 100:
                    script = ("from research.scientific_understanding_v2 import model_checks as m\n"
                              "from research.scientific_understanding_v2.test_model_checks import toy_raw, authored_matlab\n"
                              "try: m.matlab_correspondence(m.SBMLModel(toy_raw()), authored_matlab(), samples=1000000000)\n"
                              "except ValueError: raise SystemExit(0)\n"
                              "raise SystemExit(1)\n")
                    try:
                        result = subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=1)
                    except subprocess.TimeoutExpired:
                        self.fail("extreme sample count has no preflight resource bound")
                    self.assertEqual(result.returncode, 0, result.stderr.decode())
                else:
                    with self.assertRaises(ValueError):
                        checks.matlab_correspondence(model, authored_matlab(), samples=count)

    def test_resource_rejections_are_bounded(self):
        for value in ("1e101", "1e-101", "9" * 101):
            with self.assertRaises(ValueError):
                checks.fraction(value)
        with self.assertRaises(ValueError):
            checks.scalar_ast("1" * 10001, {})
        with self.assertRaises(ValueError):
            checks.scalar_ast("2**9", {})
        with self.assertRaises(ValueError):
            checks.safe_xml(b" " * (5 * 1024 * 1024 + 1))
        with self.assertRaises(ValueError):
            checks.safe_xml(b'<!DOCTYPE foo [<!ENTITY x "boom">]><sbml/>')

    def test_nested_power_resource_failure_is_explicit_and_bounded(self):
        # OS limits apply only in this authored-synthetic child. No large value
        # is constructed in the shared test process, even on a broken checker.
        script = r"""import resource
resource.setrlimit(resource.RLIMIT_AS, (96 * 1024 * 1024, 96 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
from research.scientific_understanding_v2 import model_checks as m
expr = "2"
for _ in range(12): expr = "(" + expr + ")**8"
import xml.etree.ElementTree as ET
node = ET.Element("cn")
node.text = "2"
for _ in range(12):
    parent = ET.Element("apply")
    ET.SubElement(parent, "power")
    parent.append(node)
    ET.SubElement(parent, "cn").text = "8"
    node = parent
for compute in (lambda: m.scalar_ast(expr, {}), lambda: m.mathml(node, {})):
    try:
        compute()
    except ValueError:
        continue
    except (MemoryError, OverflowError):
        raise SystemExit(2)
    raise SystemExit(1)
raise SystemExit(0)
"""
        try:
            result = subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=3)
        except subprocess.TimeoutExpired:
            self.fail("nested powers exceeded the checker resource deadline")
        self.assertEqual(result.returncode, 0, "nested powers need an explicit arithmetic resource bound")

    def test_real_development_sbml_to_published_export_finite_correspondence(self):
        model = checks.SBMLModel((DEV / "tyson1991.sbml").read_bytes())
        result = checks.matlab_correspondence(model, (DEV / "tyson1991.m").read_bytes(), samples=5)
        self.assertEqual(result["status"], "MATCHED_FINITE_RATIONAL_SAMPLES")
        self.assertEqual(result["discrepancies"], [])
        self.assertFalse(result["code_executed"])
        self.assertIn("not a proof", result["scope"].lower())

    @unittest.skipUnless(find_spec("scipy") is not None and find_spec("numpy") is not None,
                         "optional pinned numerical dependencies are not on PYTHONPATH")
    def test_optional_dev_stiff_solve_has_finite_limited_evidence(self):
        script = '''from pathlib import Path
from research.scientific_understanding_v2 import model_checks as m
model=m.SBMLModel(Path("research/scientific_understanding_v2/fixtures/upstream/tyson1991.sbml").read_bytes())
r=m.integrate_model(model,t_end=0.01)
assert r["status"] == "REPRODUCED_NUMERICALLY"
assert {x["method"] for x in r["runs"]} == {"Radau", "BDF"}
assert r["max_solver_difference"] < 1e-5
assert all(max(x["conserved_total_max_abs_drift"], default=0) < 1e-7 for x in r["runs"])
assert "Not a rigorous global" in r["scope"]
'''
        result = subprocess.run([sys.executable, "-c", script], capture_output=True, timeout=8)
        self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == "__main__":
    unittest.main()
