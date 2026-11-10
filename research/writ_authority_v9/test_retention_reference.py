"""Independent Writ/16 challenge/receipt binding falsification cases."""
import hashlib
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from .destination_reference import (
    DOMAIN, hash_struct, canonical, DestinationProofError
)
from .retention_reference import check_fresh_readback, PROOF_DOMAIN

class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.receiver=Ed25519PrivateKey.generate()
        self.operator=Ed25519PrivateKey.generate()
        self.public=self.receiver.public_key().public_bytes(
            serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        directory='a'*64
        dest=hash_struct({'kind':'writ/destination-route/1',
                          'endpoint':'approved','receiver':self.public.hex(),
                          'directory':directory})
        route=hash_struct({'sink':'feed','tool':'file','endpoint':'approved',
                           'destination':dest})
        body={'version':'writ/destination-receipt/1',
              'policy_hash':'b'*64,'effect_id':1,'action':'publish',
              'sink':'feed','endpoint':'approved','route_id':route,
              'digest':'c'*64,'size':10,'nonce':'d'*32,
              'directory_identity':directory,'outcome':'durably_written'}
        self.ack={'body':body,'signature':self.receiver.sign(DOMAIN+canonical(body)).hex()}
        self.expected={k:body[k] for k in ('policy_hash','effect_id','action','sink',
                                          'endpoint','route_id','digest','size','nonce')}
        self.challenge='e'*32
        self.proofbody={
            'version':'writ/retention-proof/1','challenge':self.challenge,
            'ack_hash':hashlib.sha256(canonical(self.ack)).hexdigest(),
            'policy_hash':body['policy_hash'],'effect_id':body['effect_id'],
            'route_id':body['route_id'],'payload_digest':body['digest'],
            'size':body['size'],'lease_nonce':body['nonce'],
            'directory_identity':directory,'outcome':'present_at_challenge'}
    def signed(self,body=None,signer=None):
        body=body or self.proofbody
        signer=signer or self.receiver
        return {'body':body,'signature':signer.sign(PROOF_DOMAIN+canonical(body)).hex()}
    def test_positive(self):
        self.assertTrue(check_fresh_readback(
            self.signed(),self.ack,self.public,self.challenge,self.expected))
    def test_valid_historical_signature_is_not_fresh(self):
        with self.assertRaises(DestinationProofError):
            check_fresh_readback(self.signed(),self.ack,self.public,'f'*32,self.expected)
    def test_operator_cannot_fake_receiver_signature(self):
        with self.assertRaises(DestinationProofError):
            check_fresh_readback(self.signed(signer=self.operator),self.ack,
                                  self.public,self.challenge,self.expected)
    def test_rebound_receipt_rejected_even_if_receiver_signs(self):
        for field,value in (
            ('ack_hash','0'*64),('payload_digest','0'*64),('lease_nonce','0'*32),
            ('route_id','1'*64),('effect_id',9),('directory_identity','1'*64),
            ('outcome','failed')):
            with self.subTest(field=field),self.assertRaises(DestinationProofError):
                check_fresh_readback(self.signed({**self.proofbody,field:value}),
                                      self.ack,self.public,self.challenge,self.expected)
    def test_wrong_expected_admission_rejected(self):
        with self.assertRaises(DestinationProofError):
            check_fresh_readback(self.signed(),self.ack,self.public,self.challenge,
                                  {**self.expected,'digest':'0'*64})
if __name__=='__main__':
    unittest.main()
