"""Pure wire/standard crypto tests; no mocked mathematical authorization."""
from dataclasses import replace
import os
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from research.authorization_history_v1 import history
from . import protocol as p


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.public = self.key.public_key().public_bytes_raw()
        self.root = history.Root(bytes([1])*32, bytes([2])*32, b"policy", bytes([3])*32, b"genesis", b"wire")

    def test_rfc8032_empty_message_vector(self):
        public = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        private = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        signature = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
        Ed25519PublicKey.from_public_bytes(public).verify(signature, b"")
        self.assertEqual(Ed25519PrivateKey.from_private_bytes(private).sign(b""), signature)

    def test_signed_roundtrip_and_external_key_nonce_binding(self):
        nonce = os.urandom(32);e = p.sign(self.key, self.root, "checkpoint", {"x": 1}, nonce)
        self.assertEqual(p.verify(p.parse(p.canonical(e)), self.root, self.public, kind="checkpoint", nonce=nonce), {"x": 1})
        for root, key, kind, challenge in (
                (replace(self.root, genesis_id=b"other"), self.public, "checkpoint", nonce),
                (self.root, bytes(32), "checkpoint", nonce),
                (self.root, self.public, "prepared", nonce),
                (self.root, self.public, "checkpoint", bytes(32))):
            with self.subTest(kind=kind), self.assertRaises(p.Rejected):
                p.verify(e, root, key, kind=kind, nonce=challenge)

    def test_wrong_signature_domain_and_tamper_reject(self):
        e=p.sign(self.key,self.root,"prepared",{"artifact":"one"})
        e["signature"]=self.key.sign(p.canonical(e["statement"])).hex()
        with self.assertRaises(p.Rejected):p.verify(e,self.root,self.public,kind="prepared")
        e=p.sign(self.key,self.root,"prepared",{"artifact":"one"});e["statement"]["payload"]["artifact"]="two"
        with self.assertRaises(p.Rejected):p.verify(e,self.root,self.public,kind="prepared")

    def test_strict_canonical_wire(self):
        for raw in (b'{"a":1,"a":1}',b'{ "a":1}',b'{"a":NaN}',b'{"a":1}\n',b'\xff',b'['*2000+b']'*2000):
            with self.subTest(raw=raw[:20]),self.assertRaises(p.Rejected):p.parse(raw)
        with self.assertRaises(p.Rejected):p.parse(bytearray(b'{}'))
        with self.assertRaises(p.Rejected):p.parse(b'{}',1)

    def test_anchor_and_root_exact_roundtrip(self):
        a=history.initial(self.root)
        self.assertEqual(p.decode_anchor(p.encode_anchor(a)),a)
        self.assertEqual(p.root_from_json(p.parse(self.root.encode())),self.root)
        with self.assertRaises(p.Rejected):p.decode_anchor({**p.encode_anchor(a),"extra":0})
        with self.assertRaises(p.Rejected):p.decode_anchor({**p.encode_anchor(a),"generation":True})
        with self.assertRaises(p.Rejected):p.root_from_json({})

    def test_bounded_lowercase_hex(self):
        for value in ("AB", "0", "gg", None, 123, "aa"*4):
            with self.subTest(value=value),self.assertRaises(p.Rejected):p.unhex(value,maximum=3)
        with self.assertRaises(p.Rejected):p.unhex("00",length=2)

    def test_pinned_key_not_self_presented(self):
        attacker=Ed25519PrivateKey.generate();e=p.sign(attacker,self.root,"checkpoint",{})
        with self.assertRaises(p.Rejected):p.verify(e,self.root,self.public,kind="checkpoint")

    def test_whole_trusted_bootstrap_replacement_counterexample(self):
        # An observer who also replaces its only trusted key/root can authenticate
        # an entirely different world. This is not protection against all-root compromise.
        attacker=Ed25519PrivateKey.generate();other=replace(self.root,genesis_id=b"replacement")
        e=p.sign(attacker,other,"checkpoint",{"replacement_world":True})
        self.assertTrue(p.verify(e,other,attacker.public_key().public_bytes_raw(),kind="checkpoint")["replacement_world"])

    def test_oversized_event_identifier_rejects_before_authority(self):
        payload=history.proposed_payload(self.root,history.initial(self.root),event_id=b"x"*257,candidate=b"wire",certificate=b"")
        e=history.Envelope(payload,bytes(64),bytes(64))
        with self.assertRaises(p.Rejected):p.checked_intent(e.encode())


if __name__ == "__main__":unittest.main(verbosity=2)
