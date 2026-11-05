"""Independent reference replay of real Aristotle V6 PGSC6 fixed bytes.

The three vectors are copied byte-for-byte from the V6 SHA-256-matched
fixtures supplied by Aristotle. They are synthetic mathematical examples,
not signed or authenticated certificates. Tests do not pretend to invoke Lean.
"""
import unittest

from pgsc6_reference import (
    CertificateReject, Policy, decode_certificate,
    reference_certificate_passes,
)
from pgsi2_wide_runtime import Arch

VALID = tuple(x.encode("ascii") for x in (
    "PGSC6|6|1|8|32|0|-1000000000|1000000000|-1|34|26|-1000000000|1000000001|9|-4|-3|-2|-1|0|1|2|3|4|10|0|2|1|1|-1|1|1|1|-2|-2|12|80|71|83|73|50|45|87|73|68|69|124|48|19|80|71|83|73|50|45|87|73|68|69|124|48|124|45|50|124|48|124|49",
    "PGSC6|6|1|8|32|1|-1000000000|1000000000|-4|26|19|-1000000000|999999999|9|-4|-3|-2|-1|0|1|2|3|4|10|0|2|1|1|-1|1|1|1|-2|-2|19|80|71|83|73|50|45|87|73|68|69|124|48|124|45|50|124|48|124|49|19|80|71|83|73|50|45|87|73|68|69|124|48|124|45|49|124|49|124|49",
    "PGSC6|6|1|8|32|2|-1000000000|1000000000|0|19|0|1000000000|5|9|-4|-3|-2|-1|0|1|2|3|4|10|0|2|1|1|-1|1|1|1|-2|-2|19|80|71|83|73|50|45|87|73|68|69|124|48|124|45|49|124|49|124|49|33|80|71|83|73|50|45|87|73|68|69|124|48|124|50|124|49|124|49|124|45|49|124|49|124|49|124|49|124|45|50|124|45|50",
))


def trusted_policy() -> Policy:
    c = decode_certificate(VALID[0])
    return Policy(Arch(c.max_width, c.bound), c.target, c.corpus, c.low, c.high)


class PGSC6IndependentReplayTests(unittest.TestCase):
    def test_three_authentic_source_bytes_pass_reference(self):
        policy = trusted_policy()
        for index, raw in enumerate(VALID):
            c = decode_certificate(raw)
            self.assertEqual(c.generation, index)
            self.assertTrue(reference_certificate_passes(raw, policy, index, c.incumbent))

    def test_replay_and_substituted_incumbents_reject(self):
        policy = trusted_policy()
        for index, raw in enumerate(VALID):
            c = decode_certificate(raw)
            self.assertFalse(reference_certificate_passes(
                raw, policy, index + 1, c.incumbent))
            self.assertFalse(reference_certificate_passes(
                raw, policy, index, c.candidate))

    def test_proposer_cannot_rebind_trusted_interval_target_or_corpus(self):
        policy = trusted_policy()
        c = decode_certificate(VALID[0])
        for p in (
            Policy(policy.arch, policy.target, policy.corpus, policy.low, policy.high-1),
            Policy(policy.arch, policy.target, policy.corpus, policy.low, policy.high+1),
            Policy(policy.arch, policy.target, policy.corpus[::-1], policy.low, policy.high),
            Policy(Arch(7, 32), policy.target, policy.corpus, policy.low, policy.high),
            Policy(Arch(8, 31), policy.target, policy.corpus, policy.low, policy.high),
        ):
            with self.subTest(policy=p):
                self.assertFalse(reference_certificate_passes(VALID[0], p, 0,
                                                              c.incumbent))

    def test_1205_single_byte_mutations_reject(self):
        raw = VALID[0]
        self.assertEqual(len(raw), 225)
        c = decode_certificate(raw)
        policy = trusted_policy()
        count = 0
        for position, original in enumerate(raw):
            for substitute in b"01|+-X":
                if substitute == original:
                    continue
                count += 1
                mutant = raw[:position] + bytes([substitute]) + raw[position+1:]
                self.assertFalse(
                    reference_certificate_passes(mutant, policy, 0, c.incumbent),
                    (position, substitute))
        self.assertEqual(count, 1205)

    def test_malformed_and_wrong_format(self):
        bad = (
            b"", b"PGSC5|6|1", b"PGSC6", b"PGSC6|", b"PGSC6|-0",
            b"PGSC6|+6", b"PGSC6|06", b"PGSC6|6|01",
            VALID[0] + b"\n", VALID[0]+b"|1",
            b"\xef\xbb\xbf"+VALID[0], VALID[0]+b"\0",
        )
        for raw in bad:
            with self.subTest(raw=raw[:30]), self.assertRaises(CertificateReject):
                decode_certificate(raw)

    def test_reference_is_not_a_signature_or_kernel_check(self):
        self.assertFalse(reference_certificate_passes(
            VALID[0], trusted_policy(), 0, b"PGSI2-WIDE|0|0"))
        with self.assertRaises(TypeError):
            reference_certificate_passes(VALID[0], trusted_policy(), -1.0, b"")


if __name__ == "__main__":
    unittest.main()
