"""Writ/18 reference checks: genuine keys, signed nonce, durable first-claim."""
import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from .destination_reference import DOMAIN, canonical, hash_struct, DestinationProofError
from .claim_readback_reference_v18 import (
    DOMAIN18,claim_link,verify_claim_readback,check_current_local_claim
)

class ClaimReadbackTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.path=Path(self.t.name)
        self.priv=Ed25519PrivateKey.generate()
        self.public=self.priv.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        self.payload=b'this exact original payload'
        directory='f'*64
        ident=hash_struct({'kind':'writ/destination-route/1',
                           'endpoint':'approved','receiver':self.public.hex(),
                           'directory':directory})
        route=hash_struct({'sink':'feed','tool':'file','endpoint':'approved','destination':ident})
        self.ackbody={'version':'writ/destination-receipt/1','policy_hash':'a'*64,
            'effect_id':5,'action':'publish','sink':'feed','endpoint':'approved',
            'route_id':route,'digest':hashlib.sha256(self.payload).hexdigest(),
            'size':len(self.payload),'nonce':'b'*32,'directory_identity':directory,
            'outcome':'durably_written'}
        self.ack={'body':self.ackbody,
                  'signature':self.priv.sign(DOMAIN+canonical(self.ackbody)).hex()}
        self.expected={k:self.ackbody[k] for k in
                       ('policy_hash','effect_id','action','sink','endpoint',
                        'route_id','digest','size','nonce')}
        self.challenge='c'*32
        self.proofbody={'version':'writ/retention-proof/2',
            'challenge':self.challenge,'ack_hash':hash_struct(self.ack),
            'policy_hash':self.ackbody['policy_hash'],'effect_id':5,
            'route_id':route,'payload_digest':self.ackbody['digest'],
            'size':len(self.payload),'lease_nonce':'b'*32,
            'directory_identity':directory,
            'outcome':'present_at_challenge','claim_link':claim_link(self.ackbody)}
        self.file=self.path/'writ-000000000005.bin'
        self.claim=self.path/'writ-000000000005.claim.json'
        self.ackfile=self.path/'writ-000000000005.ack.json'
        self.file.write_bytes(self.payload)
        self.ackfile.write_bytes(canonical(self.ack))
        request={k:self.ackbody[k] for k in
                 ('policy_hash','effect_id','action','sink','endpoint','route_id',
                  'digest','size','nonce')}
        request['version']='writ/destination-request/1'
        request['payload_b64']=base64.b64encode(self.payload).decode()
        claimed={'version':'writ/receiver-claim/1','effect_id':5,
                 'request_hash':hash_struct(request),
                 'digest':self.ackbody['digest'],'lease_nonce':'b'*32}
        self.claim.write_bytes(canonical(claimed))
    def tearDown(self):
        self.t.cleanup()
    def signed(self,body=None,key=None,domain=DOMAIN18):
        body=body or self.proofbody
        key=key or self.priv
        return {'body':body,'signature':key.sign(domain+canonical(body)).hex()}
    def test_exact_fresh_proof_and_first_claim(self):
        self.assertEqual(verify_claim_readback(self.signed(),self.ack,self.public,
                         self.expected,self.challenge)['claim_link'],claim_link(self.ackbody))
        self.assertTrue(check_current_local_claim(self.path,self.ack,self.public,
                         self.expected,self.payload))
    def test_historical_ack_does_not_replace_missing_claim(self):
        self.claim.unlink()
        # Historical signature remains valid; independent current claim does not.
        verify_claim_readback(self.signed(),self.ack,self.public,
                              self.expected,self.challenge)
        with self.assertRaises(DestinationProofError):
            check_current_local_claim(self.path,self.ack,self.public,
                                      self.expected,self.payload)
    def test_modified_or_symlinked_claim_rejected(self):
        self.claim.write_text('{}')
        with self.assertRaises(DestinationProofError):
            check_current_local_claim(self.path,self.ack,self.public,self.expected,self.payload)
        self.claim.unlink()
        (self.path/'other').write_bytes(b'{}')
        self.claim.symlink_to('other')
        with self.assertRaises(DestinationProofError):
            check_current_local_claim(self.path,self.ack,self.public,self.expected,self.payload)
    def test_wrong_challenge_and_claim_link_rejected_even_if_signed(self):
        with self.assertRaises(DestinationProofError):
            verify_claim_readback(self.signed(),self.ack,self.public,
                                  self.expected,'e'*32)
        with self.assertRaises(DestinationProofError):
            verify_claim_readback(self.signed({**self.proofbody,'claim_link':'0'*64}),
                                  self.ack,self.public,self.expected,self.challenge)
    def test_old_version_signature_and_operator_key_refused(self):
        with self.assertRaises(DestinationProofError):
            verify_claim_readback(self.signed(domain=b'writ-v16/retention-proof\x00'),
                                  self.ack,self.public,self.expected,self.challenge)
        other=Ed25519PrivateKey.generate()
        with self.assertRaises(DestinationProofError):
            verify_claim_readback(self.signed(key=other),self.ack,self.public,
                                  self.expected,self.challenge)
    def test_bad_payload_or_missing_ack_refused(self):
        self.file.write_bytes(b'X'*len(self.payload))
        with self.assertRaises(DestinationProofError):
            check_current_local_claim(self.path,self.ack,self.public,self.expected,self.payload)
        self.file.write_bytes(self.payload)
        self.ackfile.unlink()
        with self.assertRaises(DestinationProofError):
            check_current_local_claim(self.path,self.ack,self.public,self.expected,self.payload)

if __name__=='__main__':
    unittest.main()
