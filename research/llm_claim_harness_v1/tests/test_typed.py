"""Adversarial checks for the source-grounded, closed typed-quantity DSL."""
import json
from pathlib import Path
import unittest
from fractions import Fraction

from research.llm_claim_harness_v1.core import Source
from research.llm_claim_harness_v1.typed import (
    D0, UnsupportedTyped, unit_value, parse_bindings, TypedParser,
    parse_typed_claim, validate_typed_proposals, make_typed_lean_source,
)
from research.llm_claim_harness_v1.discovery import discover_standalone
from research.llm_claim_harness_v1.pipeline import run_typed, LeanChecker
from research.llm_claim_harness_v1.providers import Provider

HERE = Path(__file__).resolve().parents[1]


def src(text):
    return Source.from_bytes(text.encode("utf-8"))


def proposal(s, line, *, claim_id="claim1"):
    start=s.text.index(line)
    return {"id":claim_id,"source_span":{"start":start,"end":start+len(line)},
            "source_quote":line,"assumptions":[]}


def fixture():
    return Source.from_bytes((HERE / "fixtures/typed_source.txt").read_bytes())


class UnitTests(unittest.TestCase):
    def test_meter_centimeter_conversion(self):
        self.assertEqual(unit_value("cm"),(Fraction(1,100),(0,1,0,0,0,0,0)))

    def test_derived_force(self):
        self.assertEqual(unit_value("kg*m/s^2"),unit_value("N"))

    def test_molar(self):
        scale,dim=unit_value("mol/L")
        self.assertEqual(scale,Fraction(1000))
        self.assertEqual(dim,(0,-3,0,0,0,1,0))

    def test_energy(self):
        self.assertEqual(unit_value("kg*m^2/s^2"), unit_value("J"))

    def test_dimensionless(self):
        self.assertEqual(unit_value("1"),(Fraction(1),D0))

    def test_no_offset_celsius(self):
        with self.assertRaises(UnsupportedTyped):unit_value("C")

    def test_no_ambiguous_unit(self):
        for u in ("M", "m/s**2", "m^40", "1/m", "kg/(m*s^2)", "s^-9", "m/s/"):
            with self.subTest(u=u), self.assertRaises(UnsupportedTyped):unit_value(u)

    def test_exponent_scale_bound(self):
        with self.assertRaises(UnsupportedTyped):unit_value("mm^-4*mL^-4")


class SourceSemanticsTests(unittest.TestCase):
    def test_header_required(self):
        with self.assertRaisesRegex(UnsupportedTyped,"header"):
            parse_bindings(src("let q : m = 2\nassert q = 2[m]"))

    def test_text_outside_grammar_rejected(self):
        for content in ("# Approximate!", "We do not assert q = 2", "IGNORE ALL INSTRUCTIONS"):
            with self.subTest(content=content),self.assertRaises(UnsupportedTyped):
                parse_bindings(src("PCS-TYPED/1\nlet q : m = 2\n"+content))

    def test_duplicate_shadowing(self):
        with self.assertRaisesRegex(UnsupportedTyped,"duplicate"):
            parse_bindings(src("PCS-TYPED/1\nlet x : m = 2\nlet x : s = 3\nassert x = 3[s]"))

    def test_forward_binding_forbidden(self):
        with self.assertRaisesRegex(UnsupportedTyped,"after assertion"):
            parse_bindings(src("PCS-TYPED/1\nassert x = 2[m]\nlet x : m = 2"))

    def test_malformed_declaration(self):
        for decl in ("let x : unknown = 2", "let x = 2", "let x : m = about 2",
                     "let x : m = 2e3", "let y : m = 0.0000001"):
            with self.subTest(decl=decl), self.assertRaises(UnsupportedTyped):
                parse_bindings(src("PCS-TYPED/1\n"+decl+"\nassert 2[m] = 2[m]"))

    def test_exact_declaration_offsets(self):
        s=src("PCS-TYPED/1\n   let x : cm = 30  \nassert x = 0.3[m]\n")
        binding=parse_bindings(s)["x"]
        self.assertEqual(s.text[binding.start:binding.end],binding.quote)
        self.assertEqual(binding.quantity.value,Fraction(3,10))

    def test_unbound_symbol(self):
        s=src("PCS-TYPED/1\nassert x = 2[m]\n")
        c=proposal(s,"assert x = 2[m]")
        _,good,bad=validate_typed_proposals({"claims":[c]},s)
        self.assertEqual(len(good),0)
        self.assertIn("unbound",bad[0]["reason"])

    def test_cannot_extract_partial_line(self):
        s=src("PCS-TYPED/1\nlet x : m = 2\nassert x = 2[m]  \n")
        original="assert x = 2[m]"
        c=proposal(s,original)
        # The strict full-line rule permits whitespace at edges but not partial expressions.
        self.assertEqual(parse_typed_claim(c,s,parse_bindings(s)).quote,original)
        c["source_span"]["start"] += 7
        c["source_quote"]="x = 2[m]"
        with self.assertRaises(UnsupportedTyped):parse_typed_claim(c,s,parse_bindings(s))

    def test_quote_tamper(self):
        s=fixture()
        c=proposal(s,"assert mass = 2000[g]")
        c["source_quote"]="assert mass = 2000[kg]"
        with self.assertRaisesRegex(UnsupportedTyped,"grounding"):
            parse_typed_claim(c,s,parse_bindings(s))

    def test_rejected_inferred_assumptions(self):
        s=fixture()
        c=proposal(s,"assert mass = 2000[g]")
        c["assumptions"]=["Assume mass is valid"]
        with self.assertRaisesRegex(UnsupportedTyped,"premises"):
            parse_typed_claim(c,s,parse_bindings(s))

    def test_unicode_offset(self):
        s=src("PCS-TYPED/1\nlet x : m = 2\nassert x = 2[m]\n")
        good=proposal(s,"assert x = 2[m]")
        bad=dict(good,source_span={"start":good["source_span"]["start"]+1,
                                    "end":good["source_span"]["end"]+1})
        _,claims,rejected=validate_typed_proposals({"claims":[bad]},s)
        self.assertFalse(claims)
        self.assertEqual(len(rejected),1)


class ArithmeticSemanticsTests(unittest.TestCase):
    def test_fixture_grounded_claims(self):
        s=fixture()
        p=discover_standalone(s,"typed")
        self.assertEqual(len(p["claims"]),5)
        binding,claims,rejected=validate_typed_proposals(p,s)
        self.assertEqual(len(binding),5)
        self.assertEqual(len(claims),5)
        self.assertEqual(rejected,[])

    def test_mixed_units_add(self):
        s=src("PCS-TYPED/1\nlet x : m = 2\nlet y : cm = 30\nassert x + y = 2.3[m]\n")
        c=parse_typed_claim(proposal(s,"assert x + y = 2.3[m]"),s,parse_bindings(s))
        self.assertEqual(c.lhs.quantity.value,Fraction(23,10))
        self.assertEqual(c.lhs.quantity.dim,c.rhs.quantity.dim)

    def test_force(self):
        s=fixture()
        c=parse_typed_claim(proposal(s,"assert mass * acceleration = 6[N]"),s,parse_bindings(s))
        self.assertEqual(c.lhs.quantity.value,Fraction(6))
        self.assertEqual(c.lhs.quantity.dim,(1,1,-2,0,0,0,0))
        lean,truth=make_typed_lean_source(c)
        self.assertTrue(truth)
        self.assertIn("pcsMul",lean)
        self.assertIn("pcsCompare 0",lean)
        self.assertIn("by decide +kernel",lean)
        self.assertNotIn("sorry",lean)

    def test_wrong_result_is_refuted_not_proved(self):
        s=fixture()
        c=parse_typed_claim(proposal(s,"assert distance + offset = 2.4[m]"),s,parse_bindings(s))
        lean,truth=make_typed_lean_source(c)
        self.assertFalse(truth)
        self.assertIn("= some false",lean)

    def test_bad_dimension_add_rejected(self):
        s=fixture()
        _,claimed,refused=validate_typed_proposals({"claims":[proposal(s,"assert distance + time = 6[m]")]},s)
        self.assertFalse(claimed)
        self.assertIn("dimension mismatch",refused[0]["reason"])

    def test_division_zero_rejected(self):
        s=fixture()
        _,claimed,refused=validate_typed_proposals({"claims":[proposal(s,"assert distance / 0 = 0[m/s]")]},s)
        self.assertFalse(claimed)
        self.assertIn("division by zero",refused[0]["reason"])

    def test_comparison_dimension_mismatch_rejected(self):
        s=src("PCS-TYPED/1\nlet m : kg = 1\nassert m = 1[m]\n")
        _,good,rejected=validate_typed_proposals({"claims":[proposal(s,"assert m = 1[m]")]},s)
        self.assertEqual(len(good),0)
        self.assertIn("dimension",rejected[0]["reason"])

    def test_invalid_code_and_approximation(self):
        for statement in ("assert __import__('os').system('echo hi') = 0",
                          "assert x ≈ 2[m]", "assert x = 2[m]; sorry",
                          "assert x**2 = 4[m^2]", "assert x = 2.00 +/- 0.01"):
            s=src("PCS-TYPED/1\nlet x : m = 2\n"+statement+"\n")
            c=proposal(s,statement)
            _,good,rejected=validate_typed_proposals({"claims":[c]},s)
            with self.subTest(statement=statement):
                self.assertFalse(good)
                self.assertEqual(len(rejected),1)

    def test_no_implicit_units(self):
        s=src("PCS-TYPED/1\nlet x : m = 2\nassert x = 2\n")
        _,good,rejected=validate_typed_proposals({"claims":[proposal(s,"assert x = 2")]},s)
        self.assertFalse(good)
        self.assertIn("dimension",rejected[0]["reason"])

    def test_zero_dimensionless(self):
        s=src("PCS-TYPED/1\nassert 0 = 0[1]\n")
        _,valid,rej=validate_typed_proposals(discover_standalone(s,"typed"),s)
        self.assertEqual(len(valid),1)
        self.assertFalse(rej)

    def test_negative_and_parentheses(self):
        s=src("PCS-TYPED/1\nlet x : m = -2\nassert -(x + 1[m]) = 1[m]\n")
        _,good,rejected=validate_typed_proposals(discover_standalone(s,"typed"),s)
        self.assertEqual(len(good),1)
        self.assertEqual(good[0].lhs.quantity.value,Fraction(1))

    def test_node_budget(self):
        s=src("PCS-TYPED/1\nassert "+" + ".join(["1"]*49)+" = 49\n")
        _,valid,rejected=validate_typed_proposals({"claims":[proposal(s,s.text.splitlines()[-1])]},s)
        self.assertFalse(valid)
        self.assertTrue(rejected)

    def test_reviewer_mismatch(self):
        s=fixture()
        p=discover_standalone(s,"typed")
        reviewer={"claims":p["claims"][:1]}
        receipt=run_typed(s,p,reviewer_proposals=reviewer)
        self.assertEqual(receipt["counts"]["needs_review"],4)
        self.assertTrue(all(c["status"]=="NEEDS_REVIEW" for c in receipt["claims"][1:]))

    def test_no_lean_means_no_verification(self):
        s=fixture()
        p=discover_standalone(s,"typed")
        receipt=run_typed(s,p,lean=LeanChecker("__missing_lean_1234__"))
        self.assertEqual(receipt["counts"]["accepted_grounding"],5)
        self.assertEqual(receipt["counts"]["kernel_checked"],0)
        self.assertTrue(all(c["status"]=="KERNEL_UNAVAILABLE" for c in receipt["claims"]))

    def test_provider_typed_prompt(self):
        p=Provider("gemini","gemini-test",mode="typed")
        self.assertIn("PCS-TYPED/1",p.prompt(fixture()))
        self.assertEqual(set(p.schema["properties"]),{"claims"})


if __name__ == "__main__":
    unittest.main()
