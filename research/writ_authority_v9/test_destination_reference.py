import hashlib
import unittest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization
from research.writ_authority_v9.destination_reference import (
    check_ack, canonical, hash_struct, DOMAIN, DestinationProofError
)

def public(private):
    return private.public_key().public_bytes(serialization.Encoding.Raw,
                                              serialization.PublicFormat.Raw)

class IndependentReceiverTests(unittest.TestCase):
    def setUp(self):
        self.receiver=Ed25519PrivateKey.generate()
        self.operator=Ed25519PrivateKey.generate()
        self.pub=public(self.receiver)
        directory='a'*64
        dest=hash_struct({'kind':'writ/destination-route/1','endpoint':'approved',
                          'receiver':self.pub.hex(),'directory':directory})
        route=hash_struct({'sink':'feed','tool':'file','endpoint':'approved','destination':dest})
        self.body={
            'version':'writ/destination-receipt/1','policy_hash':'b'*64,
            'effect_id':9,'action':'publish','sink':'feed','endpoint':'approved',
            'route_id':route,'digest':'c'*64,'size':23,'nonce':'d'*32,
            'directory_identity':directory,'outcome':'durably_written',
        }
        self.expected={k:self.body[k] for k in ('policy_hash','effect_id','action',
                             'sink','endpoint','route_id','digest','size','nonce')}
    def signed(self,priv=None,body=None):
        b=body or self.body
        return {'body':b,'signature':(priv or self.receiver).sign(DOMAIN+canonical(b)).hex()}
    def test_valid(self):
        self.assertTrue(check_ack(self.signed(),self.pub,self.expected))
    def test_operator_re_signing_is_not_receiver_evidence(self):
        with self.assertRaisesRegex(DestinationProofError,'receiver signature'):
            check_ack(self.signed(self.operator),self.pub,self.expected)
    def test_independent_intent_binding(self):
        for k,v in (('nonce','e'*32),('effect_id',10),('route_id','e'*64),
                    ('policy_hash','e'*64),('digest','e'*64),('sink','other'),
                    ('action','delete'),('size',24),('endpoint','other')):
            with self.subTest(field=k),self.assertRaises(DestinationProofError):
                check_ack(self.signed(),self.pub,{**self.expected,k:v})
    def test_even_receiver_signed_wrong_route_refused(self):
        b={**self.body,'route_id':'f'*64}
        with self.assertRaisesRegex(DestinationProofError,'route/identity'):
            check_ack(self.signed(body=b),self.pub,{**self.expected,'route_id':'f'*64})
    def test_malformed_or_boolean_effect_is_refused(self):
        b={**self.body,'effect_id':True}
        with self.assertRaisesRegex(DestinationProofError,'effect id'):
            check_ack(self.signed(body=b),self.pub,{**self.expected,'effect_id':True})

if __name__=='__main__':
    unittest.main()
