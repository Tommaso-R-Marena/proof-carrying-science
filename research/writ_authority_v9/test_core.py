"""Independent Writ/9 scope-chain regression suite (stdlib unittest)."""
import unittest
from research.writ_authority_v9.core import (
    Scope, PolicyError, parse_hops, validate_chain, admissible, debit, attenuates,
)

DECL = """
delegate a from publisher to analyst actions publish,review uses 4 clearance internal limit 512 bytes;
subdelegate b from a to reviewer actions publish uses 3 clearance public limit 256 bytes;
subdelegate c from b to publisher_bot actions publish uses 2 clearance public limit 128 bytes;
"""
ROOT = Scope(frozenset({"publish", "review", "revoke"}), 2, 1024, 8)

class TestWritAuthority(unittest.TestCase):
    def setUp(self):
        self.path = validate_chain(parse_hops(DECL), "c", ROOT)

    def test_full_chain(self):
        self.assertEqual([h.actor for h in self.path], ["analyst", "reviewer", "publisher_bot"])

    def test_nonamplification(self):
        self.assertTrue(attenuates(self.path[-1].scope, ROOT))
        self.assertFalse(attenuates(ROOT, self.path[-1].scope))

    def test_hierarchical_quota_debit(self):
        remaining = {"a": 4, "b": 3, "c": 2}
        self.assertEqual(debit(self.path, remaining), {"a": 3, "b": 2, "c": 1})
        self.assertEqual(remaining, {"a": 4, "b": 3, "c": 2})

    def test_ancestor_revocation_fails_closed(self):
        remaining = {"a": 4, "b": 3, "c": 2}
        self.assertTrue(admissible(self.path, action="publish", label=0,
                                   size=64, remaining=remaining))
        for ancestor in ("a", "b", "c"):
            self.assertFalse(admissible(
                self.path, action="publish", label=0, size=64,
                remaining=remaining, revoked=frozenset({ancestor})))

    def test_effective_scope_rejections(self):
        remaining = {"a": 4, "b": 3, "c": 2}
        for action, label, size in (
            ("review", 0, 64), ("publish", 1, 64), ("publish", 0, 129)):
            self.assertFalse(admissible(
                self.path, action=action, label=label, size=size,
                remaining=remaining))
        self.assertFalse(admissible(
            self.path, action="publish", label=0, size=64,
            remaining={"a": 4, "b": 0, "c": 2}))

    def test_invalid_ancestry(self):
        cases = [
            ("uses 2 clearance", "uses 5 clearance"),
            ("limit 128 bytes", "limit 800 bytes"),
            ("to publisher_bot", "to analyst"),
            ("actions publish uses 2", "actions revoke uses 2"),
            ("from b to publisher_bot", "from c to publisher_bot"),
        ]
        for original, bad in cases:
            with self.subTest(bad=bad), self.assertRaises(PolicyError):
                validate_chain(parse_hops(DECL.replace(original, bad)), "c", ROOT)

    def test_parser_rejects_unknown_and_duplicate_actions(self):
        with self.assertRaises(PolicyError):
            parse_hops(DECL + "\nexecute arbitrary shell;")
        with self.assertRaises(PolicyError):
            parse_hops(DECL.replace("publish,review", "publish,publish"))

if __name__ == "__main__":
    unittest.main()
