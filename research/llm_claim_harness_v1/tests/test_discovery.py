"""Deterministic extraction must save API calls without overclaiming context."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from research.llm_claim_harness_v1.core import Source
from research.llm_claim_harness_v1.discovery import discover_standalone

HERE = Path(__file__).resolve().parents[1]


class DiscoveryTests(unittest.TestCase):
    def test_arithmetic_fixture_discovers_only_3_valid_lines(self):
        s = Source.from_bytes((HERE / 'fixtures/arithmetic_source.txt').read_bytes())
        found = discover_standalone(s, 'arithmetic')
        self.assertEqual(len(found['claims']), 3)
        self.assertEqual([x['source_quote'] for x in found['claims']], [
            '(1/2 + 1/3) = 5/6', '0.1 + 0.2 = 0.3', '2 * (3 - 5) >= -3'])

    def test_literal_fixture(self):
        text = 'Intro\n3/4 >= 2/3\n7 < 2\ninvalid\n'
        s = Source.from_bytes(text.encode())
        found = discover_standalone(s, 'literal')['claims']
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]['relation']['lhs'], '3/4')

    def test_unicode_and_crlf_offsets(self):
        text = 'π; not an equation\r\n  1/3 + 2/3 = 1  \r\n'
        s = Source.from_bytes(text.encode())
        found = discover_standalone(s, 'arithmetic')['claims']
        self.assertEqual(len(found), 1)
        quote = found[0]['source_quote']
        self.assertEqual(quote, '1/3 + 2/3 = 1')
        self.assertEqual(text[found[0]['source_span']['start']:found[0]['source_span']['end']], quote)

    def test_no_inference_from_prose(self):
        text = 'approximately 1/3 + 2/3 = 1 according to model\n'
        self.assertEqual(discover_standalone(Source.from_bytes(text.encode()), 'arithmetic')['claims'], [])

    def test_literal_does_not_promote_complex_equation(self):
        s = Source.from_bytes(b'1+2=3\n')
        self.assertEqual(discover_standalone(s, 'literal')['claims'], [])
        self.assertEqual(len(discover_standalone(s, 'arithmetic')['claims']), 1)

    def test_invalid_scientific_notation_and_units(self):
        s = Source.from_bytes(b'2^3 = 8\n3 kg < 4 kg\n1e6 > 2\n')
        self.assertEqual(discover_standalone(s, 'arithmetic')['claims'], [])

    def test_reject_more_than_32(self):
        s = Source.from_bytes(("1 < 2\n" * 33).encode())
        with self.assertRaisesRegex(ValueError, 'budget'):
            discover_standalone(s, 'arithmetic')

    def test_cli_no_keys_no_network(self):
        s = HERE / 'fixtures/arithmetic_source.txt'
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'receipt.json'
            args = [sys.executable, '-m', 'research.llm_claim_harness_v1', '--mode', 'arithmetic',
                    '--primary', 'deterministic', '--source', str(s), '--out', str(out), '--lean', '__none__']
            completed = subprocess.run(args, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stderr)
            receipt = json.loads(out.read_text())
            self.assertEqual(receipt['counts']['accepted_grounding'], 3)
            self.assertEqual(receipt['primary']['network_calls'], 0)
            self.assertEqual(receipt['counts']['kernel_checked'], 0)

    def test_no_sneaky_model_name(self):
        s = HERE / 'fixtures/arithmetic_source.txt'
        with tempfile.TemporaryDirectory() as tmp:
            cmd = [sys.executable, '-m', 'research.llm_claim_harness_v1', '--primary', 'deterministic',
                   '--primary-model', 'bad', '--source', str(s), '--out', str(Path(tmp)/'receipt.json')]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('does not use a model', result.stderr)


if __name__ == '__main__':
    unittest.main()
