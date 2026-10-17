import hashlib
import random
import unittest
from pathlib import Path

from pgsi2_wide_runtime import (
    Arch, Unit, Wide, WireReject, decode, encode, freeze_reference, valid
)

FIXTURES = Path(__file__).resolve().parents[3] / "formal" / "fixtures" / "proof_gated"
ARCH = Arch(8, 32)


class PGSI2WideRuntimeTests(unittest.TestCase):
    def test_roundtrip_lean_golden_vectors(self):
        raw_lines = (FIXTURES / "pgsi2_wide_canonical.txt").read_bytes().splitlines()
        self.assertEqual(len(raw_lines), 8)
        for raw in raw_lines:
            self.assertEqual(encode(decode(raw, ARCH)), raw)

    def test_malformed_lean_vectors(self):
        bad = sorted((FIXTURES / "pgsi2_wide_negative").glob("neg_*.txt"))
        self.assertEqual(len(bad), 10)
        for p in bad:
            with self.subTest(path=p.name), self.assertRaises(WireReject):
                decode(p.read_bytes(), ARCH)

    def test_generated_random_models(self):
        rng = random.Random(764)
        for _ in range(300):
            arch = Arch(rng.randrange(0, 7), 32)
            model = Wide(tuple(
                Unit(*(rng.randrange(-32, 33) for _ in range(3)))
                for _ in range(rng.randrange(0, arch.max_width + 1))
            ), rng.randrange(-32, 33))
            self.assertTrue(valid(model, arch))
            self.assertEqual(decode(encode(model), arch), model)
            for x in (-10**12, -19, -1, 0, 1, 19, 10**12):
                self.assertEqual(
                    model.predict(x),
                    model.output_bias + sum(
                        u.output * max(0, u.weight*x + u.bias) for u in model.units
                    )
                )

    def test_canonical_and_adversarial_byte_boundaries(self):
        valid_raw = b"PGSI2-WIDE|0|1|-2|3"
        self.assertEqual(decode(valid_raw, ARCH).units[0], Unit(1, -2, 3))
        mutations = [
            b"", b"PGSI2-WIDE", b"PGSI1-WIDE|0", b"pgsi2-wide|0",
            b"PGSI2-WIDE|", b"PGSI2-WIDE|-0", b"PGSI2-WIDE|00",
            b"PGSI2-WIDE|+0", b"PGSI2-WIDE|01", b"PGSI2-WIDE|0\n",
            b"PGSI2-WIDE|0\r\n", b"PGSI2-WIDE|0 ", b"PGSI2-WIDE| 0",
            b"PGSI2-WIDE|0|1|2", b"PGSI2-WIDE|0|1|2|3|",
            b"PGSI2-WIDE|0||1|1", b"PGSI2-WIDE|0|33|0|0",
            b"PGSI2-WIDE|0|-33|0|0", b"PGSI2-WIDE|0|\xc2\xb10|0|1",
            b"PGSI2-WIDE|0\0", b"\xef\xbb\xbfPGSI2-WIDE|0",
            b"PGSI2-WIDE|0|1|0|3\n",
        ]
        for raw in mutations:
            with self.subTest(raw=raw), self.assertRaises(WireReject):
                decode(raw, ARCH)
        with self.assertRaises(WireReject):
            decode(b"PGSI2-WIDE|0|1|0|1", Arch(0, 32))
        with self.assertRaises(WireReject):
            decode(b"PGSI2-WIDE|0|1|0|1", Arch(1, 0))
        with self.assertRaises(WireReject):
            decode(b"PGSI2-WIDE|0", ARCH, max_bytes=5)
        with self.assertRaises(ValueError):
            decode(b"PGSI2-WIDE|0", ARCH, max_bytes=-1)

    def test_frozen_snapshot_requires_matching_declared_digest(self):
        raw = b"PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2"
        h = hashlib.sha256(raw).hexdigest()
        snap = freeze_reference(raw, ARCH, expected_sha256=h)
        self.assertEqual(snap.artifact, raw)
        self.assertEqual(snap.digest, h)
        for x in range(-200, 201):
            self.assertEqual(snap.predict(x), snap.model.predict(x))
        with self.assertRaises(WireReject):
            freeze_reference(raw, ARCH, expected_sha256="0"*64)
        # The frozen snapshot is independent of later changes to the source variable.
        raw = b"PGSI2-WIDE|0"
        self.assertEqual(snap.artifact, b"PGSI2-WIDE|0|2|1|1|-1|1|1|1|-2|-2")

    def test_host_limits_are_explicit_not_mislabeled_lean_results(self):
        with self.assertRaises(TypeError):
            Wide((Unit(True, 0, 0),), 0)
        with self.assertRaises(ValueError):
            Arch(True, 32)
        with self.assertRaises(TypeError):
            decode("PGSI2-WIDE|0", ARCH)
        with self.assertRaises(TypeError):
            Wide((), True)
        with self.assertRaises(TypeError):
            Wide((), 0).predict(False)
        self.assertEqual(decode(b"PGSI2-WIDE|0", Arch(0, 0)), Wide((), 0))


if __name__ == "__main__":
    unittest.main()
