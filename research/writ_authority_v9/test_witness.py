"""Witness model falsification cases independent of the Writ/11 runtime."""
import unittest
from research.writ_authority_v9.witness_model import (
    Fingerprint, HostState, ready, commit_database, publish_witness, rollback_database
)

class WitnessModelTests(unittest.TestCase):
    def test_commit_without_witness_refuses_work(self):
        start=Fingerprint(0,'0'*64,'a'*64)
        next_identity=Fingerprint(1,'1'*64,'b'*64)
        state=HostState(start,start)
        after_db=commit_database(state,next_identity)
        self.assertFalse(ready(after_db))
        after_witness=publish_witness(after_db)
        self.assertTrue(ready(after_witness))
        self.assertFalse(ready(rollback_database(after_witness,start)))

    def test_same_sequence_different_snapshot_refused(self):
        start=Fingerprint(7,'7'*64,'a'*64)
        altered=Fingerprint(7,'7'*64,'b'*64)
        self.assertFalse(ready(HostState(altered,start)))

    def test_incomplete_checkpoint_requires_reconciliation(self):
        start=Fingerprint(1,'1'*64,'a'*64)
        next_identity=Fingerprint(2,'2'*64,'b'*64)
        intermediate=commit_database(HostState(start,start),next_identity)
        with self.assertRaises(ValueError):
            commit_database(intermediate,Fingerprint(3,'3'*64,'c'*64))

    def test_equal_snapshot_valid_but_not_proof_of_external_effect(self):
        same=Fingerprint(4,'4'*64,'z'*64)
        self.assertTrue(ready(HostState(same,same)))

if __name__=="__main__":
    unittest.main()
