"""Reproducible synthetic witness demonstration: NOT genuine random/externally signed evidence.

The demo witness key is intentionally reproducible and NOT a trusted custodian.
No secret signing key is emitted into the research package.
"""
from pathlib import Path
import base64
from hashlib import sha256
import json
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from . import kernel as v28
from research.evidencekernel_propensity_v25 import kernel as v25

ROOT=Path(__file__).parent

def sign(key,body):
    return base64.b64encode(key.sign(v28.signature_message(body))).decode()


def example(n=256):
    key=Ed25519PrivateKey.from_private_bytes(sha256(b'SYNTHETIC-UNTRUSTED-EK-v28-signature-key').digest())
    pub=key.public_key().public_bytes(encoding=serialization.Encoding.Raw,
                                      format=serialization.PublicFormat.Raw)
    transitions=[[[((s+a+r)%2) for r in (0,1)] for a in (0,1)] for s in (0,1)]
    stop=[[[False,False],[False,False]] for _ in range(2)]
    p={'assignment_model':'predictable_bernoulli_upper_bounded_fresh_randomness',
       'calibration_failure_bound':'1/100','confidence_alpha':'1/20',
       'estimand':'fixed_registered_cohort_binary_ate',
       'format':'pcs-evidencekernel-propensity-upper-v25',
       'initial_state':0,'interval_model':'binary_labels_with_max_misses',
       'max_interval_misses':0,'min_enrollment':n,
       'next_state_by_state_action_report':transitions,
       'null_ate_upper':'0','propensity_upper_by_state':['1/2','3/4'],
       'registered_units':n,'states':2,'stop_after_by_state_action_report':stop,
       'stopping_rule':'registered_feedback_fsm',
       'tuning':[{'alpha_spend':'1/20','lambda':'1/16','log_upper':'4',
                  'reference_weights_by_state':[[1,1],[1,3]],'taylor_terms':16}]}
    sp=v25.digest(p)
    c={'format':v28.FORMAT,'v25_protocol_sha256':sp,
       'witness_public_key_b64':base64.b64encode(pub).decode(),
       'denominator_bits':8,'registered_units':n}
    cp=v25.digest(c)
    history=[];prev=cp;state=0;labels=[]
    qs=[v28.F(1,2),v28.F(3,4)]
    for i in range(n):
        os=sha256(f'SYNTHETIC-NOT-UNPREDICTABLE-operator-{i}'.encode()).hexdigest()
        ws=sha256(f'SYNTHETIC-NOT-UNPREDICTABLE-witness-{i}'.encode()).hexdigest()
        oc=v28.commit_share('operator',cp,i,prev,os)
        wc=v28.commit_share('witness',cp,i,prev,ws)
        commit=v28.commitment_body(cp,i,prev,state,oc,wc)
        receipt=sign(key,commit)
        a=v28.treatment_from_shares(os,ws,8,qs[state])
        r=a  # noisy/reporting policy synthetic example; actual endpoint is separately modeled
        draw=v28.reveal_body(cp,commit,receipt,os,ws,a,r)
        row={'index':i,'prev_sha256':prev,'state':state,
             'operator_commit_sha256':oc,'witness_commit_sha256':wc,
             'commit_receipt_signature_b64':receipt,'operator_share_hex':os,
             'witness_share_hex':ws,'action':a,'report':r,
             'draw_signature_b64':sign(key,draw)}
        history.append(row)
        labels.append('1' if a==1 else '0')
        prev=v25.digest(row)
        state=transitions[state][a][r]
    e={'draws':history,'true_intervals':labels}
    ep=v25.digest({'domain':'pcs-ek-v28-witness-records',
                   'contract_pin':cp,'study_pin':sp,'evidence':e})
    report=v28.audit(c,p,e,contract_pin=cp,study_pin=sp,evidence_pin=ep)
    return c,p,e,(cp,sp,ep),report


def main():
    c,p,e,pins,report=example()
    for name,val in [('example_ceremony_contract.json',c),('example_study_protocol.json',p),
                     ('example_witness_evidence.json',e),('example_report.json',report)]:
        (ROOT/name).write_text(json.dumps(val,sort_keys=True,indent=2)+'\n')
    for name,pin in zip(('example_contract_pin.txt','example_study_pin.txt','example_evidence_pin.txt'),pins):
        (ROOT/name).write_text(pin+'\n')
    print('Conditional synthetic bound',report['conditional_lower_ate'],
          'verified',report['verified_signed_draws'],'signed draws')

if __name__=='__main__':main()
