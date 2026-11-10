"""Exact ceremony verification, targeted tampering, and falsification tests."""
import base64
from copy import deepcopy
from fractions import Fraction
import unittest
from . import kernel as k
from .make_demo import example
from research.evidencekernel_propensity_v25 import kernel as v25


def pinned(c,p,e):
    cp=v25.digest(c);sp=v25.digest(p)
    ep=v25.digest({'domain':'pcs-ek-v28-witness-records','contract_pin':cp,
                   'study_pin':sp,'evidence':e})
    return cp,sp,ep


class WitnessVerification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c,cls.p,cls.e,cls.pins,cls.report=example(n=64)

    def trial(self,c=None,p=None,e=None,pins=None):
        c=deepcopy(self.c if c is None else c)
        p=deepcopy(self.p if p is None else p)
        e=deepcopy(self.e if e is None else e)
        return k.audit(c,p,e,contract_pin=(pins or pinned(c,p,e))[0],
                       study_pin=(pins or pinned(c,p,e))[1],
                       evidence_pin=(pins or pinned(c,p,e))[2])

    def test_signed_transcript_reproduces_receiver(self):
        x=self.trial();self.assertEqual(x['verified_signed_draws'],64)
        self.assertEqual(x['exact_treatment_probabilities_by_state'],['1/2','3/4'])
        self.assertEqual(x['conditional_scientific_report']['status'],x['status'])

    def test_attacker_cannot_replace_treatment_and_repin(self):
        e=deepcopy(self.e);e['draws'][7]['action']^=1
        with self.assertRaises(k.Reject):self.trial(e=e)

    def test_attacker_cannot_change_reveal_and_repin(self):
        e=deepcopy(self.e)
        s=e['draws'][1]['operator_share_hex'];e['draws'][1]['operator_share_hex']=('00' if s[:2]!='00' else 'ff')+s[2:]
        with self.assertRaises(k.Reject):self.trial(e=e)

    def test_attacker_cannot_change_signed_report_and_repin(self):
        e=deepcopy(self.e);e['draws'][2]['report']^=1
        with self.assertRaises(k.Reject):self.trial(e=e)

    def test_attacker_cannot_truncate_unexpected_enrollments(self):
        e=deepcopy(self.e);e['draws']=e['draws'][:-1];e['true_intervals']=e['true_intervals'][:-1]
        with self.assertRaises(k.Reject):self.trial(e=e)

    def test_attacker_cannot_suppress_middle_draw(self):
        e=deepcopy(self.e);del e['draws'][7];del e['true_intervals'][7]
        with self.assertRaises(k.Reject):self.trial(e=e)

    def test_attacker_cannot_swap_records(self):
        e=deepcopy(self.e);e['draws'][10],e['draws'][11]=e['draws'][11],e['draws'][10]
        with self.assertRaises(k.Reject):self.trial(e=e)

    def test_attacker_cannot_swap_witness_receipt(self):
        e=deepcopy(self.e)
        e['draws'][0]['commit_receipt_signature_b64']=e['draws'][1]['commit_receipt_signature_b64']
        with self.assertRaises(k.Reject):self.trial(e=e)

    def test_attacker_cannot_fake_witness_key(self):
        c=deepcopy(self.c)
        c['witness_public_key_b64']=base64.b64encode(b'\x01'*32).decode()
        with self.assertRaises(k.Reject):self.trial(c=c)

    def test_study_tuning_must_match_physically_witnessed_probabilities(self):
        p=deepcopy(self.p)
        p['propensity_upper_by_state'][0]='3/4'
        with self.assertRaises(k.Reject):self.trial(p=p)

    def test_ceremony_cannot_rebind_to_changed_study(self):
        p=deepcopy(self.p);p['max_interval_misses']=1
        with self.assertRaises(k.Reject):self.trial(p=p)

    def test_control_outcome_record_can_change_only_with_new_external_pin(self):
        e=deepcopy(self.e);e['true_intervals'][0]='01'
        with self.assertRaises(k.Reject):
            k.audit(self.c,self.p,e,contract_pin=self.pins[0],
                    study_pin=self.pins[1],evidence_pin=self.pins[2])
        valid=self.trial(e=e)
        self.assertEqual(valid['verified_signed_draws'],64)

    def test_one_hidden_uniform_share_suffices_for_exact_mapping(self):
        # Enumerate every possible top byte of one share, fixing the adversary's share.
        fixed='a5'*32
        for prob,expected in ((Fraction(1,2),128),(Fraction(3,4),192)):
            count=0
            for i in range(256):
                honest=f'{i:02x}'+'00'*31
                count+=k.treatment_from_shares(fixed,honest,8,prob)
            self.assertEqual(count,expected)

    def test_invalid_probability_grid_fails_closed(self):
        with self.assertRaises(k.Reject):
            k.treatment_from_shares('00'*32,'00'*32,8,Fraction(1,3))

    def test_selective_abort_destroys_allocation_law(self):
        # If an operator can refuse a draw after seeing the witness share,
        # conditional on a COMPLETED draw the treatment probability becomes 1.
        fixed='00'*32
        attempts=[k.treatment_from_shares(fixed,f'{x:02x}'+'00'*31,8,Fraction(1,2))
                  for x in range(256)]
        self.assertEqual(sum(attempts),128)
        kept=[v for v in attempts if v==1]
        self.assertEqual(sum(kept),len(kept))
        self.assertEqual(Fraction(sum(kept),len(kept)),1)

    def test_modulo_shortcut_is_not_exact_for_non_power_of_two(self):
        counts=[sum(x%3==j for x in range(256)) for j in range(3)]
        self.assertEqual(counts,[86,85,85])

if __name__=='__main__':unittest.main()
