"""Independent checks of the newly frozen study and analytic selection predictions."""

from collections import Counter, defaultdict
from dataclasses import fields, replace
from fractions import Fraction
from itertools import product
import tempfile
import unittest
from pathlib import Path

from adjudicator import denied
import freeze
from ledger_study import ceiling, study
from monitors import completions, decode, monitor, observations, View
from packets import flat_record, packets
from selection import choose, strict_screen, theory


class LedgerChecks(unittest.TestCase):

    def test_simple_operational_examples(self):
        rows = {
            ("exhibit", 0, 1, 0, "synopsis"): False,
            ("exhibit", 1, 1, 0, "facsimile"): True,
            ("exhibit", 1, 1, 1, "facsimile"): False,
            ("allocation", 1, 1, 0, "two"): True,
            ("allocation", 1, 1, 1, "two"): False,
            ("recital", 1, 1, 0, "right"): False,
            ("recital", 1, 1, 1, "right"): True,
            ("recital", 1, 1, 1, "left"): False,
        }
        checked = Counter()
        for row in packets():
            v = decode(row)
            key = v.ledger, v.a, v.b, v.e, v.proposal
            if key in rows:
                self.assertEqual(denied(row), rows[key])
                checked[key] += 1
        self.assertEqual(checked, dict.fromkeys(rows, 8))

    def test_ledger_boundaries_and_adapters(self):
        cases = list(packets())
        self.assertEqual(816, len({r["id"] for r in cases}))
        n_by_event = Counter()
        for row in cases:
            v = decode(row)
            gold = flat_record(v.ledger, v.a, v.b, v.e, v.proposal, v.note)
            self.assertEqual(decode(gold, flat=True), v)
            n_by_event[v.ledger, v.a, v.b, v.e, v.proposal] += 1
        self.assertEqual(Counter(n_by_event.values()), {8: 102})
        self.assertEqual({f.name for f in fields(View)}, {
            "ledger", "executed", "note", "proposal", "a", "b", "e"})

    def test_every_support_witness_independently_replays(self):
        expected = defaultdict(set)
        worlds = {}
        for row in packets():
            v = decode(row)
            label = denied(row)
            worlds[v.ledger, v.executed, v.proposal, v.a, v.b, v.e] = label
            for obs in observations(row).values():
                expected[obs].add(label)
        for obs, labels in expected.items():
            support = dict(completions(obs))
            self.assertEqual(set(support), labels)
            for value, witness in support.items():
                action, a, b, e = witness
                self.assertEqual(worlds[obs.ledger, obs.executed, action, a, b, e], value)
                for known, reconstructed in zip(
                    (obs.proposal, obs.a, obs.b, obs.e), witness, strict=True
                ):
                    if known is not None:
                        self.assertEqual(known, reconstructed)
        alien = replace(next(iter(expected)), executed="unknown")
        self.assertEqual(completions(alien), ())
        self.assertIsNone(monitor(alien))

    def test_refinement_preserves_each_decision(self):
        for packet in packets():
            views = observations(packet)
            for coarse, refined in (("executed", "proposal"), ("proposal", "early"),
                                    ("early", "settled"), ("lossy", "settled")):
                old = monitor(views[coarse])
                if old is not None:
                    self.assertEqual(old, monitor(views[refined]))

    def test_full_coverage_floor_by_enumeration(self):
        pairs = [("a", True), ("a", False), ("a", False), ("b", True)]
        possibilities = []
        for a, b in product((True, False, None), repeat=2):
            rule = {"a": a, "b": b}
            guesses = [(rule[o], y) for o, y in pairs if rule[o] is not None]
            possibilities.append((len(guesses), sum(p != y for p, y in guesses)))
        calc = ceiling(pairs)
        self.assertEqual(max(c for c, e in possibilities if e == 0),
                         calc["max_coverage_without_error"])
        self.assertEqual(min(e for c, e in possibilities if c == len(pairs)),
                         calc["min_errors_without_abstention"])

    def test_freeze_detects_changed_input_and_key(self):
        files = freeze.frozen_files()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for name, content in files.items():
                (folder / name).write_bytes(content)
            freeze.verify(folder)
            for name, content in files.items():
                target = folder / name
                target.write_bytes(content + b" ")
                with self.assertRaises(ValueError):
                    freeze.verify(folder)
                target.write_bytes(content)

    def test_invalid_typed_packet_fields(self):
        packet = next(packets())
        valid = packet["submission"]
        for submission in (dict(valid, registers=[True, 0]), dict(valid, registers=[2, 0]),
                           dict(valid, choice="unknown"), dict(valid, dispatch="unknown")):
            with self.assertRaises(ValueError):
                observations(dict(packet, submission=submission))
        for erase in ("ledger", "note", "executed", ""):
            with self.assertRaises(ValueError):
                observations(dict(packet, erase=erase))

    def test_scored_complete_view_and_losses(self):
        report = study()
        all_rows = report["by_family"]["all"]
        self.assertEqual(all_rows["settled"]["counts"]["completion"],
                         all_rows["settled"]["counts"]["full_registers"])
        self.assertGreater(all_rows["proposal"]["counts"]["disagreement"]["fp"], 0)
        for channel in ("executed", "proposal", "early", "lossy"):
            self.assertGreater(all_rows[channel]["theoretical_census"]
                               ["min_errors_without_abstention"], 0)


class SelectionChecks(unittest.TestCase):

    def test_exact_screen_by_weighted_draw_enumeration(self):
        p0, p1 = Fraction(3, 4), Fraction(2, 3)
        n, k = 2, 2
        probability = gain = Fraction()
        for bits in product((0, 1), repeat=n * (k + 1)):
            mass = Fraction(1)
            for i, bit in enumerate(bits):
                p = p0 if i < n else p1
                mass *= p if bit else 1 - p
            improvement = max(0, max(sum(bits[2:4]), sum(bits[4:])) - sum(bits[:2]))
            gain += mass * improvement
            if improvement:
                probability += mass
        self.assertEqual(strict_screen(n, k, p0, p1), (probability, gain))

    def test_split_theory_by_enumerating_qualification_readings(self):
        p0, p1 = Fraction(3, 4), Fraction(11, 16)
        mass_promoted = gain = Fraction()
        for bits in product((0, 1), repeat=6):
            pairs = [bits[i:i + 2] for i in (0, 2, 4)]
            weight = Fraction(1)
            for i, pair in enumerate(pairs):
                p = p1 if i else p0
                weight *= p ** sum(pair) * (1 - p) ** (2 - sum(pair))
            winner = choose(pairs, 2, "split")
            if winner:
                mass_promoted += weight
            gain += weight * (sum(pairs[winner]) - sum(pairs[0])) / 2
        expected = theory("split", 2, p1, panel_size=2)
        self.assertAlmostEqual(float(mass_promoted), expected["promotion_probability"])
        self.assertAlmostEqual(float(gain), expected["panel_accuracy_gain"])
        self.assertAlmostEqual(float(mass_promoted * (p1 - p0)),
                               expected["population_accuracy_gain"])

    def test_protected_screen_and_ties(self):
        self.assertEqual(choose([(2, 2), (2, 8), (1, 9)], 2, "split"), 0)
        self.assertEqual(choose([(2, 2), (3, 1), (3, 9)], 2, "split"), 0)
        self.assertEqual(choose([(2, 2), (3, 3), (3, 9)], 2, "split"), 1)
        self.assertEqual(choose([(2, 2), (1, 4), (1, 4)], 2, "reuse"), 1)
        self.assertEqual(choose([(2, 2), (1, 3), (0, 4)], 2, "reuse"), 0)

    def test_equal_quality_control_and_weaker_monotonicity(self):
        for method in ("reuse", "split"):
            for k in (1, 4, 16, 64):
                self.assertEqual(theory(method, k, Fraction(3, 4))["population_accuracy_gain"], 0)
            losses = [theory(method, k, Fraction(11, 16))["population_accuracy_gain"]
                      for k in (1, 4, 16, 64)]
            self.assertTrue(all(a > b for a, b in zip(losses, losses[1:])))


if __name__ == "__main__":
    unittest.main()
