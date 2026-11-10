"""Independent file-retention counterexamples against signed ACK replay."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from .destination_reference import DOMAIN, hash_struct, canonical, DestinationProofError
from .receiver_readback_v16 import readback

class ReceiverReadbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.directory=Path(self.tmp.name)
        key=Ed25519PrivateKey.generate()
        self.public=key.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        self.data=b"official receipt contents"
        did='1'*64
        identity=hash_struct({'kind':'writ/destination-route/1',
                 'endpoint':'approved','receiver':self.public.hex(),'directory':did})
        route=hash_struct({'sink':'feed','tool':'file','endpoint':'approved','destination':identity})
        self.body={'version':'writ/destination-receipt/1',
            'policy_hash':'2'*64,'effect_id':1,'action':'publish','sink':'feed',
            'endpoint':'approved','route_id':route,
            'digest':hashlib.sha256(self.data).hexdigest(),'size':len(self.data),
            'nonce':'3'*32,'directory_identity':did,'outcome':'durably_written'}
        self.ack={'body':self.body,
                 'signature':key.sign(DOMAIN+canonical(self.body)).hex()}
        self.expected={k:self.body[k] for k in (
            'policy_hash','effect_id','action','sink','endpoint','route_id','digest','size','nonce')}
        self.file=self.directory/'writ-000000000001.bin'
        self.file.write_bytes(self.data)
        self.journal=self.directory/'writ-000000000001.ack.json'
        self.journal.write_bytes(canonical(self.ack))
    def tearDown(self):
        self.tmp.cleanup()
    def test_positive(self):
        self.assertEqual(readback(self.directory,self.ack,self.public,self.expected)['size'],len(self.data))
    def test_historical_signature_valid_even_when_file_deleted(self):
        self.file.unlink()
        with self.assertRaises(DestinationProofError):
            readback(self.directory,self.ack,self.public,self.expected)
    def test_reject_changed_bytes(self):
        self.file.write_bytes(b'Z'*len(self.data))
        with self.assertRaises(DestinationProofError):
            readback(self.directory,self.ack,self.public,self.expected)
    def test_reject_symlink(self):
        self.file.unlink()
        (self.directory/'replacement').write_bytes(self.data)
        self.file.symlink_to('replacement')
        with self.assertRaises(DestinationProofError):
            readback(self.directory,self.ack,self.public,self.expected)
    def test_reject_missing_or_modified_journal(self):
        self.journal.unlink()
        with self.assertRaises(DestinationProofError):
            readback(self.directory,self.ack,self.public,self.expected)
        self.journal.write_bytes(b'{}')
        with self.assertRaises(DestinationProofError):
            readback(self.directory,self.ack,self.public,self.expected)
if __name__=='__main__':
    unittest.main()
