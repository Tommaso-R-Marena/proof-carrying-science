"""Falsification tests for shared ancestor quota and sticky revocation."""
import unittest
from research.writ_authority_v9.core import PolicyError, Scope, parse_hops
from research.writ_authority_v9.trace import Admit, Revoke, replay

POLICY = """
delegate root_worker from owner to worker actions publish uses 3 clearance public limit 512 bytes;
subdelegate left from root_worker to left_worker actions publish uses 3 clearance public limit 256 bytes;
subdelegate right from root_worker to right_worker actions publish uses 3 clearance public limit 256 bytes;
"""
ROOT = Scope(frozenset({"publish", "review"}), 2, 1024, 5)
HOPS = parse_hops(POLICY)
LEFT = Admit("left_worker", "left", "publish", 0, 60)
RIGHT = Admit("right_worker", "right", "publish", 0, 60)

class TraceTests(unittest.TestCase):
    def test_shared_ancestor_is_not_double_spent_by_siblings(self):
        result = replay(HOPS, ROOT, (LEFT, RIGHT, LEFT))
        self.assertEqual(result.admitted, 3)
        self.assertEqual(result.debit_count, 6)
        self.assertEqual(result.delegation_remaining,
                         {"root_worker":0, "left":1, "right":2})
        self.assertEqual(result.root_remaining, 2)
        with self.assertRaisesRegex(PolicyError, "ancestor authority denied"):
            replay(HOPS, ROOT, (LEFT, RIGHT, LEFT, RIGHT))

    def test_ancestor_revocation_blocks_all_descendants(self):
        result = replay(HOPS, ROOT, (LEFT, Revoke("root_worker")))
        self.assertIn("root_worker", result.revoked)
        with self.assertRaisesRegex(PolicyError, "ancestor authority denied"):
            replay(HOPS, ROOT, (LEFT, Revoke("root_worker"), RIGHT))

    def test_leaf_revocation_does_not_revoke_unrelated_sibling(self):
        r = replay(HOPS, ROOT, (Revoke("left"), RIGHT))
        self.assertEqual(r.admitted, 1)
        with self.assertRaisesRegex(PolicyError, "ancestor authority denied"):
            replay(HOPS, ROOT, (Revoke("left"), LEFT))

    def test_disallow_forged_actor_or_action(self):
        with self.assertRaises(PolicyError):
            replay(HOPS, ROOT, (Admit("left_worker","right","publish",0,60),))
        with self.assertRaises(PolicyError):
            replay(HOPS, ROOT, (Admit("right_worker","right","review",0,60),))

    def test_root_quota_is_also_a_hard_cap(self):
        root = Scope(ROOT.actions, ROOT.clearance, ROOT.max_bytes, 2)
        # First-level delegation quota 3 exceeds this hypothetical root
        # and validation fails even before attempting to spend it.
        with self.assertRaises(PolicyError):
            replay(HOPS, root, (LEFT,))

    def test_no_repeated_revocation(self):
        with self.assertRaises(PolicyError):
            replay(HOPS, ROOT, (Revoke("left"), Revoke("left")))

if __name__ == "__main__":
    unittest.main()
