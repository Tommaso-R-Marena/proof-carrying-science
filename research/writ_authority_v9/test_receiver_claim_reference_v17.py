"""Tests of a self-contained receiver claim reference implementation."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
import base64
import hashlib
from pathlib import Path
import tempfile
import unittest

from research.writ_authority_v9.receiver_claim_reference_v17 import (
    ClaimError, reserve, expected_claim
)

PAYLOAD = b"published research evidence"
BASE = {"version": "writ/destination-request/1", "policy_hash": "a"*64,
        "effect_id": 1, "action": "publish", "sink": "feed",
        "endpoint": "approved", "route_id": "b"*64,
        "digest": hashlib.sha256(PAYLOAD).hexdigest(),
        "size": len(PAYLOAD), "nonce": "1"*32,
        "payload_b64": base64.b64encode(PAYLOAD).decode("ascii")}


class ClaimReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        self.claim = self.path / "writ-000000000001.claim.json"
        self.output = self.path / "writ-000000000001.bin"
        self.ack = self.path / "writ-000000000001.ack.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_first_reservation_and_same_request_no_second_write(self):
        self.assertTrue(reserve(BASE, self.path))
        self.assertEqual(self.claim.read_bytes(), expected_claim(BASE))
        self.assertFalse(reserve(BASE, self.path))

    def test_conflicting_nonce_refused_after_crash(self):
        self.assertTrue(reserve(BASE, self.path))
        with self.assertRaisesRegex(ClaimError, "conflicting"):
            reserve({**BASE, "nonce": "2"*32}, self.path)

    def test_missing_ack_does_not_authorize_reexecution(self):
        self.assertTrue(reserve(BASE, self.path))
        self.output.write_bytes(PAYLOAD)
        # The receiver can only return True for first claim. False does not
        # authorize a fresh ACK; no ACK exists after this simulated crash.
        self.assertFalse(reserve(BASE, self.path))
        self.assertFalse(self.ack.exists())

    def test_existing_output_without_claim_is_uncertain(self):
        self.output.write_bytes(PAYLOAD)
        with self.assertRaisesRegex(ClaimError, "orphan"):
            reserve(BASE, self.path)

    def test_existing_ack_without_claim_is_uncertain(self):
        self.ack.write_text("{}")
        with self.assertRaisesRegex(ClaimError, "orphan"):
            reserve(BASE, self.path)

    def test_claim_symlink_refused(self):
        (self.path / "elsewhere").write_bytes(expected_claim(BASE))
        self.claim.symlink_to("elsewhere")
        with self.assertRaises(OSError):
            reserve(BASE, self.path)

    def test_concurrent_conflicting_reservations(self):
        left, right = BASE, {**BASE, "nonce": "2"*32}
        def attempt(request):
            try:
                return reserve(request, self.path)
            except ClaimError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(attempt, (left, right)))
        self.assertEqual(result.count(True), 1)
        self.assertEqual(result.count(False), 1)

    def test_altered_request_invalidates_durable_claim(self):
        self.assertTrue(reserve(BASE, self.path))
        for field, new_value in (("nonce", "f"*32),
                                 ("digest", "f"*64),
                                 ("route_id", "e"*64),
                                 ("effect_id", 2),
                                 ("payload_b64", "AA==")):
            with self.subTest(field=field):
                if field == "effect_id":
                    continue  # different ID is a different claim namespace
                with self.assertRaisesRegex(ClaimError, "conflicting"):
                    reserve({**BASE, field: new_value}, self.path)


if __name__ == "__main__":
    unittest.main()
