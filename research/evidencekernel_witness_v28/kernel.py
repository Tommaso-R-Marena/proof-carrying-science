"""EvidenceKernel v28: two-party commit/reveal witness receipts for treatment allocation.

Research-only. Assumes an independent, honest chronology-enforcing witness,
private unpredictable shares, full custody and no selective abort, plus the
underlying v25 causal/measurement premises. Cryptography proves neither
physical randomness nor honesty, time order, or absence of omitted enrollments.
"""
from __future__ import annotations
import argparse
import base64
from fractions import Fraction
from hashlib import sha256
import json
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from research.evidencekernel_propensity_v25 import kernel as v25

check=v25.check
Reject=v25.Reject
D=v25.digest
F=Fraction
FORMAT='pcs-evidencekernel-witness-ceremony-v28'
RESULT='pcs-evidencekernel-witness-audit-v28'
WKEYS={'format','v25_protocol_sha256','witness_public_key_b64','denominator_bits','registered_units'}
EKEYS={'draws','true_intervals'}
DRAW={'index','prev_sha256','state','operator_commit_sha256','witness_commit_sha256',
      'commit_receipt_signature_b64','operator_share_hex','witness_share_hex',
      'action','report','draw_signature_b64'}


def bytes32(s,label):
    check(type(s) is str and len(s)==64 and all(c in '0123456789abcdef' for c in s),
          'invalid '+label)
    return bytes.fromhex(s)


def decode_b64(s,size,label):
    check(type(s) is str and len(s)<=200,'invalid '+label)
    try:
        b=base64.b64decode(s,validate=True)
    except (ValueError,base64.binascii.Error) as e:
        raise Reject('malformed '+label) from e
    check(len(b)==size and base64.b64encode(b).decode()==s,
          'noncanonical '+label)
    return b


def signature_message(body):
    return json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def commit_share(role,protocol_pin,index,previous,share):
    check(role in ('operator','witness'),'unknown role')
    bytes32(share,'share')
    bytes32(protocol_pin,'protocol pin')
    bytes32(previous,'prior record pin')
    check(type(index) is int and index>=0,'invalid share index')
    msg=f'pcs-evidencekernel-v28-share|{role}|{protocol_pin}|{index}|{previous}|{share}'
    return sha256(msg.encode('ascii')).hexdigest()


def commitment_body(protocol_pin,index,previous,state,operator_commit,witness_commit):
    return {'domain':'pcs-ek-v28-both-committed', 'protocol_sha256':protocol_pin,
            'index':index,'prev_sha256':previous,'state':state,
            'operator_commit_sha256':operator_commit,
            'witness_commit_sha256':witness_commit}


def reveal_body(protocol_pin,commitment,receipt_sig,operator_share,witness_share,action,report):
    return {'domain':'pcs-ek-v28-draw-revealed','protocol_sha256':protocol_pin,
            'commitment':commitment,'commit_receipt_signature_b64':receipt_sig,
            'operator_share_hex':operator_share,'witness_share_hex':witness_share,
            'action':action,'report':report}


def verify_sig(pub,body,signature):
    sig=decode_b64(signature,64,'witness signature')
    try:
        pub.verify(sig,signature_message(body))
    except Exception as e:
        raise Reject('witness signature verification failed') from e


def treatment_from_shares(operator_share,witness_share,bits,prob):
    """Exact fair uniform integer from XOR of independent 256-bit shares.

    This preserves a true Bernoulli threshold when at least one share is fresh
    uniform and independent of the other *conditional on the past and prior commits*.
    No hash-to-range modulo bias or random-oracle assumption is needed.
    """
    x=int.from_bytes(bytes(a^b for a,b in zip(bytes32(operator_share,'operator share'),
                                               bytes32(witness_share,'witness share'))),'big')
    check(type(bits) is int and 1<=bits<=20,'unsupported denominator bits')
    check(type(prob) is F and 0<prob<1,'invalid treatment probability')
    denom=1<<bits
    numer=prob*denom
    check(numer.denominator==1 and 0<numer<denom,
          'reference probability is not exactly representable with this denominator')
    return int((x>>(256-bits))<int(numer))


def audit(contract,study_protocol,evidence,*,contract_pin,study_pin,evidence_pin):
    v25.verify_pin(contract_pin);v25.verify_pin(study_pin);v25.verify_pin(evidence_pin)
    check(D(contract)==contract_pin,'ceremony contract digest mismatch')
    check(D(study_protocol)==study_pin,'study protocol digest mismatch')
    check(D({'domain':'pcs-ek-v28-witness-records','contract_pin':contract_pin,
             'study_pin':study_pin,'evidence':evidence})==evidence_pin,
          'witness transcript external commitment mismatch')
    v25.exact_keys(contract,WKEYS,'witness ceremony registration')
    v25.exact_keys(evidence,EKEYS,'witness evidence')
    check(contract['format']==FORMAT and contract['v25_protocol_sha256']==study_pin,
          'study/ceremony binding mismatch')
    d=v25.design(study_protocol)
    bits=contract['denominator_bits'];n=contract['registered_units']
    check(type(bits) is int and 1<=bits<=20 and
          type(n) is int and n==d['n'],'unsupported witness denominator or cohort size')
    public_bytes=decode_b64(contract['witness_public_key_b64'],32,'public key')
    pub=Ed25519PublicKey.from_public_bytes(public_bytes)
    probabilities=[]
    for s in range(d['S']):
        q=d['tune'][0]['qs'][s]
        check(d['upper'][s]==q and all(cfg['qs'][s]==q for cfg in d['tune']),
              'scientific receiver must use exact witnessed propensity at every state')
        treatment_from_shares('00'*32,'00'*32,bits,q)
        probabilities.append(q)
    draws=evidence['draws'];labels=evidence['true_intervals']
    check(type(draws) is list and d['min']<=len(draws)<=d['n'] and
          type(labels) is list and len(labels)==len(draws),
          'incomplete or unsupported enrolled prefix')
    acts=[];reports=[];state=d['initial'];previous=contract_pin
    for i,record in enumerate(draws):
        v25.exact_keys(record,DRAW,'witness draw')
        check(type(record['index']) is int and record['index']==i and
              record['state']==state and record['prev_sha256']==previous,
              'invalid record ordering, continuity, or policy state')
        for key in ('operator_commit_sha256','witness_commit_sha256'):
            bytes32(record[key],key)
        os=record['operator_share_hex'];ws=record['witness_share_hex']
        check(record['operator_commit_sha256']==commit_share('operator',contract_pin,i,previous,os)
              and record['witness_commit_sha256']==commit_share('witness',contract_pin,i,previous,ws),
              'share reveal does not match previously witnessed commitments')
        commitment=commitment_body(contract_pin,i,previous,state,
                                    record['operator_commit_sha256'],record['witness_commit_sha256'])
        verify_sig(pub,commitment,record['commit_receipt_signature_b64'])
        a=record['action'];r=record['report']
        check(type(a) is int and a in (0,1) and type(r) is int and r in (0,1),
              'invalid assignment or report')
        check(a==treatment_from_shares(os,ws,bits,probabilities[state]),
              'treatment assignment not generated from committed random shares')
        verify_sig(pub,reveal_body(contract_pin,commitment,
                   record['commit_receipt_signature_b64'],os,ws,a,r),
                   record['draw_signature_b64'])
        acts.append(a);reports.append(r)
        previous=D(record)
        end=i+1==n or (i+1>=d['min'] and d['stop'][state][a][r])
        check(end==(i==len(draws)-1),'premature stop or concealed earlier stopping event')
        state=d['trans'][state][a][r]
    derived={'assignments':acts,'reports':reports,'true_intervals':labels}
    internal_pin=v25.evidence_digest(study_pin,derived)
    scientific=v25.audit(study_protocol,derived,protocol_pin=study_pin,
                         evidence_pin=internal_pin)
    return {'format':RESULT,'status':scientific['status'],
            'verified_signed_draws':len(draws),
            'exact_treatment_probabilities_by_state':[str(v) for v in probabilities],
            'first_signed_commit_anchor':contract_pin,
            'terminal_signed_record_sha256':previous,
            'conditional_lower_ate':scientific['anytime_lower_ate'],
            'conditional_confidence_alpha':scientific['conditional_confidence_alpha'],
            'asserted_measurement_calibration_failure':scientific['asserted_joint_calibration_failure_bound'],
            'conditional_scientific_report':scientific,
            'ceremony_contract_sha256':contract_pin,
            'study_protocol_sha256':study_pin,
            'transcript_sha256':evidence_pin,
            'trust_boundary':'Ed25519 authenticates witness signatures, and XOR mapping is exactly unbiased IF at least one share per draw is conditionally uniform/unpredictable, commits are completed before reveals, an independent witness enforces the chronology, no selective abort/dropout occurs, and enrollment is complete. Signatures/hashes alone cannot prove those premises.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('ceremony_contract','study_protocol','witness_evidence'):
        p.add_argument(name)
    for key in ('contract_pin','study_pin','evidence_pin'):
        p.add_argument('--'+key.replace('_','-'),required=True)
    args=p.parse_args()
    try:
        report=audit(v25.read(args.ceremony_contract),v25.read(args.study_protocol),
                     v25.read(args.witness_evidence),contract_pin=args.contract_pin,
                     study_pin=args.study_pin,evidence_pin=args.evidence_pin)
        print(json.dumps(report,indent=2,sort_keys=True))
    except (Reject,ValueError,TypeError,KeyError,OverflowError,OSError) as exc:
        p.exit(2,'REJECTED: '+str(exc)+'\n')

if __name__=='__main__':main()
